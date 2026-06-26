from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "SolidWorks AI Studio"


def project_root() -> Path:
    override = os.environ.get("SWAI_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    bundle_root = getattr(sys, "_MEIPASS", "")
    if getattr(sys, "frozen", False) and bundle_root:
        return Path(bundle_root).resolve()
    return Path(__file__).resolve().parents[3]


def user_data_dir() -> Path:
    override = os.environ.get("SWAI_USER_DATA_DIR")
    if override:
        base = Path(override)
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "solidworks-ai-studio"
    base.mkdir(parents=True, exist_ok=True)
    return base


def user_logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_outputs_dir() -> Path:
    override = os.environ.get("SWAI_OUTPUT_DIR")
    path = Path(override).expanduser() if override else project_root() / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def validation_dir() -> Path:
    path = user_outputs_dir() / "validation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def validation_latest_dir() -> Path:
    path = validation_dir() / "latest"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_logs_dir() -> Path:
    path = user_outputs_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_temp_dir() -> Path:
    path = user_outputs_dir() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class SkillPaths:
    solidworks: Path
    taste: Path
    solidworks_scripts: Path
    solidworks_mcp_server: Path


def skill_paths(root: Path | None = None) -> SkillPaths:
    base = root or project_root()
    solidworks = base / "vendor" / "skills" / "solidworks-automation"
    taste = base / "vendor" / "skills" / "taste-skill"
    return SkillPaths(
        solidworks=solidworks,
        taste=taste,
        solidworks_scripts=solidworks / "scripts",
        solidworks_mcp_server=solidworks / "mcp-server" / "server.py",
    )


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
