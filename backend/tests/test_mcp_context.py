from pathlib import Path

from sw_ai_backend.api import routes


def test_review_context_prepares_default_part(monkeypatch) -> None:
    prepared: list[tuple[Path, str, str]] = []
    target = Path("C:/tmp/swai-review-context.SLDPRT")

    def fake_ensure_sample_part(path: Path, shape: str, *, radius_mm: float = 10, depth_mm: float = 70, color: str = "#AEB7BC") -> None:
        prepared.append((path, shape, color))

    monkeypatch.setattr(routes, "_ensure_sample_part", fake_ensure_sample_part)

    routes._prepare_mcp_context("solidworks_review_active", {"_default_part_path": str(target)})

    assert prepared == [(target, "box", "#9DA7AA")]


def test_export_context_prepares_default_part(monkeypatch) -> None:
    prepared: list[Path] = []
    target = Path("C:/tmp/swai-export-context.SLDPRT")

    def fake_ensure_sample_part(path: Path, shape: str, *, radius_mm: float = 10, depth_mm: float = 70, color: str = "#AEB7BC") -> None:
        prepared.append(path)

    monkeypatch.setattr(routes, "_ensure_sample_part", fake_ensure_sample_part)

    routes._prepare_mcp_context("solidworks_export_active", {"_default_part_path": str(target)})

    assert prepared == [target]


def test_context_mcp_tool_retries_after_connect(monkeypatch) -> None:
    calls: list[str] = []

    class Runner:
        def run(self, tool_name: str, parameters: dict, raise_on_error_status: bool = False):
            calls.append(tool_name)
            if tool_name == "solidworks_create_basic_part" and calls.count(tool_name) == 1:
                raise RuntimeError("RPC failed")
            return {"tool": tool_name, "parameters": parameters}

    monkeypatch.setattr(routes, "mcp_tool_runner", Runner())
    monkeypatch.setattr(routes.time, "sleep", lambda _seconds: None)

    result = routes._run_context_mcp_tool("solidworks_create_basic_part", {"shape": "box"}, attempts=2)

    assert result == {"tool": "solidworks_create_basic_part", "parameters": {"shape": "box"}}
    assert calls == ["solidworks_create_basic_part", "solidworks_connect", "solidworks_create_basic_part"]
