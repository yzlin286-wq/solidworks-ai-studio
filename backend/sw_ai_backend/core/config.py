from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import ValidationError

from sw_ai_backend.core.paths import user_data_dir
from sw_ai_backend.models.schemas import AppConfig, LLMProfile


DEFAULT_PROFILES = [
    LLMProfile(
        id="ccagent",
        name="CCAgent OpenAI-compatible",
        api_base_url="https://api.ccagent.cn/v1",
        model="glm-5.1",
        vision_model="doubao-seed-2.0-pro",
        temperature=0.2,
        max_tokens=8192,
        timeout_seconds=180,
    ),
    LLMProfile(
        id="openai",
        name="OpenAI",
        api_base_url="https://api.openai.com/v1",
        model="gpt-4.1",
        vision_model="gpt-4.1",
        temperature=0.2,
        max_tokens=4096,
        timeout_seconds=120,
    ),
    LLMProfile(
        id="azure-compatible",
        name="Azure-compatible",
        api_base_url="https://your-resource.openai.azure.com/openai/v1",
        model="deployment-name",
        vision_model="deployment-name",
        temperature=0.2,
        max_tokens=4096,
        timeout_seconds=120,
    ),
    LLMProfile(
        id="custom",
        name="Custom gateway",
        api_base_url="http://127.0.0.1:8000/v1",
        model="custom-model",
        vision_model="custom-vision-model",
        temperature=0.2,
        max_tokens=4096,
        timeout_seconds=120,
    ),
    LLMProfile(
        id="local",
        name="Local model gateway",
        api_base_url="http://127.0.0.1:1234/v1",
        model="local-model",
        vision_model="local-vision-model",
        temperature=0.2,
        max_tokens=1800,
        timeout_seconds=90,
    ),
]


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (user_data_dir() / "config.json")
        self._lock = threading.RLock()

    def load(self) -> AppConfig:
        with self._lock:
            if not self.path.exists():
                config = self._strict_config(AppConfig(profiles=DEFAULT_PROFILES, active_profile_id="ccagent"))
                self.save(config)
                return config
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                config = self._strict_config(AppConfig.model_validate(data))
                normalized = self._with_recommended_profiles(config)
                if normalized != config:
                    self.save(normalized)
                return normalized
            except (json.JSONDecodeError, ValidationError):
                backup = self.path.with_suffix(".invalid.json")
                self.path.replace(backup)
                config = self._strict_config(AppConfig(profiles=DEFAULT_PROFILES, active_profile_id="ccagent"))
                self.save(config)
                return config

    def save(self, config: AppConfig) -> AppConfig:
        with self._lock:
            config = self._strict_config(self._preserve_masked_api_keys(config))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(config.model_dump_json(indent=2), encoding="utf-8")
            temp.replace(self.path)
            return config

    def public_config(self) -> AppConfig:
        config = self.load()
        redacted_profiles = []
        for profile in config.profiles:
            profile_data = profile.model_dump()
            if profile_data.get("api_key"):
                profile_data["api_key"] = "********"
            redacted_profiles.append(LLMProfile.model_validate(profile_data))
        return config.model_copy(update={"profiles": redacted_profiles})

    def _with_recommended_profiles(self, config: AppConfig) -> AppConfig:
        existing_ids = {profile.id for profile in config.profiles}
        missing = [profile for profile in DEFAULT_PROFILES if profile.id not in existing_ids]
        if not missing:
            return config
        return config.model_copy(update={"profiles": [*config.profiles, *missing]})

    def _strict_config(self, config: AppConfig) -> AppConfig:
        recommended_vision = {profile.id: profile.vision_model or profile.model for profile in DEFAULT_PROFILES}
        profiles = [
            profile.model_copy(update={"vision_model": profile.vision_model or recommended_vision.get(profile.id, profile.model)})
            for profile in config.profiles
        ]
        return config.model_copy(update={"profiles": profiles, "mock_mode": False})

    def _preserve_masked_api_keys(self, config: AppConfig) -> AppConfig:
        if not self.path.exists():
            return config
        try:
            existing = AppConfig.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError):
            return config
        existing_keys = {profile.id: profile.api_key for profile in existing.profiles if profile.api_key}
        profiles = []
        changed = False
        for profile in config.profiles:
            if profile.api_key == "********":
                profiles.append(profile.model_copy(update={"api_key": existing_keys.get(profile.id, "")}))
                changed = True
            else:
                profiles.append(profile)
        return config.model_copy(update={"profiles": profiles}) if changed else config
