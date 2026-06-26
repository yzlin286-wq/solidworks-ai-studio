from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from sw_ai_backend.core.config import ConfigStore
from sw_ai_backend.core.paths import project_root, validation_latest_dir
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession, ensure_skill_import_path


SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")
TEXT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".csv",
    ".html",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".tsx",
    ".ts",
    ".txt",
    ".yml",
    ".yaml",
}
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__"}
CAD_SUFFIXES = {".sldprt", ".sldasm", ".slddrw", ".step", ".stp", ".stl", ".pdf", ".dxf", ".dwg"}
REOPEN_SUFFIXES = {".sldprt", ".sldasm", ".slddrw", ".step", ".stp", ".stl"}
FILE_LOAD_ERROR_NAMES = {
    1: "swGenericError",
    2: "swFileNotFoundError",
    1024: "swInvalidFileTypeError",
    65536: "swFileWithSameTitleAlreadyOpen",
    1048576: "swAddinInteruptError",
    2097152: "swFileRequiresRepairError",
    4194304: "swFileCriticalDataRepairError",
    8388608: "swApplicationBusy",
}
DEFAULT_TEMPLATE_PREFERENCES = {
    "part": (8, ".prtdot", ["gb_part.prtdot", "part.prtdot"]),
    "assembly": (9, ".asmdot", ["gb_assembly.asmdot", "assembly.asmdot"]),
    "drawing": (10, ".drwdot", ["gb_a4.drwdot", "a4.drwdot"]),
}


