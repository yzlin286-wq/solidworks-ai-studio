from pathlib import Path
import asyncio

import pytest

from sw_ai_backend.runner.queue import ExecutionQueue, ScriptSafetyError


def test_runner_rejects_shell_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_runner_rejects_shell_patterns(tmp_path, monkeypatch))


async def _test_runner_rejects_shell_patterns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWAI_OUTPUT_DIR", str(tmp_path / "outputs"))
    script_dir = tmp_path / "outputs" / "temp"
    script_dir.mkdir(parents=True)
    script = script_dir / "bad.py"
    script.write_text("import os\nos.system('cmd.exe /c echo unsafe')\n", encoding="utf-8")

    queue = ExecutionQueue()

    with pytest.raises(ScriptSafetyError):
        await queue.submit(str(script), "unsafe", 5)


def test_runner_executes_safe_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_runner_without_real_evidence_fails(tmp_path, monkeypatch))


async def _test_runner_without_real_evidence_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWAI_OUTPUT_DIR", str(tmp_path / "outputs"))
    script_dir = tmp_path / "outputs" / "temp"
    script_dir.mkdir(parents=True)
    script = script_dir / "safe.py"
    script.write_text("print('safe run')\n", encoding="utf-8")

    queue = ExecutionQueue()
    record = await queue.submit(str(script), "safe", 10)

    for _ in range(30):
        current = await queue.store.get(record.run_id)
        if current and current.stage in {"done", "failed"}:
            break
        await asyncio.sleep(0.1)

    current = await queue.store.get(record.run_id)
    assert current is not None
    assert current.stage == "failed"
    assert "safe run" in current.stdout
    assert not current.real_execution_verified


def test_runner_allows_safe_os_environ_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_runner_marks_done_only_with_real_evidence(tmp_path, monkeypatch))


async def _test_runner_marks_done_only_with_real_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWAI_OUTPUT_DIR", str(tmp_path / "outputs"))
    script_dir = tmp_path / "outputs" / "temp"
    script_dir.mkdir(parents=True)
    script = script_dir / "safe_env.py"
    script.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "root = Path(os.environ.get('SWAI_PROJECT_ROOT') or Path.cwd())\n"
        "Path(__file__).with_name('proof.json').write_text('{\"ok\": true}', encoding='utf-8')\n"
        "print(root.name)\n",
        encoding="utf-8",
    )

    queue = ExecutionQueue()

    async def fake_active_document_summary() -> str:
        return "活动文档: proof.sldprt"

    monkeypatch.setattr(queue, "_active_document_summary", fake_active_document_summary)
    record = await queue.submit(str(script), "safe env", 10)

    for _ in range(30):
        current = await queue.store.get(record.run_id)
        if current and current.stage in {"done", "failed"}:
            break
        await asyncio.sleep(0.1)

    current = await queue.store.get(record.run_id)
    assert current is not None
    assert current.stage == "done"
    assert current.real_execution_verified
    assert current.evidence["created_files_exist"] is True
