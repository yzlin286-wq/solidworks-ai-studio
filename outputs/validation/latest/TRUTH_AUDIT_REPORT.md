# 严格真实性审计报告

生成时间：2026-06-27T01:29:58.069475
严格审计通过：True
结论：All functions are proven real-usable.

## 摘要

- 能力总数：55
- 可调用能力：40
- 已通过：55
- 失败：0
- 有原因跳过：0
- 未测试：0
- 仅文档/上下文能力：15
- Manifest 文件数：61

## 跳过
- 无

## 失败
- 无

## 严格失败项
- 无

## 能力证据

| 能力 | 可调用 | 类型 | UI | API | 状态 | 真实结果 | 文件证据 | SW 状态 |
|---|---:|---|---:|---:|---|---:|---:|---:|
| `example.01_basic_part` | True | python_script | True | True | passed | True | True | False |
| `example.02_complex_part` | True | python_script | True | True | passed | True | True | False |
| `example.03_assembly` | True | python_script | True | True | passed | True | True | False |
| `example.04_batch_export` | True | python_script | True | True | passed | True | True | True |
| `example.05_drawing` | True | python_script | True | True | passed | True | True | False |
| `example.06_friendly_api` | True | python_script | True | True | passed | True | True | True |
| `example.07_motion_study_rotary_motor` | True | python_script | True | True | passed | True | True | True |
| `example.08_mini_fan_motion_assembly` | True | python_script | True | True | passed | True | True | True |
| `mcp.solidworks_add_coincident_mate` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_add_component` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_add_concentric_mate` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_add_distance_mate` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_add_rotary_motor` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_close_documents` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_connect` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_create_basic_part` | True | mcp_tool | True | True | passed | True | True | True |
| `mcp.solidworks_export_active` | True | mcp_tool | True | True | passed | True | True | True |
| `mcp.solidworks_health_check` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_new_document` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_open_document` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_review_active` | True | mcp_tool | True | True | passed | True | True | True |
| `mcp.solidworks_save_document` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_set_appearance` | True | mcp_tool | True | True | passed | True | False | True |
| `mcp.solidworks_set_component_fixed` | True | mcp_tool | True | True | passed | True | False | True |
| `reference.references-advanced-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-api-lookup-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-appearance-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-assembly-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-drawing-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-export-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-mcp-server-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-motion-study-md` | False | documentation_only | True | False | passed | True | True | True |
| `reference.references-openclaw-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-part-modeling-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-review-md` | False | documentation_only | True | False | passed | True | False | False |
| `reference.references-troubleshooting-md` | False | documentation_only | True | False | passed | True | False | False |
| `script.sw_appearance` | True | python_script | True | True | passed | True | True | True |
| `script.sw_assembly` | True | python_script | True | True | passed | True | True | True |
| `script.sw_connect` | True | python_script | True | True | passed | True | True | True |
| `script.sw_drawing` | True | python_script | True | True | passed | True | True | True |
| `script.sw_export` | True | python_script | True | True | passed | True | True | True |
| `script.sw_macro_guard` | True | python_script | True | True | passed | True | True | False |
| `script.sw_motion` | True | python_script | True | True | passed | True | True | True |
| `script.sw_part` | True | python_script | True | True | passed | True | True | True |
| `script.sw_preflight` | True | python_script | True | True | passed | True | True | True |
| `script.sw_review` | True | python_script | True | True | passed | True | True | True |
| `script.sw_session` | True | python_script | True | True | passed | True | True | True |
| `script.validate_mcp` | True | python_script | True | True | passed | True | True | False |
| `script.validate_skill` | True | python_script | True | True | passed | True | True | False |
| `wrapper.export_dwg` | True | python_script | True | True | passed | True | True | True |
| `skill.solidworks-automation` | False | prompt_context | True | False | passed | True | False | False |
| `subskill.subskills-solidworks-fillet-chamfer-cnc-references-cnc-fillet-chamfer-lessons-md` | False | documentation_only | True | False | passed | True | False | False |
| `subskill.subskills-solidworks-fillet-chamfer-cnc-skill-md` | True | prompt_context | True | True | passed | True | True | True |
| `subskill.subskills-solidworks-threaded-holes-references-threaded-hole-lessons-md` | False | documentation_only | True | False | passed | True | False | False |
| `subskill.subskills-solidworks-threaded-holes-skill-md` | True | prompt_context | True | True | passed | True | True | True |
