# TASK 007 — Child Tutor Policy

## Goal

把普通 Chat 升级为儿童英语 Tutor。

## Allowed Changes

```text
server/app/tutor/**
server/tests/**
docs/API_CONTRACT.md
miniprogram/pages/chat/**（仅 suggested actions）
```

## Implementation

建议：

```text
server/app/tutor/
├── child_policy.py
├── prompt_builder.py
├── service.py
└── schemas.py
```

输入：

- age
- grade
- english_level

Levels：

```text
starter
beginner
elementary
```

## Required Rules

Starter/Beginner：

- 短句
- 中文可辅助
- 一次一个知识点
- 新词不超过 2–3 个
- 鼓励跟读
- 避免复杂语法术语

Elementary：

- 增加英文比例
- 可解释简单语法
- 仍保持短

## Suggested Actions

至少：

```text
listen
repeat
explain_zh
```

前端不要解析 reply 猜按钮。

## Golden Tests

Age 8 / Beginner：

> 苹果英文怎么说？

测试 policy/prompt 要求：

- apple
- invite repeat
- concise

Age 11 / Elementary：

> apple和apples有什么区别？

policy 允许解释 plural。

测试不要依赖真实 LLM 随机输出。

## Do Not

- 不加 DB profile
- 不加 memory
- 不做 story/scenario
