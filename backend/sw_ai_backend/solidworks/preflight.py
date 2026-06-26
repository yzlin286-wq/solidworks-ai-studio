from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import project_root, skill_paths, user_outputs_dir, validation_dir
from sw_ai_backend.models.schemas import PreflightCheck, PreflightResponse, StatusLevel
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession, ensure_skill_import_path


def _template_label(key: str) -> str:
    return {"part": "零件", "assembly": "装配体", "drawing": "工程图"}.get(key, key)


def _addin_label(key: str) -> str:
    return {
        "motion": "Motion",
        "simulation": "Simulation",
        "sheet_metal": "Sheet Metal",
        "weldments": "Weldments",
    }.get(key, key)


class SolidWorksPreflight:
    def __init__(self) -> None:
        self.paths = skill_paths()

    def run(self, write_report: bool = True, start_solidworks: bool = True) -> PreflightResponse:
        started_at = datetime.now(timezone.utc)
        started = time.perf_counter()
        checks: list[PreflightCheck] = []
        details: dict[str, Any] = {"generated_at": started_at.isoformat()}
        is_windows = platform.system().lower().startswith("windows")
        checks.append(self._check("windows", "Windows 系统", is_windows, "检测到 Windows。" if is_windows else "当前不是 Windows。"))
        details["platform"] = platform.platform()
        details["user"] = os.environ.get("USERNAME", "")
        details["session_name"] = os.environ.get("SESSIONNAME", "")

        sw_install = self._detect_solidworks_2025()
        details["solidworks_install"] = sw_install
        checks.append(
            PreflightCheck(
                key="skill-path",
                label="SolidWorks automation Skill 路径",
                status=StatusLevel.PASS if self.paths.solidworks.exists() else StatusLevel.FAIL,
                message=str(self.paths.solidworks),
                suggestion="" if self.paths.solidworks.exists() else "请运行 scripts/sync_solidworks_skill.ps1。",
            )
        )
        install_check = PreflightCheck(
            key="solidworks-2025-install",
            label="SolidWorks 2025 安装",
            status=StatusLevel.PASS if sw_install.get("detected") else StatusLevel.WARN,
            message=sw_install.get("message", ""),
            suggestion="" if sw_install.get("detected") else "请安装 SolidWorks 2025，或检查 COM 注册状态。",
        )

        dependency_details = self._dependencies()
        details["python_dependencies"] = dependency_details
        missing = [name for name, available in dependency_details.items() if not available]
        checks.append(
            PreflightCheck(
                key="python-com",
                label="Python COM 依赖",
                status=StatusLevel.PASS if not missing else StatusLevel.FAIL,
                message="pywin32 和 comtypes 可用。" if not missing else f"缺少：{', '.join(missing)}",
                suggestion="" if not missing else '请运行：python -m pip install "pywin32>=305" "comtypes>=1.2.0"',
            )
        )

        session_status = RealSolidWorksSession().status(start_if_missing=start_solidworks and not missing and is_windows)
        details["solidworks_session"] = session_status.model_dump(mode="json")
        if install_check.status != StatusLevel.PASS and session_status.version.startswith("33."):
            install_check = install_check.model_copy(
                update={
                    "status": StatusLevel.PASS,
                    "message": f"已连接 SolidWorks COM revision {session_status.version}；33.x 对应 SolidWorks 2025。",
                    "suggestion": "",
                }
            )
        checks.append(install_check)
        checks.append(
            PreflightCheck(
                key="solidworks",
                label="SolidWorks COM",
                status=StatusLevel.PASS if session_status.attached else StatusLevel.FAIL,
                message=session_status.message,
                suggestion="" if session_status.attached else "请手动启动 SolidWorks 2025，关闭阻塞弹窗后重新运行 preflight。",
            )
        )

        template_details = self._templates(session_status.attached)
        details["templates"] = template_details
        for key, value in template_details.items():
            checks.append(
                PreflightCheck(
                    key=f"template-{key}",
                    label=f"{_template_label(key)}模板",
                    status=StatusLevel.PASS if value.get("exists") else StatusLevel.WARN,
                    message=value.get("path") or value.get("message", "未检测到模板。"),
                    suggestion="" if value.get("exists") else "请在 Settings 或 SolidWorks 选项中配置模板路径。",
                )
            )

        output = user_outputs_dir()
        writable = self._is_writable(output)
        details["output_dir"] = {"path": str(output), "writable": writable}
        checks.append(self._check("output-dir", "验证输出目录", writable, str(output), "请检查文件夹权限。"))

        addins = self._addins(session_status.attached)
        details["addins"] = addins
        for key, value in addins.items():
            checks.append(
                PreflightCheck(
                    key=f"addin-{key}",
                    label=f"{_addin_label(key)} Add-in",
                    status=StatusLevel.PASS if value.get("available") else StatusLevel.WARN,
                    message=value.get("message", ""),
                    suggestion=value.get("suggestion", ""),
                )
            )

        mcp = self._mcp_probe()
        details["mcp"] = mcp
        checks.append(
            PreflightCheck(
                key="mcp-server",
                label="MCP server",
                status=StatusLevel.PASS if mcp.get("server_exists") and mcp.get("tool_count", 0) > 0 else StatusLevel.FAIL,
                message=f"从 {self.paths.solidworks_mcp_server} 发现 {mcp.get('tool_count', 0)} 个工具",
                suggestion="" if mcp.get("tool_count", 0) > 0 else "请同步 solidworks-automation Skill 并安装 MCP requirements。",
            )
        )

        can_run_real = all(
            check.status == StatusLevel.PASS
            for check in checks
            if check.key in {"windows", "python-com", "solidworks", "output-dir", "mcp-server"}
        )
        report_json = validation_dir() / "sw2025_preflight.json"
        report_md = validation_dir() / "sw2025_preflight.md"
        if write_report:
            self._write_reports(report_json, report_md, checks, details)
        finished_at = datetime.now(timezone.utc)
        return PreflightResponse(
            mode="solidworks" if can_run_real else "mock",
            checks=checks,
            can_run_real_com=can_run_real,
            solidworks_version=session_status.version,
            report_json=str(report_json),
            report_markdown=str(report_md),
            state="ready" if can_run_real else "mock",
            stale=False,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_seconds=round(time.perf_counter() - started, 3),
        )

    def _detect_solidworks_2025(self) -> dict[str, Any]:
        candidates = [
            Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"),
            Path(r"C:\Program Files\Dassault Systemes\SOLIDWORKS 2025\SLDWORKS.exe"),
        ]
        detected_paths = [str(path) for path in candidates if path.exists()]
        if detected_paths:
            return {"detected": True, "paths": detected_paths, "message": detected_paths[0]}
        if platform.system().lower().startswith("windows"):
            try:
                import winreg

                for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                    try:
                        with winreg.OpenKey(root, r"SOFTWARE\SolidWorks\SOLIDWORKS 2025") as key:
                            install_dir, _ = winreg.QueryValueEx(key, "InstallDir")
                            return {"detected": True, "paths": [str(install_dir)], "message": str(install_dir)}
                    except OSError:
                        continue
            except Exception:
                pass
        return {"detected": False, "paths": [], "message": "常见路径与注册表探测均未找到 SolidWorks 2025 安装路径。"}

    def _dependencies(self) -> dict[str, bool]:
        return {
            "pywin32": importlib.util.find_spec("win32com.client") is not None and importlib.util.find_spec("pythoncom") is not None,
            "comtypes": importlib.util.find_spec("comtypes") is not None,
        }

    def _templates(self, attached: bool) -> dict[str, dict[str, Any]]:
        result = {name: {"exists": False, "path": "", "message": "SolidWorks 会话不可用。"} for name in ["part", "assembly", "drawing"]}
        if not attached:
            return result
        try:
            ensure_skill_import_path()
            from sw_connect import find_template

            with solidworks_com_runtime("preflight template probe"):
                sw = RealSolidWorksSession().attach(start_if_missing=False)
                for doc_type in result:
                    try:
                        path = find_template(sw, doc_type)
                        result[doc_type] = {"exists": bool(path and Path(path).exists()), "path": str(path or "")}
                    except Exception as exc:
                        result[doc_type] = {"exists": False, "path": "", "message": str(exc)}
        except Exception as exc:
            for doc_type in result:
                result[doc_type]["message"] = str(exc)
        return result

    def _addins(self, attached: bool) -> dict[str, dict[str, Any]]:
        addins = {
            "motion": {"available": False, "message": "未检测到 Motion type library。", "suggestion": "如果需要 Motion 验证，请安装或启用 SolidWorks Motion。"},
            "simulation": {"available": False, "message": "未检测到 Simulation Add-in。", "suggestion": "如需运行 FEA 验证，请安装或启用 SolidWorks Simulation。"},
            "sheet_metal": {"available": True, "message": "Sheet Metal 作为 SolidWorks 特征环境处理，并通过特征可用性验证。"},
            "weldments": {"available": True, "message": "Weldments 作为 SolidWorks 特征环境处理，并通过特征可用性验证。"},
        }
        motion_candidates = []
        for root in [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]:
            if root.exists():
                motion_candidates.extend(root.glob("SOLIDWORKS Corp*/**/swmotionstudy.tlb"))
                motion_candidates.extend(root.glob("Dassault Systemes/**/swmotionstudy.tlb"))
        if motion_candidates:
            addins["motion"] = {"available": True, "message": str(motion_candidates[0]), "suggestion": ""}
        if attached:
            try:
                with solidworks_com_runtime("preflight add-in probe"):
                    sw = RealSolidWorksSession().attach(start_if_missing=False)
                    if not motion_candidates:
                        for dll in Path(r"C:\Program Files").glob("SOLIDWORKS Corp*/**/cmotionswapi.DLL"):
                            try:
                                result = sw.LoadAddIn(str(dll))
                                addins["motion"] = {
                                    "available": result == 0,
                                    "message": f"Motion DLL 加载尝试结果 {result}: {dll}",
                                    "suggestion": "" if result == 0 else "请注册或启用 SolidWorks Motion Add-in。",
                                }
                                break
                            except Exception as exc:
                                addins["motion"] = {
                                    "available": False,
                                    "message": f"Motion DLL 存在但加载失败：{exc}",
                                    "suggestion": "请修复或重新注册 SolidWorks Motion 安装。",
                                }
                    sim = sw.GetAddInObject("SldWorks.Simulation")
                    if not sim:
                        for dll in Path(r"C:\Program Files").glob("SOLIDWORKS Corp*/**/cosworks.dll"):
                            try:
                                sw.LoadAddIn(str(dll))
                                sim = sw.GetAddInObject("SldWorks.Simulation")
                                if sim:
                                    break
                            except Exception:
                                continue
                    addins["simulation"] = {
                        "available": bool(sim),
                        "message": "Simulation Add-in 对象可用。" if sim else "Simulation Add-in 对象返回 None。",
                        "suggestion": "" if sim else "请启用 SolidWorks Simulation，或将 FEA 测试标记为有原因跳过。",
                    }
            except Exception as exc:
                addins["simulation"]["message"] = f"Simulation 探测失败：{exc}"
        return addins

    def _mcp_probe(self) -> dict[str, Any]:
        from sw_ai_backend.mcp.tool_registry import MCPToolRegistry

        tools = MCPToolRegistry().discover()
        return {
            "server_exists": self.paths.solidworks_mcp_server.exists(),
            "tool_count": len(tools),
            "tools": [tool.name for tool in tools],
        }

    def _is_writable(self, path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _check(self, key: str, label: str, ok: bool, message: str, suggestion: str = "") -> PreflightCheck:
        return PreflightCheck(
            key=key,
            label=label,
            status=StatusLevel.PASS if ok else StatusLevel.FAIL,
            message=message,
            suggestion="" if ok else suggestion,
        )

    def _write_reports(self, json_path: Path, md_path: Path, checks: list[PreflightCheck], details: dict[str, Any]) -> None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"checks": [check.model_dump(mode="json") for check in checks], "details": details}
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = ["# SolidWorks 2025 运行前自检", "", f"生成时间：{details['generated_at']}", ""]
        lines.append("| 检查项 | 状态 | 消息 | 建议 |")
        lines.append("|---|---|---|---|")
        for check in checks:
            lines.append(f"| {check.label} | {check.status.value} | {check.message.replace('|', '/')} | {check.suggestion.replace('|', '/')} |")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    response = SolidWorksPreflight().run(write_report=True, start_solidworks=True)
    print(response.report_json)
    print(response.report_markdown)
    print(response.mode)


if __name__ == "__main__":
    main()
