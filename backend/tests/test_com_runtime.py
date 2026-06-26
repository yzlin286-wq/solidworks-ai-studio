from types import SimpleNamespace
import sys

from sw_ai_backend.solidworks import com_runtime


def _reset_state() -> None:
    for name in ["pythoncom", "initialized", "depth"]:
        if hasattr(com_runtime._state, name):
            delattr(com_runtime._state, name)


def test_solidworks_com_runtime_initializes_and_releases(monkeypatch) -> None:
    _reset_state()
    calls: list[str] = []
    fake_pythoncom = SimpleNamespace(
        CoInitialize=lambda: calls.append("init"),
        CoUninitialize=lambda: calls.append("uninit"),
    )
    monkeypatch.setitem(sys.modules, "pythoncom", fake_pythoncom)

    with com_runtime.solidworks_com_runtime("test"):
        assert calls == ["init"]

    assert calls == ["init", "uninit"]
    _reset_state()


def test_solidworks_com_runtime_raises_initialization_reason(monkeypatch) -> None:
    _reset_state()

    def fail_init() -> None:
        raise RuntimeError("boom")

    fake_pythoncom = SimpleNamespace(CoInitialize=fail_init, CoUninitialize=lambda: None)
    monkeypatch.setitem(sys.modules, "pythoncom", fake_pythoncom)

    try:
        with com_runtime.solidworks_com_runtime("preflight"):
            pass
    except com_runtime.COMRuntimeError as exc:
        assert "preflight" in str(exc)
        assert "boom" in str(exc)
    else:
        raise AssertionError("COMRuntimeError was not raised")
    finally:
        _reset_state()
