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
├── Student Profile
├── Pronunciation
├── Scenario English
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
    └── SQLAlchemy / Alembic → SQLite（当前）/ PostgreSQL（未来）
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
│   ├── photo/
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
APP_ENV=development
LLM_PROVIDER=qwen
STT_PROVIDER=qwen_audio
TTS_PROVIDER=qwen_audio
```

第三方差异由 server adapter/factory 隔离。

发音练习保持独立边界：

```text
POST /api/pronunciation/evaluate
→ PronunciationService
→ PronunciationGateway (Fake | Xunfei ISE)
→ normalized PronunciationResult
→ PronunciationAttemptRepository
```

讯飞 adapter 独占 HMAC 鉴权、WebSocket 帧和 XML 解析；API/业务层只处理规范化
0–100 分数。上传 MP3 是请求期临时文件，结果通过 SQLAlchemy/Alembic 保存，但原始
音频和 provider XML 均不持久化。`X-Client-Id` 仍只是匿名数据 namespace，不是认证。

默认 Batch Voice MVP 的 LLM/STT/TTS 共用 Alibaba Model Studio 北京 Workspace；DeepSeek 和 MiniMax adapters 保留但不参与默认链路。

Photo English 复用同一北京 Workspace，但保持独立的薄边界：

```text
temporary_image (Pillow verify / EXIF transpose / resize / metadata strip)
→ PhotoLearningService
→ VisionGateway (Fake | Qwen qwen3.7-flash)
→ strict Pydantic structured output
→ domain result guard
→ PhotoLearningRepository（仅 status=ok）
```

Profile read session 在 Vision 调用前关闭；成功结果只在 provider 返回后开启短写事务。
原图与归一化 JPEG 都由临时上下文在成功/失败路径删除。

`development` / `test` 允许 Fake provider；`production` 禁止 provider 为空或 `fake`，避免漏配时静默运行测试实现。

## 8. 第一阶段 Voice 模式

MVP 使用 Batch Push-to-Talk：

```text
微信小程序 RecorderManager
↓
录完一句
↓
HTTP upload
↓
STTGateway
↓
Tutor / LLM
↓
TTSGateway
↓
音频返回
↓
小程序播放
```

这条路径优先验证：

- 儿童是否愿意开口
- STT 是否够准
- Tutor 回答是否合适
- TTS 是否自然
- 整体延迟是否可接受

MVP 不要求为了使用 Pipecat 而把 batch 文件请求转换成 realtime frames。

后续 realtime voice 再进入：

```text
MiniProgram realtime transport
↓
Pipecat transport
↓
Pipecat frame pipeline
↓
STT → Tutor/LLM → TTS
```

Realtime 阶段再处理：

- streaming
- continuous conversation
- barge-in
- realtime turn-taking
- WebSocket / WebRTC compatibility

Tasks 009–010 只证明 Batch Voice Loop，不代表 realtime voice 已完成。


## 9. RAG

Task 020 的教材 RAG：

```text
repo 外 manifest.json + content.jsonl
→ 校验与稳定 source SHA-256
→ LlamaIndex IngestionPipeline + SentenceSplitter(384/48)
→ 显式 Qwen qwen3.7-text-embedding（1024 维）
→ SimpleVectorStore / StorageContext.persist（每本书一个受保护索引）

child question + client-scoped current textbook/unit
→ TextbookRetriever（index manifest compatibility + exact Unit metadata filter）
→ provider-neutral RetrievedTextbookChunk
→ TextbookQAService
→ existing LLMGateway
→ short grounded answer + compact source location
```

SQLAlchemy 只保存 catalogue、Unit 和 child selection 元数据；教材正文和 embeddings 只存在
Git 忽略的运行时索引中。每次 index/retrieval 都显式传 embedding，禁止 LlamaIndex 默认
OpenAI embedding/LLM。当前没有导入任何真实 PEP 内容，也不实现 RAGFlow、OCR 或外部向量库。

## 10. Database

Task 016 起使用：

- SQLAlchemy 2.x async API；
- Alembic 作为唯一 schema migration 机制；
- 本地默认 `sqlite+aiosqlite:///./baby_english.db`；
- 每个请求由 FastAPI dependency 管理独立 `AsyncSession`；
- `StudentProfileRepository` 隔离 ORM，返回 Tutor 既有 domain `StudentProfile`。

当前表包括 `student_profiles`、`pronunciation_attempts`、`photo_learning_records`、
`textbooks`、`textbook_units` 与 `student_textbooks`。未来可切 PostgreSQL，
但当前不安装 PostgreSQL driver，也不让 Tutor/Voice/Provider adapter 直接依赖数据库。

匿名数据 owner 由小程序稳定保存的 `X-Client-Id` 提供。它只是数据 namespace，不是认证 token；缺失或非法时不回退共享 `anon`。

Scenario English 增加三个专用表：`scenario_sessions`、active-only
`scenario_turns` 与 `scene_goal_progress`。完成场景时在一个本地事务内写结构化结果、
upsert goal progress 并删除 raw turns，不引入通用 UnitOfWork 或 Memory framework。

```text
StudentProfile + ChildTutorPolicy + Scene + Goals + ordered active history
→ existing LLMGateway
→ short role-play reply

complete
→ SceneGoalAssessor
→ atomic structured progress + raw-turn deletion
```

## 11. External API Boundary

小程序只调用本项目 API：

```text
/api/health
/api/student/profile
/api/tutor/chat
/api/voice/transcribe
/api/voice/turn
/api/voice/media/{media_id}
/api/pronunciation/evaluate
/api/scenarios
/api/scenarios/{scene_id}/sessions
/api/scenarios/sessions/{session_id}/*
/api/photo/analyze
/api/photo/records/{record_id}/listen
/api/textbooks
/api/textbooks/{textbook_id}/units
/api/textbooks/current
/api/textbooks/ask
```

`/api/voice/speak` 尚未实现，不属于当前可用 API boundary。

禁止小程序直连第三方 AI provider。
