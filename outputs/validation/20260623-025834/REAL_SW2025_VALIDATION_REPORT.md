# Real SolidWorks 2025 Validation Report

Generated: 2026-06-23T03:02:43.823883
Overall: failed
Core passed: 21
Core failed: 2

| Capability | Status | Files | Skip reason |
|---|---|---|---|
| mcp.solidworks_health_check | passed | 0 |  |
| mcp.solidworks_connect | passed | 0 |  |
| mcp.solidworks_create_basic_part | passed | 1 |  |
| script.sw_part | passed | 1 |  |
| mcp.solidworks_save_document | passed | 0 |  |
| mcp.solidworks_export_active | passed | 1 |  |
| mcp.solidworks_set_appearance | passed | 0 |  |
| mcp.solidworks_review_active | passed | 1 |  |
| mcp.solidworks_create_basic_part | passed | 1 |  |
| mcp.solidworks_export_active | passed | 1 |  |
| mcp.solidworks_review_active | passed | 1 |  |
| mcp.solidworks_open_document | failed | 0 |  |
| mcp.solidworks_new_document | passed | 0 |  |
| mcp.solidworks_add_component | passed | 0 |  |
| mcp.solidworks_add_component | passed | 0 |  |
| mcp.solidworks_set_component_fixed | passed | 0 |  |
| mcp.solidworks_save_document | passed | 0 |  |
| mcp.solidworks_add_coincident_mate | skipped_with_reason | 0 | solidworks_add_coincident_mate returned error: 组件 acceptance_mounting_plate-1 缺少特征: ['Front Plane'] |
| mcp.solidworks_add_distance_mate | skipped_with_reason | 0 | solidworks_add_distance_mate returned error: 组件 acceptance_mounting_plate-1 缺少特征: ['Top Plane'] |
| mcp.solidworks_add_concentric_mate | passed | 0 |  |
| mcp.solidworks_review_active | passed | 1 |  |
| mcp.solidworks_open_document | failed | 0 |  |
| mcp.solidworks_add_rotary_motor | passed | 0 |  |
| script.sw_motion | passed | 2 |  |
| example.07_motion_study_rotary_motor | passed | 2 |  |
| example.08_mini_fan_motion_assembly | passed | 2 |  |
| reference.references-motion-study-md | passed | 2 |  |
| optional.export_pdf | skipped_with_reason | 0 | solidworks_export_active returned error: <unknown>.GetSldWorksObject |
| optional.export_dxf | skipped_with_reason | 0 | solidworks_export_active returned error: <unknown>.ExportToDWG2 |
| wrapper.export_dwg | passed | 2 |  |
| mcp.solidworks_close_documents | passed | 0 |  |
| example.01_basic_part | passed | 2 |  |
| example.02_complex_part | passed | 8 |  |
| example.03_assembly | passed | 1 |  |
| example.04_batch_export | passed | 2 |  |
| example.05_drawing | passed | 2 |  |
| example.06_friendly_api | passed | 2 |  |
| script.validate_skill | passed | 1 |  |
| script.validate_mcp | passed | 1 |  |
| script.sw_macro_guard | passed | 1 |  |
| subskill.subskills-solidworks-fillet-chamfer-cnc-skill-md | passed | 10 |  |
| subskill.subskills-solidworks-threaded-holes-skill-md | passed | 10 |  |
| script.sw_appearance | passed | 2 |  |
| script.sw_assembly | passed | 2 |  |
| script.sw_connect | passed | 4 |  |
| script.sw_drawing | passed | 3 |  |
| script.sw_export | passed | 4 |  |
| script.sw_part | passed | 3 |  |
| script.sw_preflight | passed | 2 |  |
| script.sw_review | passed | 11 |  |
| script.sw_session | passed | 3 |  |
| mcp.status | passed | 0 |  |
| mcp.config_snippets | passed | 0 |  |
| mcp.tool_listing | passed | 0 |  |
| mcp.start | passed | 0 |  |
| mcp.stop | passed | 0 |  |
| ai.natural_language_generate_approve_run | passed | 18 |  |
| reference.references-advanced-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-api-lookup-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-appearance-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-assembly-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-drawing-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-export-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-mcp-server-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-openclaw-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-part-modeling-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-review-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| reference.references-troubleshooting-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| skill.solidworks-automation | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| subskill.subskills-solidworks-fillet-chamfer-cnc-references-cnc-fillet-chamfer-lessons-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
| subskill.subskills-solidworks-threaded-holes-references-threaded-hole-lessons-md | passed | 0 | Documentation capability indexed for prompt context and Skill Browser. |
