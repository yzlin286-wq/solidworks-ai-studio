from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import skill_paths
from sw_ai_backend.models.schemas import MCPToolDefinition


class MCPToolRegistry:
    def __init__(self) -> None:
        self.paths = skill_paths()

    def discover(self) -> list[MCPToolDefinition]:
        server = self.paths.solidworks_mcp_server
        if not server.exists():
            return []
        try:
            module = ast.parse(server.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            return []
        schemas = self._pydantic_model_schemas(module)
        tools: list[MCPToolDefinition] = []
        for node in module.body:
            if not isinstance(node, ast.FunctionDef) or not self._is_tool(node):
                continue
            annotation = node.args.args[0].annotation if node.args.args and node.args.args[0].arg == "params" else None
            model_name = ast.unparse(annotation) if annotation else ""
            tools.append(
                MCPToolDefinition(
                    name=node.name,
                    description=self._description(node),
                    input_schema=schemas.get(model_name, {"type": "object", "properties": {}}),
                    output_schema={"type": "string"},
                    source_path=str(server),
                )
            )
        return sorted(tools, key=lambda tool: tool.name)

    def get(self, name: str) -> MCPToolDefinition | None:
        for tool in self.discover():
            if tool.name == name:
                return tool
        return None

    def _is_tool(self, node: ast.FunctionDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "tool":
                return True
        return False

    def _description(self, node: ast.FunctionDef) -> str:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                    return str(keyword.value.value)
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
        return ast.get_docstring(node) or node.name

    def _pydantic_model_schemas(self, module: ast.Module) -> dict[str, dict[str, Any]]:
        schemas: dict[str, dict[str, Any]] = {}
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(getattr(base, "id", "") == "BaseModel" or getattr(base, "attr", "") == "BaseModel" for base in node.bases):
                continue
            properties: dict[str, Any] = {}
            required: list[str] = []
            for stmt in node.body:
                if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                    continue
                field = stmt.target.id
                properties[field] = self._annotation_schema(stmt.annotation)
                if stmt.value is None:
                    required.append(field)
            schemas[node.name] = {"type": "object", "properties": properties, "required": required}
        return schemas

    def _annotation_schema(self, annotation: ast.AST | None) -> dict[str, Any]:
        text = ast.unparse(annotation) if annotation is not None else "str"
        if "float" in text:
            return {"type": "number"}
        if "int" in text:
            return {"type": "integer"}
        if "bool" in text:
            return {"type": "boolean"}
        if "List" in text or "list" in text:
            return {"type": "array"}
        return {"type": "string"}
