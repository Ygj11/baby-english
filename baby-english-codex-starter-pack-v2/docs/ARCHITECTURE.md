# ARCHITECTURE.md

## 1. 总体架构

```text
微信小程序
│
│ HTTPS / WebSocket（后续）
▼
FastAPI Application
│
├── Tutor
├── Voice
├── Vision
├── Textbook
├── Users
└── WeChat
    │
    ├── Pipecat
    │   ├── STT
    │   ├── LLM
    │   ├── TTS
    │   └── Voice Pipeline
    │
    ├── LlamaIndex
    ├── Pronunciation Provider
    └── PostgreSQL
```

## 2. 项目母仓库

本项目不是任何第三方应用的 Fork。

母仓库：

```text
baby-english
```

第三方以 dependency / source donor 方式使用。

## 3. Pipecat

Pipecat 是 Python dependency。

类似 Java 项目中的 framework dependency。

核心负责：

- realtime Voice pipeline
- realtime STT/TTS services
- voice processing
- transport integration
- conversation pipeline primitives

对于 MVP 的 batch HTTP voice turn，不强迫所有调用通过 Pipecat FrameProcessor。
应用层可以使用薄 `STTGateway` / `TTSGateway`，具体实现可复用 Pipecat service 或 provider 官方 SDK。

原则：

- 不 Fork Pipecat
- 不修改 Pipecat framework 源码
- provider 差异封装在 `server/app/voice/`

## 4. Source Donors

### pipecat-examples

用于参考：

- push-to-talk
- websocket
- study companion
- storytelling
- travel companion

### Spoken

用于迁移/参考：

- scenario
- correction
- pronunciation / ISE
- dictionary
- wordbook
- learning report

Spoken 不决定总体架构。

### 微信官方 miniprogram-demo

优先参考：

- Recorder
- Camera
- Login
- Subscribe
- Share
- Storage
- Socket
- Upload

## 5. MiniProgram

使用：

- 原生微信 MiniProgram
- TDesign MiniProgram

目标：

```text
miniprogram/
├── pages/
├── components/
├── services/
├── utils/
├── app.js
├── app.json
└── app.wxss
```

## 6. Backend

目标：

```text
server/
├── app/
│   ├── main.py
│   ├── api/
│   ├── voice/
│   ├── tutor/
│   ├── vision/
│   ├── textbook/
│   ├── pronunciation/
│   ├── users/
│   └── wechat/
└── tests/
```

## 7. Provider Strategy

核心业务不得直接绑定具体 provider。

通过环境变量配置：

```text
STT_PROVIDER=
LLM_PROVIDER=
TTS_PROVIDER=
```

第三方差异由 server adapter/factory 隔离。

## 8. 第一阶段 Voice 模式

MVP：

```text
Push to Talk
↓
完整一句
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

暂不要求：

- full duplex
- barge-in
- WebRTC
- continuous realtime conversation

## 9. RAG

MVP：

```text
LlamaIndex
```

第一本教材：

```text
PEP 三年级上册
```

大量教材后再评估 RAGFlow。

## 10. Database

建议长期使用：

- PostgreSQL
- SQLAlchemy
- Alembic

但 Tasks 001–010 不提前建设复杂数据库。

## 11. External API Boundary

小程序只调用本项目 API：

```text
/api/health
/api/tutor/chat
/api/voice/transcribe
/api/voice/speak
/api/voice/turn
```

禁止小程序直连第三方 AI provider。
