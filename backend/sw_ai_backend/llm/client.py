from __future__ import annotations

import base64
import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from sw_ai_backend.models.schemas import AIPlanResponse, GenerateScriptResponse, LLMProfile, utc_now

class LLMConfigurationError(ValueError):
    pass


class LLMProviderError(RuntimeError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMResponseError(ValueError):
    pass


@dataclass
class LLMClient:
    profile: LLMProfile

    async def test_connection(self) -> tuple[bool, str, int | None, list[str], bool, bool]:
        if not self.profile.api_key:
            return False, "API Key 为空。请先保存 Profile，再测试真实 Provider。", None, [], False, False
        started = time.perf_counter()
        models: list[str] = []
        models_verified = False
        chat_verified = False
        notes: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=self.profile.timeout_seconds) as client:
                try:
                    response = await client.get(
                        f"{self.profile.api_base_url}/models",
                        headers=self._headers(),
                    )
                    if response.status_code < 400:
                        data = response.json()
                        models = [item.get("id", "") for item in data.get("data", []) if item.get("id")][:12]
                        models_verified = True
                    else:
                        notes.append(f"models HTTP {response.status_code}")
                except (httpx.HTTPError, ValueError) as exc:
                    notes.append(f"models {exc}")

                chat_response = await client.post(
                    f"{self.profile.api_base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._chat_payload(
                        model=self.profile.model,
                        messages=[
                            {"role": "system", "content": "你是本地 CAD 自动化应用的连接测试。"},
                            {"role": "user", "content": "请只回复：SWAI_OK"},
                        ],
                        temperature=0,
                        max_tokens=128,
                    ),
                )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if chat_response.status_code >= 400:
                suffix = f"；{'; '.join(notes)}" if notes else ""
                return False, f"Provider chat 返回 HTTP {chat_response.status_code}{suffix}。", latency_ms, models, models_verified, False
            data = chat_response.json()
            content = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            chat_verified = bool(content)
            if not chat_verified:
                return False, "Provider chat 响应为空，请检查 Model 名称。", latency_ms, models, models_verified, False
            detail = "models+chat" if models_verified else "chat"
            return True, f"连接成功，已验证 {detail} 真实响应。", latency_ms, models, models_verified, chat_verified
        except httpx.TimeoutException:
            return False, "连接超时。", None, models, models_verified, chat_verified
        except httpx.HTTPError as exc:
            return False, f"连接失败：{exc}", None, models, models_verified, chat_verified

    async def test_vision_connection(self) -> tuple[bool, str, int | None, str, bool]:
        if not self.profile.api_key:
            return False, "API Key 为空。请先保存 Profile，再测试真实视觉 Provider。", None, self._vision_model(), False
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.profile.timeout_seconds) as client:
                response = await client.post(
                    f"{self.profile.api_base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._chat_payload(
                        model=self._vision_model(),
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "请判断图片是否是一个非空测试图。只回复 SWAI_VISION_OK 或解释失败原因。"},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/png;base64,{_tiny_png_base64()}"},
                                    },
                                ],
                            }
                        ],
                        temperature=0,
                        max_tokens=128,
                    ),
                )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code >= 400:
                return False, f"Vision Provider 返回 HTTP {response.status_code}。", latency_ms, self._vision_model(), False
            data = response.json()
            content = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            if not content:
                return False, "Vision Provider 响应为空，请检查 Vision Model 名称。", latency_ms, self._vision_model(), False
            return True, "视觉模型连接成功，已验证 image_url chat 真实响应。", latency_ms, self._vision_model(), True
        except httpx.TimeoutException:
            return False, "视觉模型连接超时。", None, self._vision_model(), False
        except httpx.HTTPError as exc:
            return False, f"视觉模型连接失败：{exc}", None, self._vision_model(), False

    async def generate_plan(
        self,
        prompt: str,
        skill_context: str,
        output_dir: str,
    ) -> AIPlanResponse:
        if not self.profile.api_key:
            raise LLMConfigurationError("API Key 为空。请先保存真实 Provider Profile。")
        try:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": self._system_prompt(skill_context),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create a SolidWorks automation execution plan only. "
                            "Return one raw JSON object with keys plan, risks, required_files. "
                            "Do not wrap it in Markdown. Do not add prose before or after the JSON. "
                            f"Output directory: {output_dir or 'user selected workspace output directory'}.\n"
                            f"User request: {prompt}"
                        ),
                    },
                ]
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError("Provider 请求超时，请检查网络或增大 Timeout。") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Provider 返回 HTTP {exc.response.status_code}，请检查 API Base URL、API Key 和 Model。") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Provider 请求失败：{exc}") from exc
        data = self._json_from_text(content)
        plan = str(data.get("plan") or "").strip()
        if not plan:
            raise LLMResponseError("Provider 返回内容缺少 plan 字段。")
        return AIPlanResponse(
            plan=plan,
            risks=[str(item) for item in data.get("risks", [])][:8],
            required_files=[str(item) for item in data.get("required_files", [])][:12],
            prompt=prompt,
            demo_mode=False,
            provider_verified_at=utc_now(),
        )

    async def generate_script(
        self,
        prompt: str,
        skill_context: str,
        output_dir: str,
        script_path: Path,
    ) -> GenerateScriptResponse:
        if not self.profile.api_key:
            raise LLMConfigurationError("API Key 为空。请先保存真实 Provider Profile。")
        try:
            content = await self._chat(
                [
                    {
                        "role": "system",
                        "content": self._system_prompt(skill_context),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Generate a safe Python script for this SolidWorks task. "
                            "Return one raw JSON object with keys plan, risks, required_files, script. "
                            "Do not wrap it in Markdown. Do not add prose before or after the JSON. "
                            "The script must import from the vendored SolidWorks automation scripts, "
                            "must not invoke shell commands, and must write outputs only to the requested path. "
                            "Do not include hard-coded approval gates such as APPROVED_BY_HUMAN = False; "
                            "the desktop app enforces human review before this script is executed. "
                            "Do not call low-level long-argument COM APIs such as FeatureExtrusion2, FeatureExtrusion3, "
                            "FeatureCut3, FeatureCut4, Extension.SaveAs, SaveAs2, SaveAs3, or InsertFeatureChamfer directly. "
                            "Use SolidWorksSession.save/export and sw_part helpers instead.\n"
                            "For plate-style tasks, follow this stable helper pattern and adapt dimensions only:\n"
                            "from sw_session import SolidWorksSession\n"
                            "from sw_connect import mm\n"
                            "from sw_part import sketch, sketch_rectangle, sketch_circle, extrude_midplane, extrude_cut, chamfer\n"
                            "session = SolidWorksSession(); model = session.new_part()\n"
                            "with sketch(model, 'Front Plane') as base_sketch: sketch_rectangle(model, 0, 0, mm(120), mm(80))\n"
                            "extrude_midplane(model, base_sketch, mm(10))\n"
                            "with sketch(model, 'Front Plane') as hole_sketch: create four sketch_circle calls\n"
                            "extrude_cut(model, hole_sketch, 0)\n"
                            "try: chamfer(model, mm(1))\n"
                            "except Exception as exc: print('chamfer warning:', exc)\n"
                            "session.save(model, part_path); session.export(model, step_path)\n"
                            f"Output directory: {output_dir or 'user selected workspace output directory'}.\n"
                            f"User request: {prompt}"
                        ),
                    },
                ]
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError("Provider 请求超时，请检查网络或增大 Timeout。") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Provider 返回 HTTP {exc.response.status_code}，请检查 API Base URL、API Key 和 Model。") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Provider 请求失败：{exc}") from exc
        data = self._json_from_text(content)
        script = str(data.get("script") or "").strip()
        if not script.strip():
            raise LLMResponseError("Provider 返回内容缺少非空 script 字段。")
        script = self._normalize_generated_script(script)
        self._validate_generated_script(script)
        script = self._with_project_import_prologue(script)
        return GenerateScriptResponse(
            plan=str(data.get("plan") or "生成 SolidWorks Python 自动化 Script，用户审批后再执行。"),
            risks=[str(item) for item in data.get("risks", ["需要可用的 SolidWorks COM 会话。"])][:8],
            required_files=[str(item) for item in data.get("required_files", [])][:12],
            script=script,
            script_path=str(script_path),
            demo_mode=False,
            fallback_used=False,
            fallback_reason="",
            provider_verified_at=utc_now(),
        )

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=self.profile.timeout_seconds) as client:
            response = await client.post(
                f"{self.profile.api_base_url}/chat/completions",
                headers=self._headers(),
                json=self._chat_payload(
                    model=self.profile.model,
                    messages=messages,
                    temperature=self.profile.temperature,
                    max_tokens=self.profile.max_tokens,
                ),
            )
        response.raise_for_status()
        data = response.json()
        content = str(data["choices"][0]["message"]["content"]).strip()
        if not content:
            raise LLMResponseError("Provider chat 响应为空。")
        return content

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.profile.api_key}",
            "Content-Type": "application/json",
        }

    def _chat_payload(self, **payload: Any) -> dict[str, Any]:
        if str(payload.get("model", "")).lower().startswith("glm"):
            payload["thinking"] = {"type": "disabled"}
        return payload

    def _vision_model(self) -> str:
        return self.profile.vision_model or self.profile.model

    def _system_prompt(self, skill_context: str) -> str:
        return (
            "You are generating controlled SolidWorks automation for a Windows desktop app. "
            "Use only Python code that imports the vendored SolidWorks automation skill modules. "
            "Do not generate shell, PowerShell, cmd, deletion, formatting, or network download commands. "
            "Every script must be reviewed and approved by the desktop app before execution; do not add a hard-coded "
            "APPROVED_BY_HUMAN = False runtime blocker inside generated scripts. "
            "Responses for plan or script generation must be strict JSON objects only, with no Markdown fences. "
            "For SolidWorks modeling scripts, prefer stable vendored helper APIs over raw COM calls with long positional argument lists. "
            "Prefer SolidWorksSession, sw_part, sw_assembly, sw_export, sw_review, and MCP tool behavior from this context:\n"
            f"{skill_context}"
        )

    def _json_from_text(self, text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise LLMResponseError("Provider 返回内容不是合法 JSON。")
        if not isinstance(data, dict):
            raise LLMResponseError("Provider JSON 响应必须是对象。")
        return data

    def _with_project_import_prologue(self, script: str) -> str:
        prologue = '''from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

'''
        if "VENDORED_SW_SCRIPTS" in script:
            return script
        if script.startswith("from __future__ import annotations"):
            script = script.replace("from __future__ import annotations", "", 1).lstrip()
        return prologue + script

    def _normalize_generated_script(self, script: str) -> str:
        script = re.sub(
            r"(\w+)\s*,\s*_\s*,\s*_\s*=\s*connect_solidworks\(",
            r"\1, _ = connect_solidworks(",
            script,
        )
        script = re.sub(
            r"(\w+)\s*,\s*(\w+)\s*,\s*_\s*=\s*connect_solidworks\(",
            r"\1, \2 = connect_solidworks(",
            script,
        )
        return script

    def _validate_generated_script(self, script: str) -> None:
        blocked_patterns = [
            "FeatureExtrusion2(",
            "FeatureExtrusion3(",
            "FeatureCut3(",
            "FeatureCut4(",
            ".Extension.SaveAs(",
            ".SaveAs2(",
            ".SaveAs3(",
            "InsertFeatureChamfer(",
            "APPROVED_BY_HUMAN = False",
            "Execution blocked: set APPROVED_BY_HUMAN",
        ]
        found = [pattern for pattern in blocked_patterns if pattern in script]
        if found:
            raise LLMResponseError(
                "Provider 生成脚本包含不稳定的底层 SolidWorks COM 长参数调用，已拒绝执行。"
                f" 请重新生成并复用 vendored helper APIs：{', '.join(found)}"
            )


def _tiny_png_base64() -> str:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (32, 32), "#1f6feb")
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 24, 24), fill="#ffffff")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")
