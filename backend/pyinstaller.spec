# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path.cwd().parent
vendor_skills = root / "vendor" / "skills"
validation_hiddenimports = collect_submodules("sw_ai_backend.validation")
mcp_hiddenimports = [
    "mcp",
    "mcp.server",
    "mcp.server.fastmcp",
    "mcp.server.fastmcp.exceptions",
    "mcp.server.fastmcp.prompts",
    "mcp.server.fastmcp.prompts.base",
    "mcp.server.fastmcp.prompts.manager",
    "mcp.server.fastmcp.resources",
    "mcp.server.fastmcp.resources.base",
    "mcp.server.fastmcp.resources.resource_manager",
    "mcp.server.fastmcp.resources.templates",
    "mcp.server.fastmcp.resources.types",
    "mcp.server.fastmcp.server",
    "mcp.server.fastmcp.tools",
    "mcp.server.fastmcp.tools.base",
    "mcp.server.fastmcp.tools.tool_manager",
    "mcp.server.fastmcp.utilities",
    "mcp.server.fastmcp.utilities.context_injection",
    "mcp.server.fastmcp.utilities.func_metadata",
    "mcp.server.fastmcp.utilities.logging",
    "mcp.server.fastmcp.utilities.types",
    "mcp.types",
]

a = Analysis(
    ["sw_ai_backend/main.py"],
    pathex=[str(Path.cwd())],
    binaries=[],
    datas=[(str(vendor_skills), "vendor/skills")] if vendor_skills.exists() else [],
    hiddenimports=mcp_hiddenimports + validation_hiddenimports + [
        "comtypes",
        "pythoncom",
        "pywintypes",
        "win32com",
        "win32com.client",
        "win32com.client.dynamic",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="sw-ai-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
