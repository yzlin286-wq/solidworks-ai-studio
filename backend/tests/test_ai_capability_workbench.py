from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from sw_ai_backend.api import ai_capabilities
from sw_ai_backend.main import create_app
from sw_ai_backend.registry.ai_capability_registry import AICapabilityRegistry
from sw_ai_backend.registry.recipe_registry import RecipeRegistry


HEADERS = {"X-SWAI-Token": "dev-token"}


def test_ai_capability_registry_has_27_workbench_entries() -> None:
    registry = AICapabilityRegistry()
    capabilities = registry.list()

    assert len(capabilities) == 27
    assert capabilities[0].id == "ai.environment_preflight"
    assert capabilities[-1].id == "ai.troubleshooting_diagnosis"
    assert all(item.id.startswith("ai.") for item in capabilities)


def test_recipe_registry_has_14_entries_and_mounting_plate() -> None:
    recipes = RecipeRegistry().list()

    assert len(recipes) == 14
    mounting_plate = next(item for item in recipes if item.recipe_id == "mounting_plate")
    assert mounting_plate.capability_id == "ai.parametric_part_generator"
    assert "mounting_plate.STEP.mock.txt" in mounting_plate.mock_artifacts


def test_ai_capability_api_lists_capabilities_recipes_and_mcp_tools() -> None:
    client = TestClient(create_app())

    capabilities = client.get("/api/ai-capabilities", headers=HEADERS)
    recipes = client.get("/api/recipes", headers=HEADERS)
    mcp_tools = client.get("/api/mcp/tools", headers=HEADERS)

    assert capabilities.status_code == 200
    assert capabilities.json()["total"] == 27
    assert recipes.status_code == 200
    assert recipes.json()["total"] == 14
    assert mcp_tools.status_code == 200
    assert mcp_tools.json()["total"] == 16


def test_mounting_plate_mock_workflow_requires_approval_and_creates_artifacts() -> None:
    client = TestClient(create_app())
    capability_id = "ai.parametric_part_generator"
    plan = client.post(
        f"/api/ai-capabilities/{capability_id}/plan",
        headers=HEADERS,
        json={"recipe_id": "mounting_plate", "execution_mode": "mock", "prompt": "生成 mounting_plate"},
    )
    assert plan.status_code == 200
    task_id = plan.json()["task_id"]

    generated = client.post(
        f"/api/ai-capabilities/{capability_id}/generate-script",
        headers=HEADERS,
        json={"task_id": task_id, "parameters": {"width_mm": 120}},
    )
    assert generated.status_code == 200
    assert "mock execution is explicit" in generated.json()["script"]

    validation = client.post(f"/api/ai-capabilities/{capability_id}/validate", headers=HEADERS, json={"task_id": task_id})
    assert validation.status_code == 200
    assert validation.json()["validation"]["ok"] is True

    blocked = client.post(f"/api/ai-capabilities/{capability_id}/execute", headers=HEADERS, json={"task_id": task_id})
    assert blocked.status_code == 400

    approved = client.post(f"/api/ai-capabilities/{capability_id}/approve", headers=HEADERS, json={"task_id": task_id})
    assert approved.status_code == 200
    assert approved.json()["approved"] is True

    executed = client.post(
        f"/api/ai-capabilities/{capability_id}/execute",
        headers=HEADERS,
        json={"task_id": task_id, "parameters": {"width_mm": 120}},
    )
    payload = executed.json()
    assert executed.status_code == 200
    assert payload["status"] == "completed"
    assert payload["mock_demo"] is True
    assert payload["real_execution_verified"] is False
    assert len(payload["artifacts"]) >= 5
    assert all(item["exists"] for item in payload["artifacts"])