@dataclass
class TruthAudit:
    capabilities: dict[str, Any]
    report: dict[str, Any]
    manifest: dict[str, Any]
    preflight: dict[str, Any]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _latest_result_by_capability(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for result in results:
        capability_id = str(result.get("capability_id", ""))
        if capability_id:
            grouped[capability_id] = result
    return grouped


def _file_exists(path_value: str) -> bool:
    try:
        path = Path(path_value)
        return path.exists() and path.stat().st_size > 0
    except Exception:
        return False


def _describe_file_load_error(value: Any) -> str:
    try:
        numeric = int(value)
    except Exception:
        return str(value)
    name = FILE_LOAD_ERROR_NAMES.get(numeric)
    return f"{numeric}/{name}" if name else str(numeric)


def _find_template_fallback(suffix: str, preferred_names: list[str]) -> str:
    roots = [
        Path(r"C:\ProgramData\SOLIDWORKS"),
        Path(r"C:\ProgramData\SolidWorks"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for template_dir in root.glob(r"SOLIDWORKS 20*/templates"):
            for preferred in preferred_names:
                candidate = template_dir / preferred
                if candidate.exists():
                    return str(candidate)
            candidates.extend(path for path in template_dir.rglob(f"*{suffix}") if path.is_file())
    return str(sorted(candidates)[0]) if candidates else ""


def _ensure_default_templates(sw: Any) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for name, (preference, suffix, preferred_names) in DEFAULT_TEMPLATE_PREFERENCES.items():
        try:
            current = str(sw.GetUserPreferenceStringValue(preference) or "")
        except Exception as exc:
            repairs.append({"name": name, "preference": preference, "error": f"read failed: {exc}"})
            continue
        current_exists = bool(current) and Path(current).exists()
        fallback = ""
        changed = False
        if not current_exists:
            fallback = _find_template_fallback(suffix, preferred_names)
            if fallback:
                try:
                    changed = bool(sw.SetUserPreferenceStringValue(preference, fallback))
                except Exception as exc:
                    repairs.append(
                        {
                            "name": name,
                            "preference": preference,
                            "old": current,
                            "old_exists": current_exists,
                            "fallback": fallback,
                            "fallback_exists": Path(fallback).exists(),
                            "changed": False,
                            "error": f"write failed: {exc}",
                        }
                    )
                    continue
        try:
            new = str(sw.GetUserPreferenceStringValue(preference) or "")
        except Exception:
            new = ""
        repairs.append(
            {
                "name": name,
                "preference": preference,
                "old": current,
                "old_exists": current_exists,
                "fallback": fallback,
                "fallback_exists": bool(fallback) and Path(fallback).exists(),
                "changed": changed,
                "new": new,
                "new_exists": bool(new) and Path(new).exists(),
            }
        )
    return repairs


def _com_member(obj: Any, name: str, *args: Any) -> Any:
    member = getattr(obj, name)
    if args:
        return member(*args)
    try:
        return member() if callable(member) else member
    except Exception as exc:
        message = str(exc)
        if "-2147352573" in message or "找不到成员" in message or "Member not found" in message:
            return member
        raise


def _close_model(sw: Any, model: Any) -> None:
    try:
        title = str(_com_member(model, "GetTitle") or "")
        if title:
            sw.CloseDoc(title)
    except Exception:
        pass


def _close_matching_documents(sw: Any, path: Path) -> None:
    stem = path.stem.lower()
    target_path = str(path.resolve()).lower()
    try:
        documents = _com_member(sw, "GetDocuments")
    except Exception:
        documents = []
    for document in documents or []:
        try:
            title = str(_com_member(document, "GetTitle") or "")
        except Exception:
            title = ""
        try:
            path_name = str(_com_member(document, "GetPathName") or "")
        except Exception:
            path_name = ""
        normalized_path = str(Path(path_name).resolve()).lower() if path_name else ""
        if normalized_path == target_path or title.lower().startswith(stem):
            try:
                sw.CloseDoc(title)
            except Exception:
                pass


def _open_import_file(sw: Any, path: Path) -> tuple[Any | None, str]:
    ensure_skill_import_path()
    from sw_preflight import import_com_dependencies

    pythoncom, win32com_client, _variant = import_com_dependencies()
    _ensure_default_templates(sw)

    try:
        import_data = None
        try:
            import_data = sw.GetImportFileData(str(path))
        except Exception:
            import_data = None
        if import_data is None:
            import_data = win32com_client.VARIANT(pythoncom.VT_DISPATCH, None)
        errors_seen = []
        attempt_count = 0
        errors = win32com_client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        model = sw.LoadFile4(str(path), "r", import_data, errors)
        attempt_count += 1
        if model is not None:
            return model, "LoadFile4 imported file with option='r'."
        errors_seen.append(_describe_file_load_error(errors.value))
        unique_errors = ", ".join(sorted(set(errors_seen))) or "unknown"
        load_file4_reason = f"LoadFile4 failed across {attempt_count} options; errors={unique_errors}."
    except Exception as exc:
        load_file4_reason = f"LoadFile4 exception: {exc}"

    return None, f"{load_file4_reason} OpenDoc7 fallback not attempted because clean-session probes terminated the SolidWorks COM server."


def _run_reopen_probe(path: Path) -> dict[str, Any]:
    code = textwrap.dedent(
        """
        from __future__ import annotations

        import contextlib
        import io
        import json
        import sys
        import time
        import traceback
        from pathlib import Path

        path = Path(sys.argv[1]).resolve()
        scripts = Path(sys.argv[2]).resolve()
        sys.path.insert(0, str(scripts))

        payload = {
            "reopen_passed": False,
            "reason": "",
            "document_title": "",
            "document_type": "",
            "template_preferences": [],
            "log": "",
        }
        log = io.StringIO()
        FILE_LOAD_ERROR_NAMES = {
            1: "swGenericError",
            2: "swFileNotFoundError",
            1024: "swInvalidFileTypeError",
            65536: "swFileWithSameTitleAlreadyOpen",
            1048576: "swAddinInteruptError",
            2097152: "swFileRequiresRepairError",
            4194304: "swFileCriticalDataRepairError",
            8388608: "swApplicationBusy",
        }
        DEFAULT_TEMPLATE_PREFERENCES = {
            "part": (8, ".prtdot", ["gb_part.prtdot", "part.prtdot"]),
            "assembly": (9, ".asmdot", ["gb_assembly.asmdot", "assembly.asmdot"]),
            "drawing": (10, ".drwdot", ["gb_a4.drwdot", "a4.drwdot"]),
        }

        def describe_file_load_error(value):
            try:
                numeric = int(value)
            except Exception:
                return str(value)
            name = FILE_LOAD_ERROR_NAMES.get(numeric)
            return f"{numeric}/{name}" if name else str(numeric)

        def member(obj, name, *args):
            value = getattr(obj, name)
            if args:
                return value(*args)
            try:
                return value() if callable(value) else value
            except Exception as exc:
                message = str(exc)
                if "-2147352573" in message or "找不到成员" in message or "Member not found" in message:
                    return value
                raise

        def close_model(sw, model):
            try:
                title = str(member(model, "GetTitle") or "")
                if title:
                    sw.CloseDoc(title)
            except Exception:
                pass

        def close_matching(sw):
            stem = path.stem.lower()
            target = str(path).lower()
            try:
                docs = member(sw, "GetDocuments") or []
            except Exception:
                docs = []
            for doc in docs:
                try:
                    title = str(member(doc, "GetTitle") or "")
                except Exception:
                    title = ""
                try:
                    doc_path = str(member(doc, "GetPathName") or "")
                except Exception:
                    doc_path = ""
                normalized = str(Path(doc_path).resolve()).lower() if doc_path else ""
                if normalized == target or title.lower().startswith(stem):
                    try:
                        sw.CloseDoc(title)
                    except Exception:
                        pass

        def find_template_fallback(suffix, preferred_names):
            roots = [Path(r"C:\ProgramData\SOLIDWORKS"), Path(r"C:\ProgramData\SolidWorks")]
            candidates = []
            for root in roots:
                if not root.exists():
                    continue
                for template_dir in root.glob(r"SOLIDWORKS 20*/templates"):
                    for preferred in preferred_names:
                        candidate = template_dir / preferred
                        if candidate.exists():
                            return str(candidate)
                    candidates.extend(candidate for candidate in template_dir.rglob(f"*{suffix}") if candidate.is_file())
            return str(sorted(candidates)[0]) if candidates else ""

        def ensure_default_templates(sw):
            repairs = []
            for name, preference_data in DEFAULT_TEMPLATE_PREFERENCES.items():
                preference, suffix, preferred_names = preference_data
                try:
                    old = str(sw.GetUserPreferenceStringValue(preference) or "")
                except Exception as exc:
                    repairs.append({"name": name, "preference": preference, "error": f"read failed: {exc}"})
                    continue
                old_exists = bool(old) and Path(old).exists()
                fallback = ""
                changed = False
                if not old_exists:
                    fallback = find_template_fallback(suffix, preferred_names)
                    if fallback:
                        try:
                            changed = bool(sw.SetUserPreferenceStringValue(preference, fallback))
                        except Exception as exc:
                            repairs.append(
                                {
                                    "name": name,
                                    "preference": preference,
                                    "old": old,
                                    "old_exists": old_exists,
                                    "fallback": fallback,
                                    "fallback_exists": Path(fallback).exists(),
                                    "changed": False,
                                    "error": f"write failed: {exc}",
                                }
                            )
                            continue
                try:
                    new = str(sw.GetUserPreferenceStringValue(preference) or "")
                except Exception:
                    new = ""
                repairs.append(
                    {
                        "name": name,
                        "preference": preference,
                        "old": old,
                        "old_exists": old_exists,
                        "fallback": fallback,
                        "fallback_exists": bool(fallback) and Path(fallback).exists(),
                        "changed": changed,
                        "new": new,
                        "new_exists": bool(new) and Path(new).exists(),
                    }
                )
            return repairs

        def attach():
            import pythoncom
            import win32com.client
            import win32com.client.dynamic

            pythoncom.CoInitialize()
            last_exc = None
            for attempt in range(4):
                try:
                    import_sw = win32com.client.Dispatch("SldWorks.Application")
                    if attempt == 0:
                        time.sleep(1)
                    try:
                        import_sw.Visible = True
                    except Exception:
                        pass
                    _ = member(import_sw, "RevisionNumber")
                    sw = win32com.client.dynamic.Dispatch(import_sw._oleobj_)
                    return sw, import_sw, pythoncom, win32com.client
                except Exception as exc:
                    last_exc = exc
                    time.sleep(2)
            raise RuntimeError(f"Could not attach SolidWorks for reopen probe: {last_exc}")

        def open_import(sw, pythoncom, win32com_client):
            load_file4_reason = ""
            try:
                import_variants = []
                try:
                    import_data = sw.GetImportFileData(str(path))
                    if import_data is not None:
                        import_variants.append(("GetImportFileData", import_data))
                except Exception:
                    pass
                import_variants.extend(
                    [
                        ("VT_DISPATCH_None", win32com_client.VARIANT(pythoncom.VT_DISPATCH, None)),
                    ]
                )
                errors_seen = []
                attempt_count = 0
                for variant_name, import_data in import_variants:
                    try:
                        errors = win32com_client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                        model = sw.LoadFile4(str(path), "r", import_data, errors)
                        attempt_count += 1
                        if model is not None:
                            return model, f"LoadFile4 imported file with {variant_name}, option='r'."
                        errors_seen.append(describe_file_load_error(errors.value))
                    except Exception as exc:
                        errors_seen.append(f"exception={exc}")
                unique_errors = ", ".join(sorted(set(errors_seen))) or "unknown"
                load_file4_reason = f"LoadFile4 failed across {attempt_count} import variants/options; errors={unique_errors}."
            except Exception as exc:
                load_file4_reason = f"LoadFile4 exception: {exc}"

            return None, f"{load_file4_reason} OpenDoc7 fallback not attempted because clean-session probes terminated the SolidWorks COM server."

        try:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                from sw_connect import open_document

                sw, import_sw, pythoncom, win32com_client = attach()
                payload["template_preferences"] = ensure_default_templates(sw)
                close_matching(sw)
                suffix = path.suffix.lower()
                if suffix in {".step", ".stp", ".stl"}:
                    model, reason = open_import(sw, pythoncom, win32com_client)
                    close_owner = sw
                else:
                    model = open_document(sw, str(path), read_only=True, silent=True, raise_on_error=True)
                    reason = "OpenDoc6 opened native SolidWorks document."
                    close_owner = sw
                if model is None:
                    raise RuntimeError(reason)
                payload["reopen_passed"] = True
                payload["reason"] = reason
                payload["document_title"] = str(member(model, "GetTitle") or "")
                payload["document_type"] = str(member(model, "GetType") or "")
                close_model(close_owner, model)
        except Exception as exc:
            payload["reason"] = str(exc)[:500]
            payload["traceback"] = traceback.format_exc()[-2000:]
        payload["log"] = log.getvalue()[-2000:]
        print(json.dumps(payload, ensure_ascii=False))
        """
    )
    scripts = project_root() / "vendor" / "skills" / "solidworks-automation" / "scripts"
    completed = subprocess.run(
        [sys.executable, "-c", code, str(path), str(scripts)],
        cwd=str(project_root()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "reopen_passed": False,
            "reason": (completed.stderr or completed.stdout or f"Probe exited with code {completed.returncode}")[:500],
            "document_title": "",
            "document_type": "",
            "log": completed.stdout[-2000:],
        }
    try:
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception as exc:
        return {
            "reopen_passed": False,
            "reason": f"Probe returned invalid JSON: {exc}",
            "document_title": "",
            "document_type": "",
            "log": completed.stdout[-2000:],
        }


def _evidence_for(capability: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {
            "has_real_acceptance_result": False,
            "has_file_evidence": False,
            "has_solidworks_state_evidence": False,
            "existing_files": [],
        }
    created_files = [str(item) for item in result.get("created_files", []) if item]
    existing_files = [item for item in created_files if _file_exists(item)]
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    state_text = "\n".join(
        [
            str(result.get("active_document_before", "")),
            str(result.get("active_document_after", "")),
            stdout,
            stderr,
        ]
    ).lower()
    has_state = any(token in state_text for token in ["solidworks", "document", "sldprt", "sldasm", "slddrw", "revision", "active"])
    return {
        "has_real_acceptance_result": True,
        "has_file_evidence": bool(existing_files),
        "has_solidworks_state_evidence": has_state,
        "existing_files": existing_files,
    }


def scan_for_secrets(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & SKIP_DIRS:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        matches = SECRET_RE.findall(text)
        if matches:
            findings.append({"path": str(path), "match_count": len(matches)})
    payload = {
        "ok": not findings,
        "generated_at": datetime.now().isoformat(),
        "finding_count": len(findings),
        "findings": findings,
        "redaction": "Secret values are never written to this report; only paths and counts are recorded.",
    }
    target = validation_latest_dir() / "security_secret_scan.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def write_llm_api_validation() -> dict[str, Any]:
    config = ConfigStore().load()
    profile = next((item for item in config.profiles if item.id == config.active_profile_id), config.profiles[0])
    payload: dict[str, Any] = {
        "ok": False,
        "generated_at": datetime.now().isoformat(),
        "profile_id": profile.id,
        "api_base_url": profile.api_base_url,
        "model": profile.model,
        "api_key_present": bool(profile.api_key),
        "api_key_redacted": True,
        "status_code": None,
        "models_returned": [],
        "models_verified": False,
        "chat_verified": False,
        "error": "",
    }
    if profile.api_key:
        try:
            with httpx.Client(timeout=min(profile.timeout_seconds, 15)) as client:
                try:
                    response = client.get(
                        f"{profile.api_base_url}/models",
                        headers={"Authorization": f"Bearer {profile.api_key}", "Content-Type": "application/json"},
                    )
                    payload["status_code"] = response.status_code
                    if response.status_code < 400:
                        payload["models_verified"] = True
                        data = response.json() if response.content else {}
                        payload["models_returned"] = [str(item.get("id", "")) for item in data.get("data", []) if item.get("id")][:20]
                except Exception as exc:
                    payload["error"] = f"models check failed: {str(exc)[:300]}"
                chat_response = client.post(
                    f"{profile.api_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {profile.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": profile.model,
                        "messages": [
                            {"role": "system", "content": "你是本地 CAD 自动化应用的连接测试。"},
                            {"role": "user", "content": "请只回复：SWAI_OK"},
                        ],
                        "temperature": 0,
                        "max_tokens": 128,
                    },
                )
            payload["chat_status_code"] = chat_response.status_code
            if chat_response.status_code < 400:
                data = chat_response.json() if chat_response.content else {}
                content = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
                payload["chat_verified"] = bool(content)
            payload["ok"] = bool(payload["chat_verified"])
        except Exception as exc:
            payload["error"] = str(exc)[:500]
    else:
        payload["error"] = "No API key is configured for the active profile."
    target = validation_latest_dir() / "llm_api_validation.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def write_reopen_manifest(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    latest = validation_latest_dir()
    manifest_files = [Path(str(item)) for item in (manifest or {}).get("files", []) if item and not Path(str(item)).name.startswith("~$")]
    if manifest_files:
        candidates = [path for path in manifest_files if path.suffix.lower() in CAD_SUFFIXES and path.exists()]
    else:
        candidates = [path for path in latest.rglob("*") if path.is_file() and path.suffix.lower() in CAD_SUFFIXES and not path.name.startswith("~$")]
    files = sorted({path.resolve() for path in candidates})
    entries: list[dict[str, Any]] = []
    for path in files:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            continue
        suffix = path.suffix.lower()
        attempted = suffix in REOPEN_SUFFIXES
        entry = {
            "file_path": str(path),
            "kind": suffix.lstrip("."),
            "size": size,
            "reopen_attempted": attempted,
            "reopen_passed": False,
            "reason": "",
            "document_title": "",
            "document_type": "",
        }
        if not attempted:
            entry["reason"] = "File type is export evidence but not part of the automated reopen probe set."
            entries.append(entry)
            continue
        probe = _run_reopen_probe(path)
        entry["reopen_passed"] = bool(probe.get("reopen_passed"))
        entry["reason"] = str(probe.get("reason", ""))
        entry["document_title"] = str(probe.get("document_title", ""))
        entry["document_type"] = str(probe.get("document_type", ""))
        if probe.get("traceback"):
            entry["traceback"] = str(probe.get("traceback", ""))
        if probe.get("log"):
            entry["log"] = str(probe.get("log", ""))
        if probe.get("template_preferences"):
            entry["template_preferences"] = probe.get("template_preferences")
        entries.append(entry)
    payload = {
        "ok": bool(entries) and all(not item["reopen_attempted"] or item["reopen_passed"] for item in entries),
        "generated_at": datetime.now().isoformat(),
        "cad_file_count": len(entries),
        "reopen_attempted_count": sum(1 for item in entries if item["reopen_attempted"]),
        "reopen_passed_count": sum(1 for item in entries if item["reopen_passed"]),
        "entries": entries,
        "conclusion": "Dedicated SolidWorks reopen checks passed." if entries and all(not item["reopen_attempted"] or item["reopen_passed"] for item in entries) else "Some generated CAD files did not pass dedicated reopen checks.",
    }
    target = latest / "solidworks_reopen_manifest.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def build_truth_audit() -> dict[str, Any]:
    root = project_root()
    latest = validation_latest_dir()
    capabilities_path = root / "backend" / "generated" / "solidworks_skill_capabilities.json"
    real_report_path = latest / "REAL_SW2025_VALIDATION_REPORT.json"
    manifest_path = latest / "files_manifest.json"
    preflight_path = root / "outputs" / "validation" / "sw2025_preflight.json"

    capabilities_payload = load_json(capabilities_path, {"capabilities": []})
    real_report = load_json(real_report_path, {"results": []})
    manifest = load_json(manifest_path, {"files": []})
    preflight = load_json(preflight_path, {"checks": []})
    secret_scan = scan_for_secrets(root)
    llm_api_validation = write_llm_api_validation()
    reopen_manifest = write_reopen_manifest(manifest)

    capabilities = list(capabilities_payload.get("capabilities", []))
    results = list(real_report.get("results", []))
    result_by_id = _latest_result_by_capability(results)
    status_counts = Counter()
    capability_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    untested: list[str] = []
    strict_failures: list[str] = []

    for capability in capabilities:
        cap_id = str(capability.get("id", ""))
        result = result_by_id.get(cap_id)
        status = str((result or {}).get("status") or capability.get("real_sw2025_status") or "untested")
        status_counts[status] += 1
        evidence = _evidence_for(capability, result)
        is_doc_only = str(capability.get("execution_kind")) == "documentation_only" or not bool(capability.get("callable"))
        callable_exec = bool(capability.get("callable")) and not is_doc_only
        api_callable = bool(capability.get("api_endpoint")) and bool(capability.get("callable"))
        row = {
            "id": cap_id,
            "title": capability.get("title", ""),
            "callable": bool(capability.get("callable")),
            "execution_kind": capability.get("execution_kind", ""),
            "source_type": capability.get("source_type", ""),
            "source_path": capability.get("source_path", ""),
            "requires_addin": capability.get("requires_addin", "none"),
            "ui_visible": bool(capability.get("ui_exposed")),
            "api_callable": api_callable,
            "status": status,
            "skip_reason": str((result or {}).get("skip_reason") or capability.get("skip_reason") or ""),
            "error_summary": str((result or {}).get("error_summary") or (result or {}).get("stderr") or "")[:800],
            "documentation_only": is_doc_only,
            **evidence,
        }
        capability_rows.append(row)
        if status == "skipped_with_reason":
            skipped.append({"id": cap_id, "reason": row["skip_reason"]})
        if status == "failed":
            failed.append({"id": cap_id, "error_summary": row["error_summary"]})
        if status == "untested":
            untested.append(cap_id)
        if callable_exec:
            if status != "passed":
                strict_failures.append(f"{cap_id} is callable and executable but status is {status}.")
            if not evidence["has_real_acceptance_result"]:
                strict_failures.append(f"{cap_id} has no real acceptance result.")
            if not (evidence["has_file_evidence"] or evidence["has_solidworks_state_evidence"]):
                strict_failures.append(f"{cap_id} has no file or SolidWorks state evidence.")

    addin_status = {
        item.get("key"): item for item in preflight.get("checks", []) if str(item.get("key", "")).startswith("addin-")
    }
    if not bool(reopen_manifest.get("ok")):
        failed_reopen = [
            str(item.get("file_path", ""))
            for item in reopen_manifest.get("entries", [])
            if item.get("reopen_attempted") and not item.get("reopen_passed")
        ]
        strict_failures.append(
            f"solidworks_reopen_manifest is not ok; {len(failed_reopen)} attempted CAD reopen checks failed."
        )
    if not bool(llm_api_validation.get("ok")):
        strict_failures.append("llm_api_validation is not ok for the active profile.")
    all_functionality_claim_allowed = not skipped and not failed and not untested and not strict_failures
    payload = {
        "strict_ok": (
            all_functionality_claim_allowed
            and bool(real_report.get("ok"))
            and bool(secret_scan.get("ok"))
            and bool(reopen_manifest.get("ok"))
            and bool(llm_api_validation.get("ok"))
        ),
        "all_functions_really_usable": all_functionality_claim_allowed,
        "current_claim": (
            "All functions are proven real-usable."
            if all_functionality_claim_allowed
            else "当前还不能宣称所有功能真实可用。"
        ),
        "generated_at": datetime.now().isoformat(),
        "inputs": {
            "capabilities": str(capabilities_path),
            "real_report": str(real_report_path),
            "manifest": str(manifest_path),
            "preflight": str(preflight_path),
        },
        "summary": {
            "capability_total": len(capabilities),
            "callable_total": sum(1 for item in capabilities if item.get("callable")),
            "passed": int(status_counts.get("passed", 0)),
            "failed": int(status_counts.get("failed", 0)),
            "skipped_with_reason": int(status_counts.get("skipped_with_reason", 0)),
            "untested": int(status_counts.get("untested", 0)),
            "documentation_only": sum(1 for row in capability_rows if row["documentation_only"]),
            "manifest_file_count": len(manifest.get("files", [])),
        },
        "skipped": skipped,
        "failed": failed,
        "untested": untested,
        "strict_failures": strict_failures,
        "addin_status": addin_status,
        "capabilities": capability_rows,
        "security_secret_scan": secret_scan,
        "llm_api_validation": llm_api_validation,
        "solidworks_reopen_manifest": reopen_manifest,
    }
    return payload


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# 严格真实性审计报告",
        "",
        f"生成时间：{payload['generated_at']}",
        f"严格审计通过：{payload['strict_ok']}",
        f"结论：{payload['current_claim']}",
        "",
        "## 摘要",
        "",
        f"- 能力总数：{summary['capability_total']}",
        f"- 可调用能力：{summary['callable_total']}",
        f"- 已通过：{summary['passed']}",
        f"- 失败：{summary['failed']}",
        f"- 有原因跳过：{summary['skipped_with_reason']}",
        f"- 未测试：{summary['untested']}",
        f"- 仅文档/上下文能力：{summary['documentation_only']}",
        f"- Manifest 文件数：{summary['manifest_file_count']}",
        "",
        "## 跳过",
    ]
    if payload["skipped"]:
        for item in payload["skipped"]:
            lines.append(f"- `{item['id']}`: {item['reason']}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 失败"])
    if payload["failed"]:
        for item in payload["failed"]:
            lines.append(f"- `{item['id']}`: {item['error_summary']}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 严格失败项"])
    if payload["strict_failures"]:
        for item in payload["strict_failures"][:200]:
            lines.append(f"- {item}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 能力证据", "", "| 能力 | 可调用 | 类型 | UI | API | 状态 | 真实结果 | 文件证据 | SW 状态 |", "|---|---:|---|---:|---:|---|---:|---:|---:|"])
    for row in payload["capabilities"]:
        lines.append(
            f"| `{row['id']}` | {row['callable']} | {row['execution_kind']} | {row['ui_visible']} | {row['api_callable']} | "
            f"{row['status']} | {row['has_real_acceptance_result']} | {row['has_file_evidence']} | {row['has_solidworks_state_evidence']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    latest = validation_latest_dir()
    payload = build_truth_audit()
    json_path = latest / "TRUTH_AUDIT_REPORT.json"
    md_path = latest / "TRUTH_AUDIT_REPORT.md"
    strict_json = latest / "STRICT_TRUTH_REPORT.json"
    strict_md = latest / "STRICT_TRUTH_REPORT.md"
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    json_path.write_text(json_text, encoding="utf-8")
    strict_json.write_text(json_text, encoding="utf-8")
    write_markdown(payload, md_path)
    write_markdown(payload, strict_md)
    print(json.dumps({"strict_ok": payload["strict_ok"], "report_json": str(strict_json), "report_markdown": str(strict_md)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
