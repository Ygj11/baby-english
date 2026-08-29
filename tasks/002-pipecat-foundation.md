# TASK 002 — Pipecat Dependency & Compatibility Baseline

## Goal

将 Pipecat 作为本项目的正式 Python dependency 接入现有 FastAPI 应用，并建立未来 realtime voice 的代码边界。

本项目已经有自己的母仓库、`AGENTS.md`、FastAPI 结构和产品文档。

因此本 task **不使用 `pipecat init` 创建或重建产品母工程**。

不实现真实 STT / TTS / LLM，不实现 realtime transport。

---

## Preconditions

- TASK 001 已完成。
- TASK 001 的修改已经由 repository owner 检查并形成干净 Git baseline。
- `uv run pytest` 通过。
- 本机已安装 Pipecat CLI；Context Hub 可以可用，也可以暂时未完成索引。

---

## Allowed Changes

```text
pyproject.toml
uv.lock
.env.example
server/app/voice/**
server/tests/**
.gitignore
README.md（仅补充 Pipecat dependency / 本地验证说明）
AGENTS.md（仅发现当前官方事实与文档冲突时最小修正）
docs/ARCHITECTURE.md（仅发现当前官方事实与文档冲突时最小修正）
```

禁止修改其他产品功能目录。

---

## Required Inspection Before Coding

先执行：

```bash
pipecat --version
pipecat --help
pipecat init --help
pipecat init --list-options
pipecat context-hub --help
```

目的：

- 记录本机实际 Pipecat CLI 版本；
- 不根据模型旧知识猜当前 API；
- 确认当前 CLI 能力；
- 确认 Context Hub 是否可用。

如果 Context Hub 索引尚未完成：

```bash
pipecat context-hub refresh
```

可以由 owner 之后单独执行。

**Context Hub 索引失败不得阻塞本 task。**

---

## `pipecat init` Rule

本 task 不要求执行：

```bash
pipecat init .
```

并且明确禁止在 `baby-english` 根目录执行它。

原因：

- 本项目已经有自己的 `AGENTS.md`；
- 本项目不是纯 Pipecat bot，而是 FastAPI + MiniProgram + Tutor + Textbook + Voice 的产品应用；
- 不需要让 Pipecat scaffold 决定本项目整体目录。

如果 Codex 确实需要观察当前官方生成结构：

1. 先说明为什么有必要；
2. 只能在产品 repo 外的临时目录执行，例如：

```bash
pipecat init ../scaffolds/pipecat-reference
```

3. 不得复制整套 scaffold 进入产品 repo；
4. 不得因此引入示例中的商业 provider；
5. 不得覆盖本项目 `AGENTS.md`。

通常优先使用：

- 当前官方文档；
- Context Hub；
- installed package API；
- `pipecat init --list-options`

而不是生成 scaffold。

---

## Dependency Installation

使用项目自己的 uv：

```bash
uv add pipecat-ai
```

本 task 只安装 Pipecat core。

不要因为 CLI 在全局安装过：

```text
pipecat-ai[cli]
```

就把 CLI extra 写入本项目 dependency。

也不要提前安装具体 provider extras。

具体 STT / LLM / TTS provider 的依赖，在对应 provider 被 owner 选定后再加入。

---

## Implementation

创建最小目录：

```text
server/app/voice/
├── __init__.py
├── settings.py
└── realtime.py
```

### `settings.py`

只建立未来 realtime voice 所需的配置入口。

可以包含：

```text
STT_PROVIDER
LLM_PROVIDER
TTS_PROVIDER
```

但：

- 不设置某个收费 provider 为产品默认值；
- 不要求真实 API key；
- 不实现 provider adapter。

### `realtime.py`

只建立 Pipecat realtime integration 的模块边界。

要求：

- 使用当前已安装 Pipecat 版本的真实 core API；
- 不复制 Pipecat framework 源码；
- 不构建真实 STT/TTS/LLM pipeline；
- 不为了“看起来像完整框架”而创造多层 abstraction；
- 如果某个 Pipecat API 在当前版本中不稳定，宁可保持最小 import / compatibility seam，也不要猜旧 API。

---

## Tests

新增测试至少验证：

1. `pipecat-ai` 可从项目环境正常 import；
2. `server.app.voice` 模块可以加载；
3. voice settings 在无 API key 时仍可加载；
4. 原有 health test 继续通过。

普通测试不得：

- 访问网络；
- 调用真实 provider；
- 需要 Context Hub；
- 需要麦克风。

---

## Architecture Note

Pipecat 在本项目中的核心职责是：

```text
Realtime Voice Agent / Frame Pipeline
```

MVP Tasks 009–010 使用：

```text
Batch HTTP audio
↓
STTGateway / TTSGateway
```

不要求通过 Pipecat realtime FrameProcessor。

未来真正实现：

- streaming STT
- continuous conversation
- barge-in
- realtime TTS
- realtime transport

时，优先进入 Pipecat pipeline。

---

## Do Not

- 不运行 `pipecat init .`
- 不让 Pipecat scaffold 重建本项目
- 不接真实 STT
- 不接真实 TTS
- 不接真实 LLM
- 不建 WebSocket endpoint
- 不建 WebRTC
- 不引入 LiveKit / TEN / Dify / FastGPT
- 不 Fork Pipecat
- 不复制 Pipecat framework 源码
- 不安装未选定 provider 的 extras
- 不开始 TASK 003

---

## Verification

```bash
uv sync
uv run pytest
```

另外验证：

```bash
uv run python -c "import pipecat; print('pipecat import ok')"
```

如果当前 Pipecat package 提供稳定版本查询方式，可以输出版本；不要为此依赖私有 API。

---

## Definition of Done

- [ ] `pipecat-ai` 已成为项目 dependency
- [ ] `uv.lock` 已更新
- [ ] 没有把全局 CLI 当作项目 dependency
- [ ] `server/app/voice/` 最小边界已建立
- [ ] 没有真实 provider
- [ ] 没有 provider API key 也能测试
- [ ] 没有在产品 repo 执行 `pipecat init .`
- [ ] 原 health test 继续通过
- [ ] `uv run pytest` 全部通过
- [ ] 未开始 TASK 003

---

## Completion Report

完成后输出：

1. 本机 Pipecat CLI 版本
2. 修改摘要
3. 修改文件清单
4. 新增 dependency
5. 测试命令与结果
6. Context Hub 状态（仅信息，不作为通过条件）
7. 已知限制
8. 是否存在阻塞项
