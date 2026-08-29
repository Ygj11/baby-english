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
    "listen",
    "repeat",
    "explain_zh"
  ]
}
```

规则：

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

Response:

```json
{
  "text": "苹果英文怎么说",
  "duration_ms": 1830
}
```

## POST `/api/voice/speak`

Request:

```json
{
  "text": "Apple. Repeat after me: apple.",
  "voice": "teacher",
  "speed": 0.95
}
```

第一阶段允许：

- 返回音频二进制
- 或返回临时 audio URL

选定实现后更新本文件。

## POST `/api/voice/turn`

目标：

```text
transcribe + tutor + speak
```

Request：

multipart/form-data，至少：

```text
file
age
grade
english_level
```

Response 示例：

```json
{
  "transcript": "苹果英文怎么说",
  "reply": "Apple 🍎. Repeat after me: apple.",
  "audio_url": "/api/media/abc123",
  "suggested_actions": [
    "repeat",
    "explain_zh"
  ]
}
```

Task 010 完成后以实际实现为准更新。

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
