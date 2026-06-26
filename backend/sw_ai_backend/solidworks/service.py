from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import importlib.util
import platform
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sw_ai_backend.core.paths import skill_paths, user_outputs_dir
from sw_ai_backend.models.schemas import PreflightCheck, PreflightResponse, SolidWorksActionResponse, StatusLevel
from sw_ai_backend.solidworks.preflight import SolidWorksPreflight
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession, SolidWorksSessionResponse


class SolidWorksService:
    def __init__(self) -> None:
        self.paths = skill_paths()
        self._preflight_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="swai-preflight")
        self._preflight_lock = threading.RLock()
        self._preflight_future: Future[PreflightResponse] | None = None
        self._preflight_started_at = 0.0
        self._preflight_started_wall: datetime | None = None
        self._last_preflight: PreflightResponse | None = None
        self._last_preflight_error = ""

    def preflight(self) -> PreflightResponse:
        return SolidWorksPreflight().run(write_report=True, start_solidworks=True)

    async def preflight_async(self, timeout_seconds: int = 45) -> PreflightResponse:
        future = self._ensure_preflight_future()
        with self._preflight_lock:
            elapsed = time.monotonic() - self._preflight_started_at if future is self._preflight_future else 0.0
            if future is self._preflight_future and not future.done() and elapsed >= timeout_seconds:
                probe, probe_error = await self._probe_existing_session()
                return self._preflight_timeout_response(timeout_seconds, elapsed, probe, probe_error)
        try:
            response = await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout=timeout_seconds)
            self._remember_preflight_result(response)
            return response
        except asyncio.TimeoutError:
            with self._preflight_lock:
                elapsed = time.monotonic() - self._preflight_started_at if future is self._preflight_future else timeout_seconds
            probe, probe_error = await self._probe_existing_session()
            return self._preflight_timeout_response(timeout_seconds, elapsed, probe, probe_error)
        except Exception as exc:
            return self._preflight_error_response(exc)

    def _ensure_preflight_future(self) -> Future[PreflightResponse]:
        with self._preflight_lock:
            if self._preflight_future is not None and self._preflight_future.done():
                self._harvest_preflight_future(self._preflight_future)
            if self._preflight_future is None:
                self._preflight_started_at = time.monotonic()
                self._preflight_started_wall = datetime.now(timezone.utc)
                self._preflight_future = self._preflight_executor.submit(self.preflight)
                self._preflight_future.add_done_callback(self._preflight_done)
            return self._preflight_future

    def _preflight_done(self, future: Future[PreflightResponse]) -> None:
        with self._preflight_lock:
            self._harvest_preflight_future(future)

    def _harvest_preflight_future(self, future: Future[PreflightResponse]) -> None:
        try:
            response = future.result()
            self._remember_preflight_result(response)
            self._last_preflight_error = ""
        except Exception as exc:
            self._last_preflight_error = str(exc)
        finally:
            if future is self._preflight_future:
                self._preflight_future = None

    def _remember_preflight_result(self, response: PreflightResponse) -> None:
        with self._preflight_lock:
            self._last_preflight = response

    async def _probe_existing_session(self, timeout_seconds: float = 3.0) -> tuple[SolidWorksSessionResponse | None, str]:
        try:
            status = await asyncio.wait_for(
                asyncio.to_thread(lambda: RealSolidWorksSession().status(start_if_missing=False)),
                timeout=timeout_seconds,
            )
            return status, ""
        except Exception as exc:
            return None, str(exc)

    def _preflight_timeout_response(
        self,
        timeout_seconds: int,
        elapsed_seconds: float,
        session_probe: SolidWorksSessionResponse | None = None,
        session_probe_error: str = "",
    ) -> PreflightResponse:
        cached = self._last_preflight
        can_run_real = bool(session_probe and session_probe.attached)
        mode = "solidworks" if can_run_real else "mock"
        version = (session_probe.version if session_probe and session_probe.version else "") or (cached.solidworks_version if cached else "")
        checks = [
            PreflightCheck(
                key="solidworks-preflight-timeout",
                label="SolidWorks preflight",
                status=StatusLevel.WARN,
                message=f"SolidWorks COM preflight 已运行 {elapsed_seconds:.0f} 秒，超过 {timeout_seconds} 秒未返回。该结果标记为 stale，不会被当作完整真实自检通过。",
                suggestion="请检查 SolidWorks 是否有阻塞弹窗；关闭弹窗或重启 SolidWorks 后再点击刷新检查。",
            )
        ]
        if session_probe is not None:
            checks.append(
                PreflightCheck(
                    key="solidworks-session-probe",
                    label="轻量 SolidWorks 会话探测",
                    status=StatusLevel.PASS if session_probe.attached else StatusLevel.WARN,
                    message=session_probe.message,
                    suggestion="" if session_probe.attached else "轻量探测未连接真实会话，因此真实工具会被阻断。",
                )
            )
        elif session_probe_error:
            checks.append(
                PreflightCheck(
                    key="solidworks-session-probe",
                    label="轻量 SolidWorks 会话探测",
                    status=StatusLevel.WARN,
                    message=f"轻量探测失败：{session_probe_error}",
                    suggestion="请确认 SolidWorks 已启动且没有阻塞对话框。",
                )
            )
        if cached is not None:
            checks.append(
                PreflightCheck(
                    key="solidworks-preflight-cache",
                    label="上次 preflight 结果",
                    status=StatusLevel.WARN,
                    message=f"已保留上次结果：{cached.mode}，SolidWorks version {cached.solidworks_version or '未知'}。",
                    suggestion="当前结果为超时保护，真实状态以再次刷新后的完整 preflight 为准。",
                )
            )
        return PreflightResponse(
            mode=mode,
            checks=checks,
            can_run_real_com=can_run_real,
            solidworks_version=version,
            report_json=cached.report_json if cached else "",
            report_markdown=cached.report_markdown if cached else "",
            state="timeout-session-ready" if can_run_real else "timeout",
            stale=True,
            started_at=self._preflight_started_wall,
            finished_at=datetime.now(timezone.utc),
            elapsed_seconds=round(elapsed_seconds, 3),
        )

    def _preflight_error_response(self, exc: Exception) -> PreflightResponse:
        cached = self._last_preflight
        return PreflightResponse(
            mode="mock",
            checks=[
                PreflightCheck(
                    key="solidworks-preflight-error",
                    label="SolidWorks preflight",
                    status=StatusLevel.WARN,
                    message=f"SolidWorks preflight 执行失败：{exc}",
                    suggestion="请检查 SolidWorks、pywin32/comtypes 和 automation Skill 路径后重新刷新。",
                )
            ],
            can_run_real_com=False,
            solidworks_version=cached.solidworks_version if cached else "",
            report_json=cached.report_json if cached else "",
            report_markdown=cached.report_markdown if cached else "",
            state="error",
            stale=True,
            finished_at=datetime.now(timezone.utc),
        )

    def connect(self) -> SolidWorksActionResponse:
        return self._call_session("connect", lambda session: {"title": getattr(session.active_doc, "GetTitle", lambda: "没有活动文档")()})

    def new_part(self, parameters: dict[str, Any]) -> SolidWorksActionResponse:
        return self._call_session("new_part", lambda session: {"document": session.new_part().GetTitle()})

    def open_document(self, path: str) -> SolidWorksActionResponse:
        return self._call_session("open", lambda session: {"document": session.open(path).GetTitle()})

    def save_document(self, path: str = "") -> SolidWorksActionResponse:
        return self._call_session("save", lambda session: {"saved": bool(session.save(file_path=path or None)), "path": path})

    def export_active(self, output_path: str, format_ext: str) -> SolidWorksActionResponse:
        target = output_path or str(user_outputs_dir() / f"active.{format_ext.lower().lstrip('.')}")
        return self._call_session(
            "export",
            lambda session: {"exported": bool(session.export(output_path=target, format_ext=format_ext)), "path": target},
            files=[target],
        )

    def review_active(self, output_path: str = "") -> SolidWorksActionResponse:
        target = Path(output_path or str(user_outputs_dir() / "review"))
        return self._call_script_function(
            "review",
            "sw_review",
            "run_review",
            args=[],
            files=[str(target)],
            fallback_message="审查需要活动 SolidWorks 模型。",
        )

    def create_basic_part(self, parameters: dict[str, Any]) -> SolidWorksActionResponse:
        shape = str(parameters.get("shape", "box"))
        return self._blocked(
            "create_basic_part",
            f"基础 {shape} 零件必须通过真实 MCP solidworks_create_basic_part 执行，当前入口已拒绝非真实执行。",
            data={"parameters": parameters},
        )

    def _dependency_check(self) -> list[PreflightCheck]:
        missing = []
        for module in ["comtypes", "pythoncom", "win32com.client"]:
            if importlib.util.find_spec(module) is None:
                missing.append(module)
        return [
            PreflightCheck(
                key="python-com",
                label="Python COM 依赖",
                status=StatusLevel.PASS if not missing else StatusLevel.WARN,
                message="pywin32 和 comtypes 可导入。" if not missing else f"缺少：{', '.join(missing)}",
                suggestion="" if not missing else '请安装：python -m pip install "pywin32>=305" "comtypes>=1.2.0"',
            )
        ]

    def _solidworks_ready(self) -> PreflightCheck:
        if not platform.system().lower().startswith("windows"):
            return PreflightCheck(
                key="solidworks",
                label="SolidWorks COM",
                status=StatusLevel.WARN,
                message="非 Windows 环境无法使用 SolidWorks COM。",
                suggestion="请切换到可用的 Windows CAD 工作站运行。",
            )
        try:
            sys.path.insert(0, str(self.paths.solidworks_scripts))
            import sw_preflight

            installed = bool(sw_preflight.solidworks_installed())
            return PreflightCheck(
                key="solidworks",
                label="SolidWorks COM",
                status=StatusLevel.PASS if installed else StatusLevel.WARN,
                message="检测到 SolidWorks 安装或 COM 注册。" if installed else "未检测到 SolidWorks。",
                suggestion="" if installed else "请安装并启动一次 SolidWorks，以完成 COM 注册。",
            )
        except Exception as exc:
            return PreflightCheck(
                key="solidworks",
                label="SolidWorks COM",
                status=StatusLevel.WARN,
                message=f"Preflight wrapper 无法验证 SolidWorks：{exc}",
                suggestion="请检查 vendor/skills/solidworks-automation/scripts/sw_preflight.py。",
            )

    def _call_session(
        self,
        action: str,
        operation: Callable[[Any], dict[str, Any]],
        files: list[str] | None = None,
    ) -> SolidWorksActionResponse:
        preflight = self.preflight()
        if not preflight.can_run_real_com:
            return self._blocked(action, f"{action} 需要真实 SolidWorks COM 会话；当前 preflight 未通过。", files=files)
        try:
            sys.path.insert(0, str(self.paths.solidworks_scripts))
            from sw_session import SolidWorksSession

            session = SolidWorksSession()
            data = operation(session)
            return SolidWorksActionResponse(ok=True, mode="solidworks", action=action, message=f"{action} 已完成。", files=files or [], data=data)
        except Exception as exc:
            return SolidWorksActionResponse(ok=False, mode="solidworks", action=action, message=f"{action} 失败：{exc}", stderr=str(exc))

    def _call_script_function(
        self,
        action: str,
        module_name: str,
        function_name: str,
        args: list[Any],
        files: list[str],
        fallback_message: str,
    ) -> SolidWorksActionResponse:
        preflight = self.preflight()
        if not preflight.can_run_real_com:
            return self._blocked(action, fallback_message, files=files)
        try:
            sys.path.insert(0, str(self.paths.solidworks_scripts))
            module = __import__(module_name, fromlist=[function_name])
            function = getattr(module, function_name)
            data = function(*args)
            return SolidWorksActionResponse(ok=True, mode="solidworks", action=action, message=f"{action} 已完成。", files=files, data={"result": data})
        except Exception as exc:
            return SolidWorksActionResponse(ok=False, mode="solidworks", action=action, message=f"{action} 失败：{exc}", stderr=str(exc))

    def _blocked(
        self,
        action: str,
        message: str,
        files: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> SolidWorksActionResponse:
        return SolidWorksActionResponse(
            ok=False,
            mode="solidworks",
            action=action,
            message=message,
            stderr=message,
            files=files or [],
            data=data or {},
            real_execution_verified=False,
        )
