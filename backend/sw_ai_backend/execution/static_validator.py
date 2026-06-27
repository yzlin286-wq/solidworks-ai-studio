from __future__ import annotations

import ast
from dataclasses import dataclass


BLOCKED_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
}

BLOCKED_MODULES = {
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "shutil",
}

BLOCKED_ATTRIBUTES = {
    ("os", "system"),
    ("os", "popen"),
    ("shutil", "rmtree"),
    ("pathlib", "unlink"),
}


@dataclass(frozen=True)
class StaticValidationResult:
    ok: bool
    issues: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return {"ok": self.ok, "issues": self.issues, "warnings": self.warnings}


class StaticValidator:
    def validate(self, script: str) -> StaticValidationResult:
        issues: list[str] = []
        warnings: list[str] = []
        try:
            tree = ast.parse(script)
        except SyntaxError as exc:
            return StaticValidationResult(ok=False, issues=[f"Python syntax error: {exc}"], warnings=[])

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [alias.name.split(".", 1)[0] for alias in getattr(node, "names", [])]
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module.split(".", 1)[0])
                for module in modules:
                    if module in BLOCKED_MODULES:
                        issues.append(f"Blocked import: {module}")
            if isinstance(node, ast.Call):
                name = self._call_name(node.func)
                if name in BLOCKED_NAMES:
                    issues.append(f"Blocked call: {name}")
                for owner, attr in BLOCKED_ATTRIBUTES:
                    if name == f"{owner}.{attr}":
                        issues.append(f"Blocked call: {name}")
            if isinstance(node, ast.Attribute) and node.attr.lower() in {"deletefile", "removedocument"}:
                warnings.append(f"Potential destructive API attribute: {node.attr}")
        return StaticValidationResult(ok=not issues, issues=sorted(set(issues)), warnings=sorted(set(warnings)))

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            owner = self._call_name(node.value)
            return f"{owner}.{node.attr}" if owner else node.attr
        return ""

