import json
import re

from sw_ai_backend.core.paths import project_root


def test_release_docs_and_recipe_matrix_exist() -> None:
    root = project_root()
    for relative in [
        "CHANGELOG.md",
        "RELEASE_NOTES_v0.9.0.md",
        "VALIDATION_SUMMARY.md",
        "docs/release-checklist.md",
    ]:
        assert (root / relative).exists(), relative

    summary = (root / "VALIDATION_SUMMARY.md").read_text(encoding="utf-8")
    recipe_rows = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", summary, flags=re.MULTILINE)
    assert len(recipe_rows) == 14
    assert ("mounting_plate", "ai.parametric_part_generator") in recipe_rows
    assert "SolidWorks revision: `33.5.0`" in summary
    assert "Real task ID: `1aad1cc4590449d28c0ae15fb45c8d77`" in summary


def test_release_hygiene_ignores_generated_directories_and_keeps_icon_config() -> None:
    root = project_root()
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for entry in [
        ".venv/",
        "node_modules/",
        "dist/",
        "outputs/",
        "**/__pycache__/",
        ".pytest_cache/",
        "test-results/",
        "playwright-report/",
    ]:
        assert entry in gitignore

    builder = (root / "apps/desktop/electron-builder.yml").read_text(encoding="utf-8")
    assert "icon: build/icon.ico" in builder


def test_release_scripts_exist_and_electron_high_fix_is_pinned() -> None:
    root = project_root()
    for relative in [
        "scripts/clean_generated.ps1",
        "scripts/verify_clean_clone.ps1",
        "scripts/solidworks_long_stability_mounting_plate.ps1",
        "scripts/validate_error_scenarios.ps1",
    ]:
        assert (root / relative).exists(), relative

    package = json.loads((root / "apps/desktop/package.json").read_text(encoding="utf-8"))
    assert package["devDependencies"]["electron"] == "42.5.0"
