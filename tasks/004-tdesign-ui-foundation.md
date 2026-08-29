# TASK 004 — TDesign UI Foundation

## Goal

将 TDesign MiniProgram 作为 UI dependency 接入，并统一首页基础视觉。

## Preconditions

TASK 003 完成。

## Allowed Changes

```text
miniprogram/package.json
miniprogram/package-lock.json
miniprogram/app.json
miniprogram/pages/home/**
miniprogram/components/**
README.md（仅 npm 构建说明）
```

## Implementation

1. npm 安装 TDesign MiniProgram。
2. 使用当前官方推荐的小程序 npm 构建方式。
3. 首页至少使用 TDesign Button / Cell / Card 之一。
4. 保留五个入口。
5. 建立少量全局 spacing / radius / typography 规范。

## UX

- 大点击区域
- 一屏少信息
- 不做 Dashboard
- 不复制 retail starter

## Do Not

- 不复制 TDesign 整个源码
- 不引入第二 UI framework
- 不做 Chat 页
- 不接 Backend

## Verification

```bash
cd miniprogram
npm install
```

人工在微信开发者工具“构建 npm”。

## Definition of Done

- [ ] TDesign dependency 正常
- [ ] 首页使用 TDesign
- [ ] 五个入口仍在
