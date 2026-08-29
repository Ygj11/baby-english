# UX_UI.md

## 1. 设计关键词

- 儿童友好
- 简单
- 大按钮
- 少文字
- 高反馈
- 语音优先
- 一次一个任务

UI 基础组件统一使用 TDesign MiniProgram。

## 2. 页面树

```text
Home
├── Chat
├── Camera
│   └── Photo Result
├── Textbook
│   └── Lesson
├── Scenario
│   └── Scenario Chat
├── Story
│   └── Story Detail
├── Wordbook
└── Profile
```

## 3. 首页原型

```text
┌───────────────────────────┐
│ 👋 Hi！今天想学什么？     │
│                           │
│   🎤 和我说英语           │
│   📷 拍一拍               │
│   📖 我的课本             │
│   🎭 场景英语             │
│   📚 英语故事             │
│                           │
│ 继续学习：PEP 三上 Unit 4 │
└───────────────────────────┘
```

## 4. Chat 页面

```text
┌───────────────────────────┐
│        AI Tutor            │
│                           │
│ AI: Apple 🍎              │
│ Repeat after me: apple.   │
│                           │
│ [🔊 再听] [🐢 慢点]        │
│ [🇨🇳 中文讲讲] [🎤 跟读]    │
│                           │
│ [键盘] [🎤 按住说话] [📷]   │
└───────────────────────────┘
```

禁止：

- 超长连续气泡
- 大段 Markdown
- 一次展示大量语法规则

## 5. Photo Result

```text
识别到：

PEP 三年级上册
Unit 4 — We Love Animals

What's this?
It's a dog.

[🔊 读给我听]
[💡 给我讲讲]
[🎤 跟我读]
[🎭 和我练]
```

OCR 原始文本属于 debug 信息，不作为默认儿童 UI。

## 6. Textbook

```text
PEP 三年级上册
██████░░ 62%

Unit 4
We Love Animals

A Let's Talk       [学习]
A Let's Learn      [学习]
B Let's Talk       [学习]
```

## 7. 场景

第一批：

- ✈️ 机场
- 🏨 酒店
- 🍔 餐厅
- 🛍️ 购物
- 🗺️ 问路
- 🏫 学校
- 🐼 动物园
- 🎢 游乐园

## 8. TDesign 映射

优先：

- Button
- Avatar
- Cell
- Card
- TabBar
- Toast
- Dialog
- Upload
- Progress
- Chat
- ChatSender
- ChatRecord

如果 TDesign 已有对应组件，不重复造组件。

## 9. 页面状态

至少考虑：

- initial
- loading
- success
- empty
- recoverable error
- fatal error

儿童错误提示：

正确：

> 没听清楚，再说一次吧 🎤

错误：

> ASR provider returned HTTP 502.
