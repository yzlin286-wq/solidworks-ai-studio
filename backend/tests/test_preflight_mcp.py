import asyncio
import time

from sw_ai_backend.mcp.manager import MCPManager
from sw_ai_backend.models.schemas import PreflightCheck, PreflightResponse, SolidWorksSessionResponse, StatusLevel
from sw_ai_backend.api import routes
from sw_ai_backend.solidworks import service as service_module
from sw_ai_backend.solidworks.service import SolidWorksService
from fastapi import HTTPException
import pytest


def test_preflight_returns_checks_without_solidworks(monkeypatch) -> None:
    def fake_run(self, write_report: bool = True, start_solidworks: bool = True) -> PreflightResponse:
        return PreflightResponse(
            mode="mock",
            checks=[
                PreflightCheck(
                    key="skill-path",
                    label="SolidWorks automation Skill 路径",
                    status=StatusLevel.PASS,
                    message="mock skill path",
                )
            ],
            can_run_real_com=False,
            solidworks_version="",
            report_json="",
            report_markdown="",
        )

    monkeypatch.setattr(service_module.SolidWorksPreflight, "run", fake_run)

    response = SolidWorksService().preflight()

    assert response.checks
    assert response.mode in {"solidworks", "mock"}
    assert any(check.key == "skill-path" for check in response.checks)


def test_async_preflight_timeout_returns_warning(monkeypatch) -> None:
    def slow_run(self, write_report: bool = True, start_solidworks: bool = True) -> PreflightResponse:
        time.sleep(0.2)
        return PreflightResponse(
            mode="solidworks",
            checks=[],
            can_run_real_com=True,
            solidworks_version="33.0",
            report_json="",
            report_markdown="",
        )

    monkeypatch.setattr(service_module.SolidWorksPreflight, "run", slow_run)
    monkeypatch.setattr(
        service_module.RealSolidWorksSession,
        "status",
        lambda self, start_if_missing=False: SolidWorksSessionResponse(
            attached=False,
            visible=False,
            message="not connected",
        ),
    )
    service = SolidWorksService()
    try:
        response = asyncio.run(service.preflight_async(timeout_seconds=0.01))
    finally:
        service._preflight_executor.shutdown(wait=True, cancel_futures=True)

    assert response.mode == "mock"
    assert response.state == "timeout"
    assert response.stale
    assert not response.can_run_real_com
    assert any(check.key == "solidworks-preflight-timeout" for check in response.checks)


def test_async_preflight_timeout_uses_lightweight_session_probe(monkeypatch) -> None:
    def slow_run(self, write_report: bool = True, start_solidworks: bool = True) -> PreflightResponse:
        time.sleep(0.2)
        return PreflightResponse(
            mode="mock",
            checks=[],
            can_run_real_com=False,
            solidworks_version="",
            report_json="",
            report_markdown="",
        )

    monkeypatch.setattr(service_module.SolidWorksPreflight, "run", slow_run)
    monkeypatch.setattr(
        service_module.RealSolidWorksSession,
        "status",
        lambda self, start_if_missing=False: SolidWorksSessionResponse(
            attached=True,
            visible=True,
            version="33.5.0",
            message="session ready",
        ),
    )
    service = SolidWorksService()
    try:
        response = asyncio.run(service.preflight_async(timeout_seconds=0.01))
    finally:
        service._preflight_executor.shutdown(wait=True, cancel_futures=True)

    assert response.mode == "solidworks"
    assert response.can_run_real_com
    assert response.state == "timeout-session-ready"
    assert response.stale
    assert response.solidworks_version == "33.5.0"


def test_mcp_snippets_include_supported_clients() -> None:
    snippets = MCPManager().snippets()

    assert "Codex" in snippets.snippets
    assert "Claude Desktop" in snippets.snippets
    assert snippets.server_path.endswith("server.py")


def test_mcp_action_blocks_when_preflight_cannot_run_real_com(monkeypatch) -> None:
    async def blocked_preflight(timeout_seconds: int = 5):
        return PreflightResponse(
            mode="mock",
            checks=[
                PreflightCheck(
                    key="solidworks",
                    label="SolidWorks COM",
                    status=StatusLevel.FAIL,
                    message="not connected",
                )
            ],
            can_run_real_com=False,
            solidworks_version="",
            report_json="",
            report_markdown="",
            state="error",
        )

    monkeypatch.setattr(routes.solidworks_service, "preflight_async", blocked_preflight)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes._run_mcp_action("connect", "solidworks_connect", {}))

    assert exc.value.status_code == 424
