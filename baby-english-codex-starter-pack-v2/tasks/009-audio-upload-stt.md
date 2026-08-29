# TASK 009 — Audio Upload + Batch STT Gateway

## Goal

完成 MVP batch voice 的前半段：

```text
MiniProgram audio
↓
upload
↓
audio validation
↓
optional FFmpeg normalization
↓
STTGateway
↓
transcript
```

不做 TTS。

## Allowed Changes

```text
server/app/api/voice.py
server/app/voice/**
server/app/main.py
server/tests/**
miniprogram/services/api.js
miniprogram/services/voice.js
miniprogram/pages/chat/**
.env.example
docs/API_CONTRACT.md
docs/PRIVACY_SECURITY.md（仅实际实现差异）
pyproject.toml
uv.lock
```

## Architecture

本 task 是 batch file transcription，不强迫 STT 通过 Pipecat realtime FrameProcessor。

创建极薄：

```text
STTGateway.transcribe(...)
```

实现策略：

1. 如果当前选定 Pipecat STT service 有自然、稳定的 batch 调用方式，可复用；
2. 否则使用 provider 官方 SDK/API；
3. provider-specific 代码不得进入 API/Tutor 层。

未来 realtime STT 仍由 Pipecat pipeline 负责。

## Provider Decision

先阅读：

```text
docs/PROVIDER_STRATEGY.md
```

必须提供：

```text
FakeSTT
```

如果 owner 尚未配置真实 STT：

完成 Fake + contract + integration boundary，不得由 Codex 自行注册/决定收费厂商。

## API

实现：

```text
POST /api/voice/transcribe
```

遵守 API contract。

## Audio Handling

接受微信录音常见格式。

如 provider 需要特定格式：

使用 FFmpeg 做薄 normalization。

不要自行实现 codec。

建议：

```text
server/app/voice/audio.py
```

要求：

- size limit
- temporary file cleanup
- unsupported type error
- empty audio error

## Privacy

原始上传音频默认属于临时数据。

请求处理完成后 cleanup，除非未来产品需求明确要求保存。

禁止把原始儿童音频写入 application log。

## MiniProgram

Recorder stop 后：

```text
upload
↓
显示“我听到：xxx”
```

失败：

> 没听清楚，再说一次吧 🎤

## Tests

至少：

- valid mocked audio → fake transcript
- empty file → 4xx
- oversized file → 4xx
- STT failure → mapped error
- temp cleanup

## Do Not

- 不做 TTS
- 不做 full voice turn
- 不做 streaming
- 不做 WebSocket
- 不做 pronunciation
- 不为了 Pipecat 人为构造复杂 batch pipeline
