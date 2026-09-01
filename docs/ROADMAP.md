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

Task 018 已实现的 MVP：

- travel / restaurant / school / child-safe shopping 服务端目录
- text + batch voice role-play
- active-session conversation memory
- structured scene goal progress
- completion 后 raw transcript 删除

每轮 correction、自定义场景、全局历史和长期记忆推断仍为后续能力。

## Milestone 5 — Pronunciation

Task 017 已实现的离线验收范围：

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

Task 020 已实现的基础范围：

- SQLAlchemy textbook/unit/client selection metadata
- repo 外结构化 source package 与安全 CLI ingestion
- LlamaIndex chunk/index/persistence/Unit-filtered retrieval
- Qwen 1024 维 embedding + existing Qwen LLM grounded QA
- 服务端目录与小程序课本/Unit/问答页面

仓库未捆绑第一本真实 PEP 教材；PDF/OCR、拍照匹配教材页、quiz、wordbook 和教材语音链路
仍属于后续 task。

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
