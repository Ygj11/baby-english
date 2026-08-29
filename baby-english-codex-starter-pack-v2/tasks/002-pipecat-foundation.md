# TASK 002 — Pipecat Foundation

## Goal

把 Pipecat 作为正式 Python dependency 接入，并让 Codex 获得当前 Pipecat 官方项目模式与 API 上下文。

不实现真实 STT/TTS/LLM。

## Preconditions

- TASK 001 完成
- `uv run pytest` 通过

## Allowed Changes

```text
pyproject.toml
uv.lock
.env.example
server/app/voice/**
server/tests/**
.gitignore
README.md（仅 Pipecat 开发说明）
AGENTS.md（仅必要事实修正）
docs/ARCHITECTURE.md（仅必要事实修正）
```

## Required Research Before Coding

先确认当前 CLI：

```bash
pipecat --version
pipecat --help
pipecat init --help
```

如果 CLI 未安装：

使用 Pipecat 官方当前推荐的 `pipecat-ai[cli]` 安装方式。

不要根据模型记忆猜 CLI flags。

## Context Hub — Recommended

如果当前官方 CLI 支持并且本机允许：

安装/初始化 Pipecat Context Hub，使 Codex 可以查询当前 Pipecat docs/examples/API。

如果因环境限制无法使用：

记录原因，但不要阻塞本 task。

## Official Scaffold Inspection

使用当前 `pipecat init` 的 `--output` 能力生成到临时目录，例如：

```text
.tmp/pipecat-scaffold/
```

目的：

- 查看当前官方 server layout
- 查看当前 Pipecat worker/pipeline conventions
- 查看当前依赖声明
- 查看官方 coding-agent guidance

禁止：

- 覆盖本 repo `AGENTS.md`
- 覆盖本 repo docs
- 把整个生成项目机械复制进本项目

临时目录不得进入 git。

## Implementation

1. 将 Pipecat 加入本项目 dependency。
2. 创建最小：

```text
server/app/voice/
├── __init__.py
├── realtime.py
└── settings.py
```

3. `settings.py` 至少定义 realtime voice 未来需要的 provider 配置入口。
4. `realtime.py` 只建立 Pipecat import/构建边界，使用 fake/mock components 证明依赖可用。
5. 不要在本 task 为 batch HTTP voice 设计多层“假 Pipecat abstraction”。

## Architecture Note

Pipecat 的核心职责是：

```text
Realtime Voice Agent
```

Tasks 009–010 的 MVP batch voice 可以使用薄 Gateway，不要求强行通过 Pipecat frame pipeline。

## Do Not

- 不接真实 STT
- 不接真实 TTS
- 不接真实 LLM
- 不建 WebSocket endpoint
- 不引入其他 Voice Agent Framework
- 不 Fork Pipecat
- 不复制 Pipecat framework 源码

## Verification

```bash
uv sync
uv run pytest
```

至少验证：

- import Pipecat 正常
- realtime voice module 可加载
- 无 API key 也可测试

## Definition of Done

- [ ] Pipecat 是 dependency
- [ ] `uv.lock` 更新
- [ ] 已核对当前官方 scaffold
- [ ] `.tmp` 不进入 git
- [ ] Context Hub 已安装或记录无法安装原因
- [ ] 无真实 provider
- [ ] 原测试通过
