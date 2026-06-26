from pathlib import Path

from sw_ai_backend.runner.queue import ExecutionQueue


def test_discover_outputs_only_scans_current_script_directory(tmp_path: Path) -> None:
    current = tmp_path / "current"
    historical = tmp_path / "historical"
    current.mkdir()
    historical.mkdir()
    script = current / "task.py"
    script.write_text("print('ok')", encoding="utf-8")
    expected = current / "part.SLDPRT"
    expected.write_text("part", encoding="utf-8")
    nested = current / "outputs" / "review.json"
    nested.parent.mkdir()
    nested.write_text("{}", encoding="utf-8")
    old = historical / "old.STEP"
    old.write_text("old", encoding="utf-8")

    files = ExecutionQueue()._discover_outputs(script)

    assert str(expected) in files
    assert str(nested) in files
    assert str(old) not in files
