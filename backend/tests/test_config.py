from pathlib import Path

from sw_ai_backend.core.config import ConfigStore
from sw_ai_backend.models.schemas import AppConfig, LLMProfile


def test_config_store_roundtrip_and_redaction(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    config = AppConfig(
        profiles=[
            LLMProfile(
                id="custom",
                name="Custom",
                api_base_url="http://127.0.0.1:1234/v1",
                api_key="secret-key",
                model="cad-model",
            )
        ],
        active_profile_id="custom",
    )

    store.save(config)
    loaded = store.load()
    public = store.public_config()

    assert loaded.profiles[0].api_key == "secret-key"
    assert public.profiles[0].api_key == "********"
    assert any(profile.id == "ccagent" and profile.api_base_url == "https://api.ccagent.cn/v1" for profile in loaded.profiles)
    assert store.path.exists()


def test_config_store_creates_default_without_deadlock(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "missing.json")

    config = store.load()

    assert config.active_profile_id == "ccagent"
    assert config.profiles[0].model == "glm-5.1"
    assert config.profiles[0].vision_model == "doubao-seed-2.0-pro"
    assert store.path.exists()


def test_config_store_preserves_masked_api_key_on_save(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    original = AppConfig(
        profiles=[
            LLMProfile(
                id="ccagent",
                name="CCAgent",
                api_base_url="https://api.ccagent.cn/v1",
                api_key="real-secret",
                model="doubao-seed-2.0-pro",
            )
        ],
        active_profile_id="ccagent",
    )
    store.save(original)

    public = store.public_config()
    store.save(public)
    loaded = store.load()

    assert loaded.profiles[0].api_key == "real-secret"


def test_config_store_forces_mock_mode_off(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    config = AppConfig(
        profiles=[
            LLMProfile(
                id="ccagent",
                name="CCAgent",
                api_base_url="https://api.ccagent.cn/v1",
                api_key="real-secret",
                model="glm-5.1",
            )
        ],
        active_profile_id="ccagent",
        mock_mode=True,
    )

    saved = store.save(config)
    loaded = store.load()

    assert not saved.mock_mode
    assert not loaded.mock_mode


def test_config_store_backfills_vision_model_for_legacy_profile(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "config.json")
    config = AppConfig(
        profiles=[
            LLMProfile(
                id="ccagent",
                name="CCAgent",
                api_base_url="https://api.ccagent.cn/v1",
                api_key="real-secret",
                model="glm-5.1",
                vision_model="",
            )
        ],
        active_profile_id="ccagent",
    )

    saved = store.save(config)
    loaded = store.load()

    assert saved.profiles[0].vision_model == "doubao-seed-2.0-pro"
    assert loaded.profiles[0].vision_model == "doubao-seed-2.0-pro"
