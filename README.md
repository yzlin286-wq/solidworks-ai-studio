# SolidWorks AI Studio

当前候选版本：`v0.9.5-rc.2`。

SolidWorks AI Studio 是面向中国制造业与 CAD 自动化团队的 Windows EXE 桌面工作站。它把 `solidworks-automation-skill` 的 SolidWorks COM / MCP 能力封装为 Electron + React + TypeScript 前端，并通过本地 FastAPI 后端串行执行真实 SolidWorks 操作。

应用支持 LLM 配置、Skill 索引、SolidWorks preflight、自然语言生成 Python Script、执行前审批、直接工具、审查报告、文件导出与 MCP 配置 snippets。Mock 工作流仅用于显式开发/测试，不能作为真实 SolidWorks 执行或发布验收证据；生产验收必须以真实 Provider、真实 COM preflight、真实执行产物和可复核证据为准。

## 环境要求

- Windows 10/11，用于真实 SolidWorks COM 自动化
- SolidWorks 已安装、至少启动过一次，并完成 COM 注册
- Python 3.10+
- Node.js 20+
- Git
- 真实 COM 调用建议安装：`pywin32`、`comtypes`

## Skill 集成

上游 Skill 放在：

```text
vendor/skills/solidworks-automation
vendor/skills/taste-skill
```

安全同步脚本会跳过有本地改动的 checkout，除非显式传入 `-Force`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync_solidworks_skill.ps1
powershell -ExecutionPolicy Bypass -File scripts/sync_taste_skill.ps1
```

Taste Skill 可选安装命令：

```powershell
npx skills add https://github.com/Leonxlnx/taste-skill --skill "gpt-taste"
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
npx skills add https://github.com/Leonxlnx/taste-skill --skill "redesign-existing-projects"
npx skills add https://github.com/Leonxlnx/taste-skill --skill "full-output-enforcement"
```

当前 UI 按高级制造业 / 工程软件 / AI-assisted CAD workstation 方向实现：深浅主题、Phosphor 图标、克制 motion、键盘可达、focus ring、reduced motion、loading / empty / error / disabled / active 状态齐全。

## 初始化

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

脚本会安装 Node 依赖、创建 `.venv`、安装后端 requirements，并同步两个上游 Skill。

## 开发运行

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

开发模式下，FastAPI 后端默认监听 `127.0.0.1:8765`，使用 `SWAI_API_TOKEN=dev-token`；Electron 通过环境变量拿到后端 URL 和 token。

## 大模型 API 配置

打开应用的“设置”页面，配置 OpenAI-compatible Profile：

- `API Base URL`
- `API Key`
- `Model`
- `Temperature`
- `Max Tokens`
- `Timeout`

推荐中国客户使用的 OpenAI-compatible 配置入口：

```text
API Base URL: https://api.ccagent.cn/v1
Text / reasoning model: glm-5.1
Vision model: doubao-seed-2.0-pro
```

`API Key` 必须在应用设置中输入。不要把密钥写入源码、README、测试脚本或提交记录。当前版本将密钥保存到本地用户配置文件，并在 API 响应、日志和验证报告中脱敏；后续可替换为 Windows Credential Manager 等系统安全存储。

## 基本工作流

1. 在 Welcome 或工作台中运行 preflight。
2. 在设置中保存 LLM Profile，并点击“测试连接”。
3. 在 Skill 浏览器确认 SolidWorks Skill 与 Taste Skill 已索引。
4. 在 Prompt Composer 输入自然语言 CAD 任务。
5. 点击“规划”或“生成 Script”。
6. 审查执行计划、风险点和 Python Script。
7. 点击“审批并执行”。
8. 在执行监控中检查 stdout、stderr、生成文件和 review_report。

示例 Prompt：

```text
新建一个 120x80x10mm 安装板，四角各打 M6 通孔，倒角 1mm，保存并导出 STEP。
```

生成的 Script 只允许从项目目录或应用临时目录执行。Runner 会阻止明显的 shell、PowerShell、cmd、删除、格式化和联网下载命令模式。

## 直接工具

工作台提供真实 API-backed 直接工具：

- 健康检查
- 连接 SolidWorks
- 新建零件 / 创建基础零件
- 打开文档
- 保存文档
- 导出 STEP / STL / PDF / DXF / DWG
- 审查当前文档
- 启动 / 停止 MCP Server

所有 SolidWorks COM 操作都在 Python 后端完成；Electron 和 Node 不直接操作 COM。

## SolidWorks 2025 真实模式

真实模式需要 preflight 证明：

- 当前是 Windows 桌面会话
- SolidWorks COM 可连接或可启动
- SolidWorks revision 为 `33.x`
- `pywin32` 与 `comtypes` 可导入
- 零件、装配体、工程图模板可检测
- `outputs` 可写
- 上游 MCP 工具可从 `vendor/skills/solidworks-automation/mcp-server/server.py` 发现

运行 preflight：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sw2025_preflight.ps1
```

