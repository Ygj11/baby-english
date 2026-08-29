# TASK 003 — Initialize WeChat MiniProgram

## Goal

创建干净的微信原生小程序骨架。

不接 Backend，不安装 TDesign。

## Allowed Changes

```text
miniprogram/**
.gitignore
README.md（开发者工具说明）
```

## Implementation

创建：

```text
miniprogram/
├── app.js
├── app.json
├── app.wxss
├── sitemap.json
├── project.config.json.example
├── pages/
│   └── home/
│       ├── index.js
│       ├── index.json
│       ├── index.wxml
│       └── index.wxss
└── services/
```

Home 显示五个入口：

- 和我说英语
- 拍一拍
- 我的课本
- 场景英语
- 英语故事

不提交真实 AppID。

## Do Not

- 不引入 TDesign
- 不接 API
- 不写 Recorder
- 不做支付/登录
- 不使用 uni-app/Taro

## Acceptance

微信开发者工具可打开并编译。

Codex 无法运行开发者工具时，必须给人工 smoke test 步骤。

## Definition of Done

- [ ] 原生 MiniProgram 结构存在
- [ ] 五个入口可见
- [ ] 无真实 AppID
