# Real SolidWorks 2025 Validation Report

Generated: 2026-06-22T22:26:16.024834
Overall: failed
Core passed: 23
Core failed: 5

| Capability | Status | Files | Skip reason |
|---|---|---|---|
| mcp.solidworks_health_check | passed | 0 |  |
| mcp.solidworks_connect | passed | 0 |  |
| mcp.solidworks_create_basic_part | passed | 1 |  |
| mcp.solidworks_save_document | passed | 0 |  |
| mcp.solidworks_export_active | passed | 1 |  |
| mcp.solidworks_set_appearance | passed | 0 |  |
| mcp.solidworks_review_active | passed | 1 |  |
| mcp.solidworks_create_basic_part | passed | 1 |  |
| mcp.solidworks_export_active | passed | 1 |  |
| mcp.solidworks_open_document | passed | 0 |  |
| mcp.solidworks_new_document | passed | 0 |  |
| mcp.solidworks_add_component | passed | 0 |  |
| mcp.solidworks_add_component | passed | 0 |  |
| mcp.solidworks_save_document | passed | 0 |  |
| mcp.solidworks_add_coincident_mate | passed | 0 |  |
| mcp.solidworks_add_distance_mate | passed | 0 |  |
| mcp.solidworks_add_concentric_mate | passed | 0 |  |
| mcp.solidworks_export_active | passed | 0 |  |
| mcp.solidworks_export_active | passed | 0 |  |
| mcp.solidworks_export_active | skipped_with_reason | 0 | 1 validation error for SolidWorksExportInput
export_format
  Input should be 'step', 'stl', 'iges', 'parasolid', 'pdf' or 'dxf' [type=enum, input_value='dwg', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/enum |
| mcp.solidworks_add_rotary_motor | passed | 0 |  |
| mcp.status | passed | 0 |  |
| mcp.config_snippets | passed | 0 |  |
| mcp.tool_listing | passed | 0 |  |
| mcp.start | passed | 0 |  |
| mcp.stop | passed | 0 |  |
| ai.natural_language_generate_approve_run | failed | 1 |  |
| example.07_motion_study_rotary_motor | skipped_with_reason | 0 | Optional add-in capability requires motion; see preflight add-in status. |
| example.08_mini_fan_motion_assembly | skipped_with_reason | 0 | Optional add-in capability requires motion; see preflight add-in status. |
| reference.references-advanced-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-api-lookup-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-appearance-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-assembly-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-drawing-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-export-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-mcp-server-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-motion-study-md | skipped_with_reason | 0 | Optional add-in capability requires motion; see preflight add-in status. |
| reference.references-openclaw-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-part-modeling-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-review-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-troubleshooting-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| script.sw_export | failed | 0 |  |
| script.sw_motion | skipped_with_reason | 0 | Optional add-in capability requires motion; see preflight add-in status. |
| script.sw_part | failed | 0 |  |
| script.sw_review | failed | 0 |  |
| script.sw_session | failed | 0 |  |
| skill.solidworks-automation | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| subskill.subskills-solidworks-fillet-chamfer-cnc-references-cnc-fillet-chamfer-lessons-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| subskill.subskills-solidworks-threaded-holes-references-threaded-hole-lessons-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
