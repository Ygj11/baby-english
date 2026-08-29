# TASK 006 — Text Chat MVP

## Goal

完成：

```text
MiniProgram text
↓
POST /api/tutor/chat
↓
LLM adapter
↓
reply
```

儿童 Prompt 深化由 Task 007 完成。

## Allowed Changes

```text
server/app/api/**
server/app/tutor/**
server/app/main.py
server/tests/**
miniprogram/pages/chat/**
miniprogram/pages/home/**
miniprogram/services/api.js
miniprogram/services/chat.js
.env.example
docs/API_CONTRACT.md
```

## Provider Decision

先阅读：

```text
docs/PROVIDER_STRATEGY.md
```

Codex 不得自行选择付费 LLM 厂商。

必须实现 `FakeLLM`。

若 `.env` 已配置 owner 选择的真实 provider，则实现对应最小 adapter；没有 key 时，不阻塞 Fake + API contract。

## Backend

实现：

```text
POST /api/tutor/chat
```

建立 LLM adapter boundary。

建议：

```text
server/app/tutor/llm.py
server/app/tutor/service.py
```

LLM provider：

- 环境变量配置
- 无硬编码 key
- 测试使用 FakeLLM

## MiniProgram

创建 Chat：

- 文本输入
- Send
- AI reply
- loading
- error

优先使用 TDesign Chat 相关组件；组件名称以安装版本为准，不猜。

## Baseline Prompt

仅：

> You are an English tutor for a Chinese primary school student. Keep responses concise.

## Tests

必须：

- FakeLLM 固定 reply
- contract test
- provider failure test

## Do Not

- 不做语音
- 不做 streaming
- 不做 conversation persistence
- 不做教材
