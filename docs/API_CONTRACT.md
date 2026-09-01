# API_CONTRACT.md

除 `/api/health` 和临时媒体下载外，当前 Profile、Tutor、Voice、Pronunciation、Scenario、
Photo 与 Textbook 请求统一携带：

```text
X-Client-Id: <16–64 chars anonymous device id>
```

该值只用于隔离匿名客户端学习数据，不是认证凭证。缺失或非法返回 400。

## GET `/api/student/profile`

存在时返回：

```json
{"age":8,"grade":3,"english_level":"beginner"}
```

尚未设置返回 404。响应不暴露数据库 id 或 client id。

## PUT `/api/student/profile`

幂等 upsert：

```json
{"age":8,"grade":3,"english_level":"beginner"}
```

限制：`age` 6–12、`grade` 1–6、`english_level` 为 `starter | beginner | elementary`。非法输入返回 422 且不写数据库。

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
  "context": {
    "mode": "chat"
  }
}
```

Response:

```json
{
  "reply": "Apple 🍎. Repeat after me: apple",
  "language": "mixed",
  "repeat_text": "apple",
  "suggested_actions": [
    "repeat",
    "explain_zh"
  ]
}
```

规则：

- `message` 会 trim，长度为 1–2000 字符；
- 学生画像只从当前 `X-Client-Id` 对应的持久化 Profile 读取；
- Profile 不存在返回 409，且不调用 LLM；
- `context.mode` 当前只接受 `chat`；
- Text Chat 不生成音频，因此不返回 `listen`；
- 只有 Tutor 回复末尾存在唯一且合法的 `Repeat after me: <English target>` marker 时，
  `repeat_text` 才为该目标并提供 `repeat`；否则 `repeat_text` 为 `null` 且不提供 `repeat`；
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
```

限制：

- age、grade、english level 从持久化 Profile 读取，不再接受业务所需 form 字段；
- Profile 不存在返回 409，且不调用 STT、LLM 或 TTS；
- 音频文件限制与 `/api/voice/transcribe` 一致。

Response：

```json
{
  "transcript": "苹果英文怎么说",
  "reply": "Apple 🍎. Repeat after me: apple",
  "repeat_text": "apple",
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

## POST `/api/pronunciation/evaluate`

Content-Type：`multipart/form-data`，并携带合法 `X-Client-Id`。

Form：

```text
file=<16 kHz / mono / MP3>
reference_text=<1–12 word English target>
```

Backend 要求该 client 已有 Student Profile，按目标确定 `read_word` 或
`read_sentence`，不调用 STT、LLM 或 TTS。无 Profile 返回 409；非法 reference/audio
返回 400，超限音频返回 413，provider 配置或请求失败返回安全的 503。

Response 只包含规范化结果：

```json
{
  "attempt_id": 1,
  "reference_text": "banana",
  "overall_score": 86,
  "accuracy_score": 82,
  "fluency_score": 91,
  "completeness_score": 100,
  "standard_score": 84,
  "rejected": false,
  "words": [{"word":"banana","score":82}],
  "feedback": "不错！慢一点，再试一次会更清楚。"
}
```

原始音频在请求结束后删除；响应不包含 provider XML、凭据、鉴权 URL 或 upstream
WebSocket URL。

## Scenario English

以下 endpoint 均要求合法 `X-Client-Id` 和已存在的 Student Profile：

```text
GET  /api/scenarios
GET  /api/scenarios/{scene_id}
POST /api/scenarios/{scene_id}/sessions
POST /api/scenarios/sessions/{session_id}/turn
POST /api/scenarios/sessions/{session_id}/voice-turn
POST /api/scenarios/sessions/{session_id}/complete
```

目录仅返回四个服务端儿童场景、公开 goal 字段和当前 progress；不返回 persona、
success criteria 或 system prompt。启动 session 会清除同 client/scene 的旧 active
session，并把确定性 opening line 保存为 `idx=0`，不会调用 LLM。

Text turn request：

```json
{"message":"Can I have a sandwich, please?"}
```

Backend 从数据库读取有序 history；客户端不能提交或重写 history。成功后一次写入
user/assistant pair，provider 失败不留下单边 user turn。单 session 最多保留约 40 个
turn。Voice turn 复用现有临时上传、STT、LLM、TTS 和 `/api/voice/media/{id}`，不保存音频。

`complete` 至少需要一个 learner turn。成功时返回本 session 的
`completed_goal_ids`、短 `summary`/`tip` 和累计 progress；在同一事务中更新 durable
goal progress 并删除 raw turns。已完成 session 重试不会再次 assessment 或增加计数。

## Photo English

以下 endpoint 均要求合法 `X-Client-Id` 和已存在的 Student Profile；Profile 缺失返回
409，并在 Vision 调用前短路。

### POST `/api/photo/analyze`

`multipart/form-data` 的 `file` 只接受单个 JPEG/PNG/WebP 静态图，最大 8 MiB。Backend
使用 Pillow 验证真实格式、像素上限和动画状态，应用 EXIF orientation，把长边限制为
1600 px 后重编码为无元数据 JPEG。原始与归一化临时文件在所有路径删除。

成功响应包含 `status=ok`、owner-scoped `record_id`、一个主词、中英例句、1–8 个英文词
的 `practice_phrase`、最多四个相关词、问题、鼓励语和 `listen/repeat/practice_chat`
动作。只把这些安全教学字段写入数据库。

模糊或不适合学习的图片分别返回 `status=unclear | unsuitable`、安全的 `message_zh`、
`record_id=null` 和 `suggested_actions=["retake"]`，不写学习记录。Provider 失败返回不含
内部详情的 503。

### POST `/api/photo/records/{record_id}/listen`

只读取当前 client 拥有的已持久化 `practice_phrase`，复用现有 `TTSGateway` 与
`TemporaryMediaStore`，返回 `{"audio_url":"/api/voice/media/..."}`。客户端不能提交任意
TTS 文本；非 owner 返回 404，TTS 失败返回安全 503。

## Textbook

所有 `/api/textbooks` endpoint 都要求合法 `X-Client-Id` 和已存在的 Student Profile。

- `GET /api/textbooks`：只返回已索引书目的公开字段与 `selected`，不返回正文、向量或路径。
- `GET /api/textbooks/{textbook_id}/units`：返回按 `unit_no` 排序的 Unit；未知书目返回 404。
- `GET /api/textbooks/current`：返回 `{textbook,current_unit_no,units}`；未选择时 `textbook=null`。
- `PUT /api/textbooks/current`：以 `{textbook_id,current_unit_no}` 幂等保存当前 client 的选择；
  Unit 必须属于该书。
- `POST /api/textbooks/ask`：以 `{question}` 查询当前课本/Unit，返回短 `answer`、`found` 和
  去重的 `{unit_no,unit_title,lesson,page}` sources。无选择返回 409；索引、Embedding 或 LLM
  不可用返回不泄露内部信息的 503。

教材包只能通过服务端 CLI 导入，没有公开 upload/download endpoint。数据库会话在
Embedding/LLM 调用前关闭。

## GET `/api/voice/media/{media_id}`

返回 `/api/voice/turn` 生成的临时音频二进制。未知或过期的 `media_id` 返回 404；音频默认保留 5 分钟。

## Future Namespaces

```text
/api/auth/*
/api/vision/*
/api/stories/*
/api/words/*
/api/payments/*
/api/subscriptions/*
```

Tasks 001–010 不提前实现。
