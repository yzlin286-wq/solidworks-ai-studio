from pathlib import Path
import asyncio

import pytest

from sw_ai_backend.llm.client import LLMClient, LLMConfigurationError, LLMResponseError
from sw_ai_backend.models.schemas import LLMProfile


def test_llm_without_key_refuses_generation(tmp_path: Path) -> None:
    asyncio.run(_test_llm_without_key_refuses_generation(tmp_path))


async def _test_llm_without_key_refuses_generation(tmp_path: Path) -> None:
    profile = LLMProfile(
        id="local",
        name="Local",
        api_base_url="http://127.0.0.1:1234/v1",
        model="demo",
    )
    client = LLMClient(profile)

    ok, message, latency, models, models_verified, chat_verified = await client.test_connection()

    assert not ok
    assert "API Key" in message
    assert latency is None
    assert models == []
    assert not models_verified
    assert not chat_verified
    with pytest.raises(LLMConfigurationError):
        await client.generate_plan("Create a bracket", "skill context", str(tmp_path))
    with pytest.raises(LLMConfigurationError):
        await client.generate_script("Create a bracket", "skill context", str(tmp_path), tmp_path / "task.py")
    vision_ok, vision_message, vision_latency, vision_model, vision_verified = await client.test_vision_connection()
    assert not vision_ok
    assert "API Key" in vision_message
    assert vision_latency is None
    assert vision_model == "demo"
    assert not vision_verified


def test_empty_provider_script_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_empty_provider_script_is_rejected(tmp_path, monkeypatch))


async def _test_empty_provider_script_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(_provider_profile())

    async def empty_chat(messages):
        return ""

    monkeypatch.setattr(client, "_chat", empty_chat)

    with pytest.raises(LLMResponseError):
        await client.generate_script("Create a bracket", "skill context", str(tmp_path), tmp_path / "task.py")


def test_non_json_provider_response_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_non_json_provider_response_is_rejected(tmp_path, monkeypatch))


async def _test_non_json_provider_response_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(_provider_profile())

    async def prose_chat(messages):
        return "Sure, here is a plan without JSON."

    monkeypatch.setattr(client, "_chat", prose_chat)

    with pytest.raises(LLMResponseError):
        await client.generate_plan("Create a bracket", "skill context", str(tmp_path))


def test_non_object_provider_json_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_non_object_provider_json_is_rejected(tmp_path, monkeypatch))


async def _test_non_object_provider_json_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(_provider_profile())

    async def array_chat(messages):
        return "[1, 2, 3]"

    monkeypatch.setattr(client, "_chat", array_chat)

    with pytest.raises(LLMResponseError):
        await client.generate_plan("Create a bracket", "skill context", str(tmp_path))


def test_valid_provider_script_has_no_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_valid_provider_script_has_no_fallback(tmp_path, monkeypatch))


def test_hard_coded_approval_gate_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asyncio.run(_test_hard_coded_approval_gate_is_rejected(tmp_path, monkeypatch))


async def _test_hard_coded_approval_gate_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(_provider_profile())

    async def json_chat(messages):
        return (
            '{"plan":"create real part","risks":[],"required_files":[],'
            '"script":"APPROVED_BY_HUMAN = False\\nif not APPROVED_BY_HUMAN:\\n'
            '    raise RuntimeError(\\"Execution blocked: set APPROVED_BY_HUMAN = True only after human review and approval.\\")"}'
        )

    monkeypatch.setattr(client, "_chat", json_chat)

    with pytest.raises(LLMResponseError):
        await client.generate_script("Create a bracket", "skill context", str(tmp_path), tmp_path / "task.py")


async def _test_valid_provider_script_has_no_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(_provider_profile())

    async def json_chat(messages):
        return (
            '{"plan":"创建真实零件并保存。","risks":["需要 SolidWorks COM"],'
            '"required_files":[],"script":"def main():\\n    print(\\"real\\")\\n\\nif __name__ == \\"__main__\\":\\n    raise SystemExit(main())"}'
        )

    monkeypatch.setattr(client, "_chat", json_chat)

    script = await client.generate_script("Create a bracket", "skill context", str(tmp_path), tmp_path / "task.py")

    assert not script.demo_mode
    assert not script.fallback_used
    assert script.fallback_reason == ""
    assert "def main" in script.script


def _provider_profile() -> LLMProfile:
    return LLMProfile(
        id="provider",
        name="Provider",
        api_base_url="http://127.0.0.1:1234/v1",
        api_key="secret",
        model="cad-model",
        vision_model="vision-model",
    )
