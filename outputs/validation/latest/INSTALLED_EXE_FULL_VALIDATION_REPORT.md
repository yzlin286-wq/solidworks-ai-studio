# 安装版 EXE 完整验证报告

生成时间：2026-06-26T17:18:31.749Z
安装版 EXE 通过：true
安装版 EXE：C:\Users\Vision\AppData\Local\Programs\SolidWorks AI Studio\SolidWorks AI Studio.exe
Backend health：true
真实 SolidWorks 已连接：true
验证密钥已注入：true
真实 LLM chat 已验证：true
真实 LLM API 复测已验证：true
计划 demo_mode：false
脚本 demo_mode：false
脚本 fallback_used：false
自然语言真实证据：true
自然语言产物存在：true
自然语言阶段：done
直接工具按钮：14/14
Registry 按钮：15/15
截图：12

## Direct Tools
- 健康检查: 通过 (HTTP 200, mode solidworks, files false, real_output true)
- 连接 SolidWorks: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 打开文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 保存文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出 STEP: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出 STL: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出 PDF: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出 DXF: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出 DWG: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 审查当前文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 创建基础零件: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 新建零件: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 启动 MCP Server: 通过 (HTTP 200, mode mcp, files false, real_output true)
- 停止 MCP Server: 通过 (HTTP 200, mode mcp, files false, real_output true)

## Registry Tools
- 连接 SolidWorks: 通过 (HTTP 200, mode solidworks, files false, real_output true)
- 健康检查: 通过 (HTTP 200, mode solidworks, files false, real_output true)
- 创建基础零件: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 新建文档: 通过 (HTTP 200, mode solidworks, files false, real_output true)
- 打开文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 保存文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 导出活动文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 审查活动文档: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 设置外观: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 添加组件: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 固定组件: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 添加 Coincident Mate: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 添加 Distance Mate: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 添加 Concentric Mate: 通过 (HTTP 200, mode solidworks, files true, real_output true)
- 添加 Rotary Motor: 通过 (HTTP 200, mode solidworks, files true, real_output true)

## Registry Skipped
- 关闭文档: destructive close-documents tool is skipped during installed validation

## Strict Violations
- 无

## 错误
- 无
