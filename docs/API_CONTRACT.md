# API_CONTRACT.md

## GET `/api/health`

Response:

```json
{
  "status": "ok",
  "service": "baby-english"
}
```

## POST `/api/tutor/chat`

Request:

```json
{
  "message": "苹果英文怎么说？",
  "student": {
    "age": 8,
    "grade": 3,
    "english_level": "beginner"
  },
  "context": {
    "mode": "chat"
  }
}
```

Response:

```json
{
  "reply": "Apple 🍎. Repeat after me: apple.",
  "language": "mixed",
  "suggested_actions": [
    "repeat",
    "explain_zh"
  ]
}
```

规则：

- `message` 会 trim，长度为 1–2000 字符；
- `student.age` 为 5–15，`student.grade` 为 1–9；
- `context.mode` 当前只接受 `chat`；
- Text Chat 不生成音频，因此不返回 `listen`；
- `explain_zh` 由客户端使用最后一条 AI 回复再次调用本接口，请求简短中文解释；
- 不向前端暴露 provider raw response。
- 不返回内部 prompt。
- 不返回 chain-of-thought。

## POST `/api/voice/transcribe`

Content-Type:

```text
multipart/form-data
```

Form：

```text
file=<audio>
```

限制：

- 最大 10 MiB；
- 支持常见的 MP3、M4A、AAC、WAV、MP4、OGG、WebM 文件；
- 当前 `qwen_audio` 真实 adapter 直接支持 16 kHz MP3 和 WAV；其他已接收格式会返回受控错误，不会伪装成 MP3；
- 原始上传只写入临时文件，请求结束后删除。

Response:

```json
{
  "text": "苹果英文怎么说",
  "duration_ms": 1830
}
```

## POST `/api/voice/speak` — 未实现

当前没有独立 Text-to-Speech endpoint。客户端不得把该路径视为可用 API；如后续 Roadmap 实现，需另行定义请求、响应和音频生命周期。

## POST `/api/voice/turn`

Content-Type：

```text
multipart/form-data
```

Form：

```text
file=<audio>
age=8
grade=3
english_level=beginner
```

限制：

- `age` 为 5–15；
- `grade` 为 1–9；
- `english_level` 为 `starter`、`beginner` 或 `elementary`；
- 音频文件限制与 `/api/voice/transcribe` 一致。

Response：

```json
{
  "transcript": "苹果英文怎么说",
  "reply": "Apple 🍎. Repeat after me: apple.",
  "audio_url": "/api/voice/media/abc123",
  "suggested_actions": [
    "listen",
    "repeat",
    "explain_zh"
  ]
}
```

`audio_url` 指向本项目：

```text
GET /api/voice/media/{media_id}
```

当前为进程内临时音频，默认有效期 5 分钟；不返回 provider 原始 URL，也不在 JSON 中放入 base64 音频。

`listen` 只对应本次 response 的 `audio_url`。`explain_zh` 使用本次 `reply` 作为上下文调用 `/api/tutor/chat`，解释结果属于 Text Chat，不附带音频。

## GET `/api/voice/media/{media_id}`

返回 `/api/voice/turn` 生成的临时音频二进制。未知或过期的 `media_id` 返回 404；音频默认保留 5 分钟。

## Future Namespaces

```text
/api/auth/*
/api/scenarios/*
/api/pronunciation/*
/api/vision/*
/api/textbooks/*
/api/stories/*
/api/words/*
/api/payments/*
/api/subscriptions/*
```

Tasks 001–010 不提前实现。