def test_mounting_plate_real_workflow_requires_four_hole_geometry_evidence(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SWAI_OUTPUT_DIR", str(tmp_path / "outputs"))

    class FakeSolidWorksService:
        async def preflight_async(self, timeout_seconds=5):
            return SimpleNamespace(can_run_real_com=True, solidworks_version="test-revision", checks=[])

    class FakeMCPToolRunner:
        def run(self, tool_name, parameters, raise_on_error_status=False):
            if tool_name == "solidworks_export_active":
                path = parameters["output_path"]
                tmp_path.joinpath("exports_seen.txt").write_text(path, encoding="utf-8")
                from pathlib import Path

                Path(path).write_text("real step placeholder from dependency boundary", encoding="utf-8")
                return SimpleNamespace(stdout=json.dumps({"status": "ok", "output_path": path}), created_files=[path])
            if tool_name == "solidworks_review_active":
                from pathlib import Path

                output_dir = Path(parameters["output_dir"])
                output_dir.mkdir(parents=True, exist_ok=True)
                files = [
                    output_dir / "mounting_plate_review_report.json",
                    output_dir / "mounting_plate_review_summary.md",
                    output_dir / "mounting_plate_review_front.bmp",
                    output_dir / "mounting_plate_review_top.bmp",
                    output_dir / "mounting_plate_review_right.bmp",
                    output_dir / "mounting_plate_review_isometric.bmp",
                ]
                for path in files:
                    path.write_text("review evidence", encoding="utf-8")
                return SimpleNamespace(
                    stdout=json.dumps({"status": "ok", "created_files": [str(path) for path in files]}),
                    created_files=[str(path) for path in files],
                )
            raise AssertionError(f"Unexpected tool: {tool_name}")

    def fake_create_with_holes(output_path, geometry):
        output_path.write_text("real sldprt placeholder from dependency boundary", encoding="utf-8")
        return {
            "status": "ok",
            "output_path": str(output_path),
            "created_files": [str(output_path)],
            "features": {
                "width_mm": geometry["width_mm"],
                "height_mm": geometry["height_mm"],
                "thickness_mm": geometry["thickness_mm"],
                "holes": 4,
                "hole_diameter_mm": geometry["hole_diameter_mm"],
                "hole_offset_mm": geometry["hole_offset_mm"],
                "chamfer_mm": geometry["chamfer_mm"],
            },
        }

    monkeypatch.setattr(ai_capabilities, "solidworks_service", FakeSolidWorksService())
    monkeypatch.setattr(ai_capabilities, "mcp_tool_runner", FakeMCPToolRunner())
    monkeypatch.setattr(ai_capabilities, "_create_mounting_plate_with_holes", fake_create_with_holes)

    client = TestClient(create_app())
    capability_id = "ai.parametric_part_generator"
    plan = client.post(
        f"/api/ai-capabilities/{capability_id}/plan",
        headers=HEADERS,
        json={"recipe_id": "mounting_plate", "execution_mode": "real", "prompt": "生成四孔 mounting_plate"},
    )
    task_id = plan.json()["task_id"]
    generated = client.post(
        f"/api/ai-capabilities/{capability_id}/generate-script",
        headers=HEADERS,
        json={"task_id": task_id, "recipe_id": "mounting_plate", "execution_mode": "real"},
    )
    assert generated.status_code == 200
    validation = client.post(f"/api/ai-capabilities/{capability_id}/validate", headers=HEADERS, json={"task_id": task_id})
    assert validation.status_code == 200
    approved = client.post(f"/api/ai-capabilities/{capability_id}/approve", headers=HEADERS, json={"task_id": task_id})
    assert approved.status_code == 200

    executed = client.post(
        f"/api/ai-capabilities/{capability_id}/execute",
        headers=HEADERS,
        json={"task_id": task_id, "execution_mode": "real"},
    )
    payload = executed.json()

    assert executed.status_code == 200
    assert payload["status"] == "completed"
    assert payload["mock_demo"] is False
    assert payload["real_execution_verified"] is True
    assert payload["evidence"]["hole_features_restored"] is True
    assert payload["evidence"]["geometry_parity_verified"] is True
    assert payload["evidence"]["hole_count_observed"] == 4
    assert payload["evidence"]["hole_diameter_mm"] == 6.5
    assert len(payload["artifacts"]) >= 8


def test_static_validation_blocks_dangerous_script() -> None:
    from sw_ai_backend.execution.static_validator import StaticValidator

    result = StaticValidator().validate("import subprocess\nsubprocess.run(['cmd'])\n")

    assert result.ok is False
    assert "Blocked import: subprocess" in result.issues


def test_main_navigation_has_no_low_level_direct_tool_entry() -> None:
    from sw_ai_backend.core.paths import project_root

    shell = (project_root() / "apps/desktop/src/renderer/components/Shell.tsx").read_text(encoding="utf-8")

    assert "Direct Tools" not in shell
    assert "solidworks/create-basic-part" not in shell
    assert "solidworks/export" not in shell
