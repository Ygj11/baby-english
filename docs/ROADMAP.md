# ROADMAP.md

## Milestone 0 — Engineering Baseline

目标：

- Repo 可安装
- Python 环境确定
- Pipecat 接入
- 微信小程序骨架存在
- TDesign 可用
- Backend health 可访问

Tasks：001–005

## Milestone 1 — Text Tutor

目标：

```text
小程序文字输入
↓
Tutor
↓
LLM
↓
儿童化回答
```

Tasks：006–007

## Milestone 2 — Push-to-Talk Voice Tutor

目标：

```text
录音
↓
上传
↓
STT
↓
Tutor
↓
LLM
↓
TTS
↓
播放
```

Tasks：008–010

这是第一阶段最关键里程碑。

## Milestone 3 — WeChat Identity

后续：

- wx.login
- code2session
- user
- token/session

## Milestone 4 — Scenario English

后续：

- travel
- restaurant
- school
- shopping
- roleplay
- correction

## Milestone 5 — Pronunciation

后续：

- ISE
- repeat UI
- child-friendly score

## Milestone 6 — Vision

```text
拍照
↓
VLM
↓
结构化识别
```

## Milestone 7 — Textbook

- textbook model
- first PEP book
- LlamaIndex
- metadata
- QA

## Milestone 8 — Photo + Textbook

```text
拍课本
↓
识别 Unit/Page
↓
RAG
↓
讲解
↓
跟读
↓
发音评分
```

## Milestone 9 — Story / Learning Memory

- stories
- wordbook
- learning sessions
- progress

## Milestone 10 — Commercialization

- payment
- membership
- subscribe message
- deployment
- privacy
- parent consent


## Provider Decision Gates

- Task 006 前：若要真实联调，准备 LLM key。
- Task 009 前：若要真实联调，确定 STT。
- Task 010 前：若要真实联调，确定 TTS。

没有真实 key 时，Fake provider + contract + test 仍应完成。
