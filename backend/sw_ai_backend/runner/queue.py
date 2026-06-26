from __future__ import annotations

import asyncio
import ast
import contextlib
import io
import os
import runpy
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import is_relative_to, project_root, user_temp_dir
from sw_ai_backend.models.schemas import RunEvent, RunRecord, RunStage
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession


class ScriptSafetyError(ValueError):
    pass


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, prompt: str, script_path: str) -> RunRecord:
        async with self._lock:
            run_id = uuid.uuid4().hex
            record = RunRecord(
                run_id=run_id,
                stage=RunStage.QUEUED,
                prompt=prompt,
                script_path=script_path,
                events=[RunEvent(stage=RunStage.QUEUED, message="Run 已进入 SolidWorks 串行执行通道。")],
            )
            self._runs[run_id] = record
            return record

    async def update(
        self,
        run_id: str,
        stage: RunStage,
        message: str,
        stdout: str = "",
        stderr: str = "",
        files: list[str] | None = None,
        evidence: dict[str, Any] | None = None,
        real_execution_verified: bool | None = None,
    ) -> RunRecord:
        async with self._lock:
            record = self._runs[run_id]
            record.stage = stage
            record.stdout += stdout
            record.stderr += stderr
            if files:
                record.files.extend(files)
            if evidence is not None:
                record.evidence = evidence
            if real_execution_verified is not None:
                record.real_execution_verified = real_execution_verified
            record.events.append(RunEvent(stage=stage, message=message, stdout=stdout, stderr=stderr))
            return record

    async def get(self, run_id: str) -> RunRecord | None:
        async with self._lock:
            return self._runs.get(run_id)


