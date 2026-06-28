import json
import re

from sw_ai_backend.core.paths import project_root


def test_release_docs_and_recipe_matrix_exist() -> None:
    root = project_root()
    for relative in [
        "CHANGELOG.md",
        "RELEASE_NOTES_v0.9.0.md",
        "RELEASE_NOTES_v0.9.5-rc.1.md",
        "RELEASE_NOTES_v0.9.5-rc.2.md",
        "VALIDATION_SUMMARY.md",
        "docs/release-checklist.md",
        "release_candidate_report.md",
        "release_evidence/v0.9.5-rc.2/RC2_LOCAL_INSTALL_ACCEPTANCE.redacted.json",
        "release_evidence/v0.9.5-rc.2/SHA256SUMS.txt",
    ]:
        assert (root / relative).exists(), relative

    summary = (root / "VALIDATION_SUMMARY.md").read_text(encoding="utf-8")
    recipe_section = summary.split("## Current Recipe Validation Matrix", 1)[1].split("## Current Missing Revalidation Items", 1)[0]
    recipe_rows = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", recipe_section, flags=re.MULTILINE)
    assert len(recipe_rows) == 14
    assert ("mounting_plate", "ai.parametric_part_generator") in recipe_rows
    assert "SolidWorks revision: `33.5.0`" in summary
    assert "Real task ID: `1aad1cc4590449d28c0ae15fb45c8d77`" in summary
    assert "v0.9.5-rc.2 Local Installation Acceptance Evidence" in summary
    assert "RC2 LOCAL INSTALL PASS" in (root / "release_candidate_report.md").read_text(encoding="utf-8")


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
        "scripts/v095_install_first_start_validation.mjs",
        "scripts/v095_rc2_local_installation_acceptance.mjs",
        "scripts/create_v095_rc_evidence_package.mjs",
        "scripts/create_v095_rc2_delivery_evidence_package.mjs",
    ]:
        assert (root / relative).exists(), relative

    root_package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package = json.loads((root / "apps/desktop/package.json").read_text(encoding="utf-8"))
    backend_init = (root / "backend/sw_ai_backend/__init__.py").read_text(encoding="utf-8")
    assert root_package["version"] == "0.9.5-rc.2"
    assert package["version"] == "0.9.5-rc.2"
    assert '__version__ = "0.9.5-rc.2"' in backend_init
    assert package["devDependencies"]["electron"] == "42.5.0"


def test_release_evidence_is_redacted() -> None:
    root = project_root()
    evidence_dir = root / "release_evidence/v0.9.5-rc.2"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in evidence_dir.glob("*") if path.is_file())
    assert "C:\\Users\\Vision" not in combined
    assert not re.search(r"sk-[A-Za-z0-9_-]{16,}", combined)
    assert not re.search(r"gh[op]_[A-Za-z0-9_]{16,}", combined)
    assert not re.search(r"github_pat_[A-Za-z0-9_]{16,}", combined)
