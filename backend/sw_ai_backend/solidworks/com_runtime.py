from __future__ import annotations

from contextlib import contextmanager
import sys
import threading
from types import ModuleType
from typing import Iterator


class COMRuntimeError(RuntimeError):
    pass


_state = threading.local()


def ensure_com_initialized(reason: str) -> ModuleType:
    pythoncom = getattr(_state, "pythoncom", None)
    if getattr(_state, "initialized", False) and pythoncom is not None:
        return pythoncom
    try:
        import pythoncom as pythoncom_module
    except Exception as exc:
        raise COMRuntimeError(f"COM runtime unavailable for {reason}: {exc}") from exc
    try:
        pythoncom_module.CoInitialize()
    except Exception as exc:
        raise COMRuntimeError(f"COM initialization failed for {reason}: {exc}") from exc
    _state.pythoncom = pythoncom_module
    _state.initialized = True
    return pythoncom_module


@contextmanager
def solidworks_com_runtime(reason: str) -> Iterator[None]:
    initialized_before = bool(getattr(_state, "initialized", False))
    depth = int(getattr(_state, "depth", 0))
    if not initialized_before:
        ensure_com_initialized(reason)
    _state.depth = depth + 1
    try:
        yield
    finally:
        _state.depth = max(0, int(getattr(_state, "depth", 1)) - 1)
        if not initialized_before and _state.depth == 0:
            pythoncom = getattr(_state, "pythoncom", None)
            try:
                if pythoncom is not None:
                    pythoncom.CoUninitialize()
            except Exception as exc:
                if sys.exc_info()[0] is None:
                    raise COMRuntimeError(f"COM uninitialization failed for {reason}: {exc}") from exc
                print(f"[swai-com] COM uninitialization failed for {reason}: {exc}", file=sys.stderr)
            finally:
                _state.initialized = False
                _state.pythoncom = None
