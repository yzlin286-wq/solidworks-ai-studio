from __future__ import annotations

import asyncio
import contextlib
import io
import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sw_ai_backend.core.paths import output_logs_dir
from sw_ai_backend.models.schemas import ExecutionStatus, SolidWorksExecutionRecord
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession


Operation = Callable[[dict[str, Any]], Any]


class SolidWorksExecutionQueue:
    def __init__(self) -> None:
        self._lane = asyncio.Lock()
        self._records: dict[str, SolidWorksExecutionRecord] = {}
        self._cancelled: set[str] = set()

    async def submit(
        self,
        capability_id: str,
        parameters: dict[str, Any],
        operation: Operation,
        timeout_seconds: int = 180,
    ) -> SolidWorksExecutionRecord:
        run_id = uuid.uuid4().hex
        record = SolidWorksExecutionRecord(
            run_id=run_id,
            capability_id=capability_id,
            parameters=parameters,
            log_path=str(output_logs_dir() / f"{run_id}.json"),
        )
        self._records[run_id] = record
        await self._run(record, operation, timeout_seconds)
        return record

    async def _run(self, record: SolidWorksExecutionRecord, operation: Operation, timeout_seconds: int) -> None:
        async with self._lane:
            if record.run_id in self._cancelled:
                record.status = ExecutionStatus.CANCELLED
                record.finished_at = self._now()
                self._write_log(record)
                return
            record.status = ExecutionStatus.RUNNING
            record.started_at = self._now()
            record.active_document_before = await self._active_document_summary()
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            try:
                async def invoke() -> Any:
                    def work() -> Any:
                        with solidworks_com_runtime(f"capability {record.capability_id}"):
                            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                                return operation(record.parameters)

                    return await asyncio.to_thread(work)

                result = await asyncio.wait_for(invoke(), timeout=timeout_seconds)
                record.stdout = stdout_buffer.getvalue()
                record.stderr = stderr_buffer.getvalue()
                record.created_files = self._created_files_from_result(result)
                record.created_files_exist = self._created_files_exist(record.created_files)
                if isinstance(result, dict):
                    record.stdout += ("\n" if record.stdout else "") + json.dumps(result, ensure_ascii=False, indent=2, default=str)
                elif result is not None:
                    record.stdout += ("\n" if record.stdout else "") + str(result)
                record.status = ExecutionStatus.PASSED
            except asyncio.TimeoutError:
                record.status = ExecutionStatus.FAILED
                record.stderr = stderr_buffer.getvalue()
                record.error_summary = f"Timed out after {timeout_seconds} seconds."
            except Exception as exc:
                record.status = ExecutionStatus.FAILED
                record.stdout = stdout_buffer.getvalue()
                record.stderr = stderr_buffer.getvalue() + "\n" + traceback.format_exc()
                record.error_summary = str(exc)
            finally:
                record.finished_at = self._now()
                record.active_document_after = await self._active_document_summary()
                record.evidence = {
                    "active_document_before": record.active_document_before,
                    "active_document_after": record.active_document_after,
                    "created_files": record.created_files,
                    "created_files_exist": record.created_files_exist,
                    "stdout_present": bool(record.stdout.strip()),
                    "stderr_present": bool(record.stderr.strip()),
                }
                record.real_execution_verified = self._real_evidence_ok(record)
                self._write_log(record)

    def get(self, run_id: str) -> SolidWorksExecutionRecord | None:
        return self._records.get(run_id)

    def all(self) -> list[SolidWorksExecutionRecord]:
        return list(self._records.values())

    def cancel(self, run_id: str) -> SolidWorksExecutionRecord | None:
        self._cancelled.add(run_id)
        record = self._records.get(run_id)
        if record and record.status == ExecutionStatus.QUEUED:
            record.status = ExecutionStatus.CANCELLED
            record.finished_at = self._now()
            self._write_log(record)
        return record

    def _created_files_from_result(self, result: Any) -> list[str]:
        files: list[str] = []
        if isinstance(result, dict):
            for key in ["files", "created_files", "output_path", "drawing_path", "path", "report_path"]:
                value = result.get(key)
                if isinstance(value, str):
                    files.append(value)
                elif isinstance(value, list):
                    files.extend(str(item) for item in value)
        return sorted(set(files))

    def _created_files_exist(self, files: list[str]) -> bool:
        if not files:
            return False
        return all(Path(file_path).is_file() for file_path in files)

    def _real_evidence_ok(self, record: SolidWorksExecutionRecord) -> bool:
        active_after = record.active_document_after or ""
        active_readable = bool(active_after) and "未连接" not in active_after and "读取失败" not in active_after
        file_evidence = bool(record.created_files) and record.created_files_exist
        state_evidence = active_readable and bool(record.stdout.strip())
        return record.status == ExecutionStatus.PASSED and (file_evidence or state_evidence)

    def _write_log(self, record: SolidWorksExecutionRecord) -> None:
        path = Path(record.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    async def _active_document_summary(self) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(RealSolidWorksSession().active_document_summary),
                timeout=5,
            )
        except Exception:
            return ""

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)