class ExecutionQueue:
    def __init__(self, store: RunStore | None = None) -> None:
        self.store = store or RunStore()
        self._com_lane = asyncio.Lock()

    async def submit(self, script_path: str, prompt: str, timeout_seconds: int, evidence_output_dir: str | None = None) -> RunRecord:
        path = self._validate_script_path(script_path)
        record = await self.store.create(prompt=prompt, script_path=str(path))
        asyncio.create_task(self._run(record.run_id, path, timeout_seconds, evidence_output_dir))
        return record

    async def _run(self, run_id: str, path: Path, timeout_seconds: int, evidence_output_dir: str | None = None) -> None:
        async with self._com_lane:
            await self.store.update(run_id, RunStage.RUNNING, "已审批的 Script 开始执行。")
            try:
                execution_started_at = time.time()
                active_document_before = await self._active_document_summary()
                if getattr(sys, "frozen", False):
                    returncode, stdout, stderr = await asyncio.wait_for(
                        asyncio.to_thread(self._execute_in_current_process, path),
                        timeout=timeout_seconds,
                    )
                else:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        str(path),
                        cwd=str(project_root()),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout_seconds,
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                    returncode = int(process.returncode or 0)
                if returncode == 0:
                    files = self._discover_outputs(path, evidence_output_dir, since=execution_started_at)
                    active_document_after = await self._active_document_summary()
                    evidence = {
                        "active_document_before": active_document_before,
                        "active_document_after": active_document_after,
                        "created_files": files,
                        "created_files_exist": all(Path(file_path).is_file() for file_path in files) if files else False,
                    }
                    real_verified = self._real_evidence_ok(evidence)
                    if not real_verified:
                        await self.store.update(
                            run_id,
                            RunStage.FAILED,
                            "Script 已退出，但没有可核验的真实 SolidWorks 输出证据。",
                            stdout=stdout,
                            stderr=stderr,
                            evidence=evidence,
                            real_execution_verified=False,
                        )
                        return
                    await self.store.update(
                        run_id,
                        RunStage.DONE,
                        "Script 执行完成。",
                        stdout=stdout,
                        stderr=stderr,
                        files=files,
                        evidence=evidence,
                        real_execution_verified=True,
                    )
                else:
                    await self.store.update(
                        run_id,
                        RunStage.FAILED,
                        f"Script 退出码为 {returncode}。",
                        stdout=stdout,
                        stderr=stderr,
                    )
            except asyncio.TimeoutError:
                await self.store.update(run_id, RunStage.FAILED, "Script 执行超时。", stderr="执行超时。")
            except Exception as exc:
                await self.store.update(run_id, RunStage.FAILED, f"Script 执行失败：{exc}", stderr=str(exc))

    def _execute_in_current_process(self, path: Path) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        previous_argv = sys.argv[:]
        previous_cwd = Path.cwd()
        try:
            with solidworks_com_runtime(f"generated script {path}"):
                sys.argv = [str(path)]
                os.chdir(project_root())
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    try:
                        runpy.run_path(str(path), run_name="__main__")
                        return 0, stdout.getvalue(), stderr.getvalue()
                    except SystemExit as exc:
                        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
                        return int(code), stdout.getvalue(), stderr.getvalue()
        except Exception as exc:
            return 1, stdout.getvalue(), stderr.getvalue() + str(exc)
        finally:
            sys.argv = previous_argv
            os.chdir(previous_cwd)

    def _validate_script_path(self, script_path: str) -> Path:
        path = Path(script_path).expanduser().resolve()
        if path.suffix.lower() != ".py":
            raise ScriptSafetyError("只能执行 Python Script。")
        allowed_roots = [project_root().resolve(), user_temp_dir().resolve()]
        if not any(is_relative_to(path, root) for root in allowed_roots):
            raise ScriptSafetyError("Script 必须位于项目目录或 SolidWorks AI Studio 临时目录内。")
        if not path.exists():
            raise ScriptSafetyError("Script 路径不存在。")
        text = path.read_text(encoding="utf-8", errors="replace")
        if self._has_blocked_python_construct(text):
            raise ScriptSafetyError("Script 包含被禁止的 shell 或破坏性命令模式。")
        return path

    def _has_blocked_python_construct(self, text: str) -> bool:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return True
        blocked_import_roots = {"subprocess"}
        blocked_names = {"eval", "exec", "compile", "__import__"}
        blocked_attr_calls = {
            ("os", "system"),
            ("os", "popen"),
            ("shutil", "rmtree"),
            ("pathlib", "Path.unlink"),
            ("pathlib", "Path.rmdir"),
        }

        def dotted_name(node: ast.AST) -> str:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                parent = dotted_name(node.value)
                return f"{parent}.{node.attr}" if parent else node.attr
            return ""

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in blocked_import_roots:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".", 1)[0] in blocked_import_roots:
                    return True
            elif isinstance(node, ast.Call):
                call_name = dotted_name(node.func)
                if call_name in blocked_names:
                    return True
                if "." in call_name:
                    root, attr = call_name.split(".", 1)
                    if (root, attr) in blocked_attr_calls:
                        return True
        return False

    def _discover_outputs(self, script_path: Path, evidence_output_dir: str | None = None, since: float | None = None) -> list[str]:
        candidates = []
        folders = [script_path.parent]
        if evidence_output_dir:
            folders.append(Path(evidence_output_dir).expanduser())
        for folder in folders:
            if folder.exists():
                for path in folder.rglob("*"):
                    if not path.is_file() or path.suffix.lower() not in {".json", ".sldprt", ".sldasm", ".step", ".stp", ".stl", ".pdf", ".dxf", ".dwg", ".bmp", ".png"}:
                        continue
                    if since is not None and path.stat().st_mtime < since - 1:
                        continue
                    candidates.append(str(path))
        return sorted(set(candidates))[:24]

    async def _active_document_summary(self) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(RealSolidWorksSession().active_document_summary),
                timeout=5,
            )
        except Exception as exc:
            return f"SolidWorks 活动文档读取失败：{exc}"

    def _real_evidence_ok(self, evidence: dict[str, object]) -> bool:
        files = evidence.get("created_files")
        active_after = str(evidence.get("active_document_after") or "")
        has_files = bool(files) and bool(evidence.get("created_files_exist"))
        active_readable = bool(active_after) and "未连接" not in active_after and "读取失败" not in active_after
        return has_files and active_readable
