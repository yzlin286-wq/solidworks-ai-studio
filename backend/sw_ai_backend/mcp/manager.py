from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sw_ai_backend.core.paths import skill_paths
from sw_ai_backend.models.schemas import MCPConfigSnippetsResponse, MCPStatusResponse
from sw_ai_backend.skills.indexer import SkillIndexer


class MCPManager:
    def __init__(self) -> None:
        self.paths = skill_paths()
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> MCPStatusResponse:
        if self.process and self.process.poll() is None:
            return self.status("MCP server 已在运行。")
        server = self.paths.solidworks_mcp_server
        if not server.exists():
            return MCPStatusResponse(running=False, tools=[], message=f"未找到 MCP server：{server}")
        self.process = subprocess.Popen(
            [sys.executable, str(server)],
            cwd=str(self.paths.solidworks),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self.status("MCP server 已启动。")

    def stop(self) -> MCPStatusResponse:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        return self.status("MCP server 已停止。")

    def status(self, message: str = "") -> MCPStatusResponse:
        running = bool(self.process and self.process.poll() is None)
        command = [sys.executable, str(self.paths.solidworks_mcp_server)]
        tools = SkillIndexer.default().build_index().mcp_tools
        return MCPStatusResponse(
            running=running,
            pid=self.process.pid if running and self.process else None,
            command=command,
            tools=tools,
            message=message or ("MCP server 正在运行。" if running else "MCP server 已停止。"),
        )

    def snippets(self) -> MCPConfigSnippetsResponse:
        server = str(self.paths.solidworks_mcp_server)
        escaped_server = server.replace("\\", "\\\\")
        json_snippet = (
            '{\n'
            '  "mcpServers": {\n'
            '    "solidworks": {\n'
            '      "command": "python",\n'
            f'      "args": ["{escaped_server}"]\n'
            '    }\n'
            '  }\n'
            '}'
        )
        snippets = {
            "Codex": f"codex mcp add solidworks -- python {server}",
            "Claude Code": f"claude mcp add --scope user solidworks -- python {server}",
            "Claude Desktop": json_snippet,
            "Cursor": json_snippet,
            "Windsurf": json_snippet,
        }
        return MCPConfigSnippetsResponse(snippets=snippets, server_path=server)