报告路径：

```text
outputs/validation/sw2025_preflight.json
outputs/validation/sw2025_preflight.md
```

## MCP

后端可以启动 `vendor/skills/solidworks-automation/mcp-server/server.py`，并展示上游当前真实暴露的 MCP tools。设置页提供以下 snippets：

- Codex
- Claude Code
- Claude Desktop
- Cursor
- Windsurf

应用不会伪造 MCP 工具，实际列表以上游 server 和 Skill 索引为准。

## 构建

构建后端 EXE：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_backend.ps1
```

后端产物会复制到：

```text
apps/desktop/resources/backend/sw-ai-backend.exe
```

构建 Windows 桌面应用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_desktop.ps1
```

预期产物：

```text
dist/SolidWorks AI Studio Setup.exe
dist/SolidWorks AI Studio Portable.exe
```

## v0.9.5 RC 本机安装验收

RC 交付检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_backend.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_desktop.ps1
node scripts\v095_rc2_local_installation_acceptance.mjs
node scripts\create_v095_rc2_delivery_evidence_package.mjs
```

真实模型验证需要从本地环境或本地用户配置提供：

```powershell
$env:SWAI_VALIDATION_API_KEY="..."
$env:SWAI_VALIDATION_MODEL="glm-5.1"
$env:SWAI_VALIDATION_VISION_MODEL="doubao-seed-2.0-pro"
```

不要把 API Key 写入源码、文档、测试脚本、提交记录或 release evidence。RC 脱敏证据包：

```text
release_evidence/v0.9.5-rc.2/
```

本机交付包：

```text
outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-windows-x64.zip
outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-diagnostics.zip
```

真实验证通过后再构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_after_real_validation.ps1
```

## 测试与验证

后端单元测试：

```powershell
$env:PYTHONPATH="$PWD\backend"
python -m pytest backend/tests
```

前端组件测试与类型检查：

```powershell
cd apps/desktop
npm run typecheck
npm test
```

Renderer smoke test：

```powershell
cd apps/desktop
npm run smoke
```

完整安装版真实验证：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_installed_exe_full_validation.ps1
```

主要报告：

```text
outputs/validation/latest/INSTALLED_EXE_FULL_VALIDATION_REPORT.json
outputs/validation/latest/INSTALLED_EXE_FULL_VALIDATION_REPORT.md
```

验证脚本会检查应用启动、中文 UI、设置保存、API Key 脱敏、SolidWorks 连接、直接工具、Registry 工具、自然语言生成与审批执行、MCP start/stop/status，以及截图非空。

## 项目结构

```text
apps/desktop/
  src/main/
  src/preload/
  src/renderer/
backend/
  sw_ai_backend/
  tests/
vendor/skills/
  solidworks-automation/
  taste-skill/
scripts/
README.md
NOTICE
```

## 常见问题

- 后端返回 401：检查 `X-SWAI-Token` 是否与 `SWAI_API_TOKEN` 一致。
- COM 连接失败：手动启动 SolidWorks 2025，关闭启动弹窗，再运行 `scripts/sw2025_preflight.ps1`。
- SolidWorks 卡住：先处理 SolidWorks 桌面弹窗，再使用应用菜单 `Restart Backend`。
- 模板路径缺失：在 SolidWorks 选项或应用设置中配置零件、装配体、工程图模板。
- STEP/STL 导出失败：确认存在活动零件或装配体，并保存到 `outputs` 后重试。
- PDF/DXF/DWG 导出失败：确认工程图文档或模板可用。
- Simulation/Motion 不可用：安装或启用对应 SolidWorks Add-in，或接受验证中的 `skipped_with_reason`。
- Skill 浏览器为空：运行两个 sync 脚本并确认 `vendor/skills` 存在。
- MCP 启动失败：安装 `vendor/skills/solidworks-automation/mcp-server/requirements.txt`。
- 后端构建失败：先运行 `scripts/bootstrap.ps1`，再重试 `scripts/build_backend.ps1`。
