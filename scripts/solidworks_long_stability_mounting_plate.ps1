param(
  [int]$Count = 20,
  [int]$TimeoutSeconds = 420
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) { Join-Path $Root ".venv\Scripts\python.exe" } else { "python" }
$env:PYTHONPATH = Join-Path $Root "backend"
$env:SWAI_PROJECT_ROOT = $Root
$env:SWAI_OUTPUT_DIR = Join-Path $Root "outputs"
$env:SWAI_LONG_STABILITY_COUNT = [string]$Count
$env:SWAI_LONG_STABILITY_TIMEOUT = [string]$TimeoutSeconds

Push-Location $Root
try {
@'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from sw_ai_backend.core.paths import validation_latest_dir
from sw_ai_backend.main import create_app

count = int(os.environ["SWAI_LONG_STABILITY_COUNT"])
timeout = int(os.environ["SWAI_LONG_STABILITY_TIMEOUT"])
client = TestClient(create_app())
headers = {"X-SWAI-Token": os.environ.get("SWAI_API_TOKEN", "dev-token")}
latest = validation_latest_dir()
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "recipe_id": "mounting_plate",
    "count_requested": count,
    "timeout_seconds": timeout,
    "status": "running",
    "pass_count": 0,
    "fail_count": 0,
    "runs": [],
}

def write_report():
    latest.mkdir(parents=True, exist_ok=True)
    json_path = latest / "LONG_STABILITY_MOUNTING_PLATE_REPORT.json"
    md_path = latest / "LONG_STABILITY_MOUNTING_PLATE_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Mounting Plate Long-Stability Report",
        "",
        f"Status: {report['status']}",
        f"Requested: {report['count_requested']}",
        f"Pass: {report['pass_count']}",
        f"Fail: {report['fail_count']}",
        "",
        "| iteration | status | task_id | artifacts | error |",
        "|---:|---|---|---:|---|",
    ]
    for run in report["runs"]:
        lines.append(f"| {run['iteration']} | {run['status']} | `{run.get('task_id','')}` | {run.get('artifact_count',0)} | {run.get('error','')} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["report_json"] = str(json_path)
    report["report_markdown"] = str(md_path)

preflight = client.get("/api/solidworks/preflight", headers=headers, timeout=90).json()
report["preflight"] = {
    "can_run_real_com": preflight.get("can_run_real_com"),
    "solidworks_version": preflight.get("solidworks_version"),
    "state": preflight.get("state"),
}
if not preflight.get("can_run_real_com"):
    report["status"] = "failed"
    report["fail_count"] = count
    report["error"] = "SolidWorks COM preflight is not ready; real long-stability execution was not run."
    write_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1)

prompt = "Create a 120x80x10mm mounting plate with four M6 through holes, 1mm chamfer, save SLDPRT and export STEP."
for index in range(1, count + 1):
    run = {"iteration": index, "status": "running", "task_id": "", "artifact_count": 0, "artifacts": [], "error": ""}
    try:
        plan = client.post("/api/ai-capabilities/ai.parametric_part_generator/plan", headers=headers, json={"prompt": prompt, "recipe_id": "mounting_plate", "execution_mode": "real"}, timeout=60)
        plan.raise_for_status()
        task_id = plan.json()["task_id"]
        run["task_id"] = task_id
        for endpoint, payload in [
            ("generate-script", {"task_id": task_id, "recipe_id": "mounting_plate", "execution_mode": "real"}),
            ("validate", {"task_id": task_id}),
            ("approve", {"task_id": task_id, "approved": True, "approved_by": "long-stability"}),
            ("execute", {"task_id": task_id, "execution_mode": "real", "timeout_seconds": timeout}),
        ]:
            response = client.post(f"/api/ai-capabilities/ai.parametric_part_generator/{endpoint}", headers=headers, json=payload, timeout=timeout + 60)
            response.raise_for_status()
            body = response.json()
        run["status"] = body.get("status")
        run["artifact_count"] = len(body.get("artifacts", []))
        run["artifacts"] = body.get("artifacts", [])
        run["real_execution_verified"] = body.get("real_execution_verified")
        artifacts = body.get("artifacts", [])
        artifacts_exist = all(item.get("exists") for item in artifacts)
        evidence_ok = bool(body.get("real_execution_verified")) and bool(body.get("evidence", {}).get("created_files_exist"))
        if str(body.get("status", "")).lower() == "completed" and evidence_ok and len(artifacts) >= 4 and artifacts_exist:
            report["pass_count"] += 1
        else:
            report["fail_count"] += 1
            run["error"] = body.get("stderr") or body.get("skipped_with_reason") or "missing real execution evidence"
    except Exception as exc:
        report["fail_count"] += 1
        run["status"] = "FAILED"
        run["error"] = str(exc)
    report["runs"].append(run)
    write_report()

report["status"] = "passed" if report["pass_count"] == count and report["fail_count"] == 0 else "failed"
write_report()
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["status"] == "passed" else 1)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
