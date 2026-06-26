from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from typing import Any

from sw_ai_backend.core.paths import skill_paths
from sw_ai_backend.mcp.tool_registry import MCPToolRegistry
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime


@dataclass
class MCPToolRunResult:
    stdout: str
    stderr: str
    created_files: list[str]
    data: dict[str, Any]


class MCPToolRunner:
    def __init__(self) -> None:
        self.paths = skill_paths()
        self.registry = MCPToolRegistry()

    def run(self, tool_name: str, parameters: dict[str, Any], raise_on_error_status: bool = False) -> MCPToolRunResult:
        definition = self.registry.get(tool_name)
        if definition is None:
            raise ValueError(f"上游 server 未暴露该 MCP tool：{tool_name}")
        module = self._load_server_module()
        tool = getattr(module, tool_name, None)
        if tool is None:
            raise ValueError(f"server.py 中未找到 MCP tool 函数：{tool_name}")
        params = self._make_params(tool, parameters)
        with solidworks_com_runtime(f"MCP tool {tool_name}"):
            result = tool(params) if params is not None else tool()
        text = str(result)
        if raise_on_error_status:
            self._raise_if_error_status(text, tool_name)
        files = self._extract_files(text)
        return MCPToolRunResult(stdout=text, stderr="", created_files=files, data={"raw": text, "tool": tool_name})

    def _raise_if_error_status(self, text: str, tool_name: str) -> None:
        import json

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict) and str(data.get("status", "")).lower() in {"error", "failed", "fail"}:
            message = data.get("message") or data.get("error") or data.get("error_type") or "MCP tool 返回错误状态。"
            raise RuntimeError(f"{tool_name} 返回 {data.get('status')}：{message}")

    def _load_server_module(self):
        server = self.paths.solidworks_mcp_server
        scripts = self.paths.solidworks_scripts
        for path in [str(scripts), str(server.parent)]:
            if path not in sys.path:
                sys.path.insert(0, path)
        module_name = "_swai_upstream_solidworks_mcp_server"
        existing = sys.modules.get(module_name)
        if existing is not None:
            return existing
        spec = importlib.util.spec_from_file_location(module_name, server)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法从 {server} 加载 MCP server 模块")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _make_params(self, tool, parameters: dict[str, Any]):
        annotations = getattr(tool, "__annotations__", {})
        model = annotations.get("params")
        if isinstance(model, str):
            model = getattr(tool, "__globals__", {}).get(model)
        if model is None:
            return None
        if hasattr(model, "model_validate"):
            return model.model_validate(parameters)
        return parameters

    def _extract_files(self, text: str) -> list[str]:
        import json
        import re

        files: list[str] = []

        def collect(value: Any, key_hint: str = "") -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    collect(item, str(key).lower())
            elif isinstance(value, list):
                for item in value:
                    collect(item, key_hint)
            elif isinstance(value, str):
                if key_hint in {"path", "output_path", "report_path", "drawing_path"} and value:
                    files.append(value)
                elif key_hint in {"files", "created_files"} and value:
                    files.append(value)

        try:
            data = json.loads(text)
            collect(data)
        except json.JSONDecodeError:
            pass
        files.extend(re.findall(r"[A-Za-z]:\\[^\\/:*?\"<>|\r\n]+(?:\\[^\\/:*?\"<>|\r\n]+)*\.[A-Za-z0-9]+", text))
        return sorted(set(files))
