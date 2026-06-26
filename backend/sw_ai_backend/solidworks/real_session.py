from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import skill_paths
from sw_ai_backend.models.schemas import SolidWorksSessionResponse
from sw_ai_backend.solidworks.com_runtime import ensure_com_initialized, solidworks_com_runtime


DOC_TYPES = {
    -1: "未知",
    1: "零件",
    2: "装配体",
    3: "工程图",
}


class SolidWorksConnectionError(RuntimeError):
    pass


@dataclass
class RealSolidWorksSession:
    visible: bool = True

    def attach(self, start_if_missing: bool = True) -> Any:
        if not platform.system().lower().startswith("windows"):
            raise SolidWorksConnectionError("SolidWorks COM 仅在 Windows 上可用。")
        try:
            import win32com.client
        except ModuleNotFoundError as exc:
            raise SolidWorksConnectionError("SolidWorks COM 自动化需要 pywin32。") from exc

        ensure_com_initialized("SolidWorks session attach")
        sw = None
        try:
            sw = win32com.client.GetActiveObject("SldWorks.Application")
        except Exception:
            if not start_if_missing:
                raise SolidWorksConnectionError("当前没有可用的 SolidWorks COM 会话。")
        if sw is None:
            try:
                sw = win32com.client.Dispatch("SldWorks.Application")
                sw.Visible = self.visible
            except Exception as exc:
                raise SolidWorksConnectionError(f"无法通过 COM 启动 SolidWorks：{exc}") from exc
        try:
            sw.Visible = self.visible
        except Exception:
            pass
        return sw

    def status(self, start_if_missing: bool = False) -> SolidWorksSessionResponse:
        try:
            with solidworks_com_runtime("SolidWorks session status"):
                sw = self.attach(start_if_missing=start_if_missing)
                active = getattr(sw, "ActiveDoc", None)
                title = ""
                doc_type = ""
                if active is not None:
                    try:
                        title = str(active.GetTitle())
                    except Exception:
                        title = ""
                    try:
                        doc_type = DOC_TYPES.get(int(active.GetType()), str(active.GetType()))
                    except Exception:
                        doc_type = "未知"
                return SolidWorksSessionResponse(
                    attached=True,
                    visible=bool(getattr(sw, "Visible", True)),
                    version=self._safe_call(sw, "RevisionNumber"),
                    revision=self._safe_call(sw, "RevisionNumber"),
                    executable_path=self._safe_call(sw, "GetExecutablePath"),
                    active_document_title=title,
                    active_document_type=doc_type,
                    message="SolidWorks COM 会话已连接。",
                )
        except Exception as exc:
            return SolidWorksSessionResponse(
                attached=False,
                visible=False,
                message=f"SolidWorks COM 会话未连接：{exc}",
            )

    def detach(self) -> SolidWorksSessionResponse:
        return SolidWorksSessionResponse(
            attached=False,
            visible=False,
            message="已从 SolidWorks 分离，桌面应用保持运行。",
        )

    def active_document_summary(self) -> str:
        try:
            status = self.status(start_if_missing=False)
            if not status.attached:
                return status.message
            return f"{status.active_document_type}:{status.active_document_title}"
        except Exception as exc:
            return f"SolidWorks COM 状态读取失败：{exc}"

    def _safe_call(self, sw: Any, name: str) -> str:
        try:
            value = getattr(sw, name)
            if callable(value):
                value = value()
            return str(value or "")
        except Exception:
            return ""


def ensure_skill_import_path() -> None:
    import sys

    scripts = skill_paths().solidworks_scripts
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


def safe_output_path(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    return output
