from __future__ import annotations

from fastapi.testclient import TestClient

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
