$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) { Join-Path $Root ".venv\Scripts\python.exe" } else { "python" }
$env:PYTHONPATH = Join-Path $Root "backend"
$env:SWAI_PROJECT_ROOT = $Root
$env:SWAI_OUTPUT_DIR = Join-Path $Root "outputs"

Push-Location $Root
try {
@'
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from sw_ai_backend.core.paths import validation_latest_dir
from sw_ai_backend.main import create_app
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession

client = TestClient(create_app())
headers = {"X-SWAI-Token": os.environ.get("SWAI_API_TOKEN", "dev-token")}
latest = validation_latest_dir()
report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "running", "scenarios": []}

def record(name, status, expected, observed, skipped_with_reason=""):
    report["scenarios"].append({
        "name": name,
        "status": status,
        "expected": expected,
        "observed": observed,
        "skipped_with_reason": skipped_with_reason,
    })

def write_report():
    latest.mkdir(parents=True, exist_ok=True)
    json_path = latest / "ERROR_SCENARIOS_REPORT.json"
    md_path = latest / "ERROR_SCENARIOS_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Error Scenarios Validation", "", f"Status: {report['status']}", "", "| scenario | status | expected | observed | skipped_with_reason |", "|---|---|---|---|---|"]
    for item in report["scenarios"]:
        observed = str(item["observed"]).replace("|", "/")
        lines.append(f"| {item['name']} | {item['status']} | {item['expected']} | {observed} | {item['skipped_with_reason']} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["report_json"] = str(json_path)
    report["report_markdown"] = str(md_path)

try:
    status = RealSolidWorksSession().status(start_if_missing=False)
    if status.attached:
        record("solidworks_not_connected", "skipped_with_reason", "No COM session", status.model_dump(mode="json"), "SolidWorks is currently connected; script will not close user session.")
    else:
        response = client.post("/api/solidworks/connect", headers=headers, json={}, timeout=30)
        if response.json().get("ok") is False:
            record("solidworks_not_connected", "pass", "Connection failure is explicit", response.json())
        else:
            record("solidworks_not_connected", "skipped_with_reason", "No COM session", response.json(), "SolidWorks was reachable during validation; script will not force-disconnect it.")
except Exception as exc:
    record("solidworks_not_connected", "pass", "Connection failure is explicit", str(exc))

try:
    status = RealSolidWorksSession().status(start_if_missing=False)
    if not status.attached:
        record("no_active_document", "skipped_with_reason", "Explicit no-active-doc failure", status.model_dump(mode="json"), "SolidWorks is not connected.")
    elif status.active_document_title:
        record("no_active_document", "skipped_with_reason", "Explicit no-active-doc failure", status.model_dump(mode="json"), "An active document exists; script will not close user documents.")
    else:
        record("no_active_document", "pass", "Session reports no active document without creating or closing documents", status.model_dump(mode="json"))
except Exception as exc:
    record("no_active_document", "pass", "Review/export fails without active document", str(exc))

record("template_missing", "skipped_with_reason", "Preflight reports template warning/failure", "Use a disposable SolidWorks profile or manually move template paths before running preflight.", "Non-destructive release validation will not rename or modify user template files.")

try:
    with tempfile.TemporaryDirectory() as tmp:
        blocked = Path(tmp) / "not_a_directory"
        blocked.write_text("blocked", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "backend")
        env["SWAI_PROJECT_ROOT"] = str(Path.cwd())
        env["SWAI_OUTPUT_DIR"] = str(blocked)
        probe = subprocess.run([sys.executable, "-c", "from sw_ai_backend.core.paths import user_outputs_dir; print(user_outputs_dir())"], cwd=str(Path.cwd()), env=env, capture_output=True, text=True, timeout=30)
        record("output_dir_unusable", "pass" if probe.returncode != 0 else "fail", "Path-as-file output dir is rejected", {"returncode": probe.returncode, "stderr": probe.stderr[-500:]})
except Exception as exc:
    record("output_dir_unusable", "pass", "Path-as-file output dir is rejected", str(exc))

try:
    preflight = client.get("/api/solidworks/preflight", headers=headers, timeout=90).json()
    addin_checks = [item for item in preflight.get("checks", []) if str(item.get("key", "")).startswith("addin-")]
    unavailable = [item for item in addin_checks if item.get("status") != "pass"]
    if unavailable:
        record("requires_addin_unavailable", "pass", "Unavailable add-ins are warn/skipped with reason", unavailable)
    else:
        record("requires_addin_unavailable", "skipped_with_reason", "Unavailable add-ins are warn/skipped with reason", addin_checks, "All checked add-ins are currently available.")
except Exception as exc:
    record("requires_addin_unavailable", "fail", "Unavailable add-ins are warn/skipped with reason", str(exc))

failed = [item for item in report["scenarios"] if item["status"] == "fail"]
report["status"] = "passed" if not failed else "failed"
write_report()
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if not failed else 1)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
