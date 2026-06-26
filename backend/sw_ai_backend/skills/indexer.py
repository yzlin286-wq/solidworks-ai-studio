from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sw_ai_backend.core.paths import SkillPaths, skill_paths
from sw_ai_backend.models.schemas import SkillDocument, SkillFunction, SkillIndexResponse


TASTE_SKILL_RELATIVE_PATHS = [
    "skills/gpt-tasteskill/SKILL.md",
    "skills/taste-skill/SKILL.md",
    "skills/redesign-skill/SKILL.md",
    "skills/output-skill/SKILL.md",
]


@dataclass
class SkillIndexer:
    paths: SkillPaths

    @classmethod
    def default(cls) -> "SkillIndexer":
        return cls(skill_paths())

    def build_index(self) -> SkillIndexResponse:
        documents = self._solidworks_documents() + self._taste_documents()
        functions = self._script_functions()
        mcp_tools = self._mcp_tools()
        summary = self._context_summary(documents, functions, mcp_tools)
        return SkillIndexResponse(
            solidworks_available=self.paths.solidworks.exists(),
            taste_available=self.paths.taste.exists(),
            solidworks_path=str(self.paths.solidworks),
            taste_path=str(self.paths.taste),
            documents=documents,
            functions=functions,
            mcp_tools=mcp_tools,
            context_summary=summary,
        )

    def _solidworks_documents(self) -> list[SkillDocument]:
        base = self.paths.solidworks
        documents: list[SkillDocument] = []
        candidates: list[tuple[Path, str]] = []
        if (base / "SKILL.md").exists():
            candidates.append((base / "SKILL.md", "skill"))
        for folder, kind in [
            ("references", "reference"),
            ("subskills", "subskill"),
            ("examples", "example"),
            ("mcp-server", "mcp"),
        ]:
            root = base / folder
            if root.exists():
                candidates.extend((path, kind) for path in root.rglob("*.md"))
        for path, kind in candidates:
            documents.append(self._document(path, kind))
        return documents

    def _taste_documents(self) -> list[SkillDocument]:
        base = self.paths.taste
        documents: list[SkillDocument] = []
        for rel in TASTE_SKILL_RELATIVE_PATHS:
            path = base / rel
            if path.exists():
                documents.append(self._document(path, "taste"))
        return documents

    def _document(self, path: Path, kind: str) -> SkillDocument:
        text = self._read_text(path)
        title = self._title_from_markdown(path, text)
        return SkillDocument(
            title=title,
            path=str(path),
            kind=kind,  # type: ignore[arg-type]
            modified_at=None
            if not path.exists()
            else datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            excerpt=self._excerpt(text),
        )

    def _script_functions(self) -> list[SkillFunction]:
        functions: list[SkillFunction] = []
        scripts = self.paths.solidworks_scripts
        if not scripts.exists():
            return functions
        for path in sorted(scripts.glob("*.py")):
            if path.name.startswith("__"):
                continue
            try:
                module = ast.parse(self._read_text(path))
            except SyntaxError:
                continue
            for node in module.body:
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    functions.append(
                        SkillFunction(
                            name=node.name,
                            signature=self._signature(node),
                            module=path.stem,
                            doc=ast.get_docstring(node) or "",
                        )
                    )
        return functions

    def _mcp_tools(self) -> list[str]:
        server = self.paths.solidworks_mcp_server
        if not server.exists():
            return []
        try:
            module = ast.parse(self._read_text(server))
        except SyntaxError:
            return []
        tools: list[str] = []
        for node in module.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "tool":
                        tools.append(node.name)
        return sorted(tools)

    def _context_summary(
        self,
        documents: list[SkillDocument],
        functions: list[SkillFunction],
        mcp_tools: list[str],
    ) -> str:
        doc_titles = ", ".join(doc.title for doc in documents[:16])
        function_names = ", ".join(f"{fn.module}.{fn.name}" for fn in functions[:28])
        tool_names = ", ".join(mcp_tools)
        return (
            "SolidWorks automation Skill 已加载，可用于 preflight、文档/会话管理、零件建模、装配体、"
            "工程图、导出、外观、Motion Study、结果审查与 MCP tools。"
            f"关键文档：{doc_titles}。"
            f"可调用 Python 函数包括：{function_names}。"
            f"上游 MCP server 暴露的工具：{tool_names}。"
            "生成的 Python 应从 vendor/skills/solidworks-automation/scripts 引入能力，并且必须在用户审批后执行。"
        )

    def _signature(self, node: ast.FunctionDef) -> str:
        args = []
        total_args = node.args.posonlyargs + node.args.args
        defaults = [None] * (len(total_args) - len(node.args.defaults)) + list(node.args.defaults)
        for arg, default in zip(total_args, defaults):
            text = arg.arg
            if arg.annotation is not None:
                text += f": {ast.unparse(arg.annotation)}"
            if default is not None:
                text += f"={ast.unparse(default)}"
            args.append(text)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        for kw in node.args.kwonlyargs:
            args.append(kw.arg)
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"{node.name}({', '.join(args)}){returns}"

    def _title_from_markdown(self, path: Path, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return path.stem

    def _excerpt(self, text: str, length: int = 520) -> str:
        clean = " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.startswith("---"))
        return clean[:length]

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
