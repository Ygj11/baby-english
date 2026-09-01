# TASK 016 — Persistence Foundation + Student Profile

## Goal

把当前每次请求硬编码 `8 / 3 / beginner` 的学生画像升级为正式后端持久化：

```text
MiniProgram
→ X-Client-Id
→ FastAPI
→ StudentProfileService
→ StudentProfileRepository
→ SQLAlchemy 2.x
→ SQLite
```

Schema 从第一张表开始由 Alembic 管理，未来可切 PostgreSQL 而不改 Tutor / Voice / MiniProgram 业务结构。

完成后：
- Profile 持久化 `age / grade / english_level`；
- Chat / Voice 不再传硬编码学生字段；
- API 层读取 Profile 后显式传给现有 `TutorService.reply(message, student)`；
- Tutor / Child Tutor Policy / LLMGateway 不直接依赖数据库；
- MiniProgram 有“学习设置”页；
- 默认 tests 全离线。

不实现 Session、Learning Progress、ISE、Scene Goals、SRS、长期记忆。

---

## Required Context

阅读：`AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/API_CONTRACT.md`、`docs/DATA_MODEL.md`、`docs/PRIVACY_SECURITY.md`、`docs/TEST_PLAN.md`、`docs/SETUP.md`、本 Task。

## Source Audit Findings

当前源码已确认：
- `StudentProfile(age, grade, english_level)` 已是 Tutor domain input；
- `TutorService.reply(message, student)` 边界正确，必须保留；
- `miniprogram/services/chat.js` 与 `voice.js` 均硬编码 `8 / 3 / beginner`；
- Backend `/api/tutor/chat`、`/api/voice/turn` 当前每次请求都要求这些字段；
- repo 尚未安装 SQLAlchemy/Alembic，但 `ARCHITECTURE.md` 已确定 PostgreSQL + SQLAlchemy + Alembic。

**不要让 TutorService 自己查数据库。** 应由 API/application layer 取 Profile，再调用 TutorService。

---

## Reference Guidance — Spoken

只做本 Task 相关 JIT audit，优先读：

```text
references/spoken/backend/app/db.py
references/spoken/backend/app/core/deps.py
references/spoken/backend/app/models/session.py
references/spoken/backend/app/models/practice.py
references/spoken/backend/app/services/sessions.py
references/spoken/backend/app/services/users.py
references/spoken/backend/tests/conftest.py
references/spoken/backend/tests/test_sessions.py
references/spoken/backend/tests/test_practice.py
```

借鉴：`DATABASE_URL`、SQLAlchemy 2 typed ORM、per-client 数据隔离、API/persistence 分层、临时 SQLite tests、未来登录后 claim 匿名数据的演进思路。

不要照搬：
- `Base.metadata.create_all() + 手写 ALTER TABLE` migration；本项目用 Alembic；
- 缺 client id 时共享 `anon`；
- JWT/email auth/User；
- Session/Turn/Score/PracticeRecord；
- React/Zustand；
- Postgres driver。

Spoken 本地 reference 来自 ZIP、无 Git metadata。本 Task 默认只借设计，不逐行复制 persistence 源码；若确需复制，先满足 `AGENTS.md` 的 source revision + `THIRD_PARTY_NOTICES.md` 要求。

---

## Scope Rule

Task scope strict; file scope flexible。允许修改本 Task 直接需要的 dependency/config/API/MiniProgram/tests/docs/migrations。

禁止顺手实现：微信登录、User/WeChatIdentity、Session/Turn/Score、Learning Progress、Scene/Goals、ISE、PronunciationAttempt、Word/SRS、Long-term Memory、Vision、Textbook/RAG、PostgreSQL deployment、通用 CRUD/Repository Framework。

---

# 1. Persistence Foundation

通过 `uv add` 增加：

```text
SQLAlchemy 2.x
Alembic
aiosqlite
```

Backend 当前以 async route/provider 为主，使用 SQLAlchemy async API：

```text
create_async_engine
async_sessionmaker
AsyncSession
```

`.env.example`：

```env
DATABASE_URL=sqlite+aiosqlite:///./baby_english.db
```

暂不安装 PostgreSQL/MySQL driver。

建立最小 persistence boundary，至少有：Declarative Base、AsyncEngine、session factory、FastAPI session dependency、DATABASE_URL config。

规则：session 生命周期由 dependency 管理；repository 不读取 HTTP request；domain model 不依赖 SQLAlchemy；不造通用数据库框架。

---

# 2. Alembic Baseline

初始化 Alembic，metadata 指向 baby-english SQLAlchemy Base。

第一版 migration 创建：

```text
student_profiles
```

必须可在空 SQLite 上执行：

```bash
uv run --env-file .env alembic upgrade head
```

自动测试使用**临时 DB**验证：

```text
upgrade head → downgrade base → upgrade head
```

禁止：
- app startup 用 `create_all()` 代替 migration；
- Spoken 式 `_migrate_sqlite()` / PRAGMA ALTER schema migration；
- 对用户真实开发 DB 做 destructive downgrade test。

---

# 3. Student Profile Domain / Table

第一版只收集：

```text
age: 6–12
grade: 1–6
english_level: starter | beginner | elementary
```

不要加入姓名、生日、学校、班级、性别、手机号、头像、家长信息、learning_preference、current_textbook。

项目只保留一个 canonical `StudentProfile` domain type。现有 dataclass 可移动或保留，但不能再创建第二个同义 domain model。ORM model 与 API Pydantic schema 可独立，但不要把 ORM object 传入 Tutor。

表至少：

```text
id
client_id
age
grade
english_level
created_at
updated_at
```

要求：`client_id` non-null + unique/index；一个 client 一个 Profile；API 不暴露 DB id/client_id；不提前加 `user_id`。

---

# 4. StudentProfileRepository

建立薄 boundary：

```text
StudentProfileRepository
├── get(client_id)
└── save/upsert(client_id, profile)

SQLAlchemyStudentProfileRepository
```

要求：
- 返回 domain `StudentProfile`，不是 ORM object；
- 同一 client upsert 不重复建 row；
- client A 不能读 client B；
- 不做 UniversalRepository/generic CRUD。

思想与 `LLMGateway` 相同：业务依赖稳定接口，底层实现可替换。

---

# 5. Anonymous Client Identity

没有微信登录也必须隔离不同 MiniProgram client 数据，不能共享 `anon`。

MiniProgram 新增薄 client-id service：首次生成匿名 id → `wx.storage` 保存 → 后续稳定复用。

这里允许 wx.storage 保存 client id；**Student Profile 主数据仍在 Backend SQLite。** client id 只是数据 namespace，不是认证 token。

统一 `miniprogram/services/api.js` 给 `wx.request` 和 `wx.uploadFile` 自动加：

```text
X-Client-Id: <id>
```

不要在 chat/voice/profile service 重复拼 header。

Backend 建统一 dependency：Profile/Tutor/Voice 主路径必须有有效 id；缺失/非法返回 controlled 4xx；不回退共享 `anon`；限制长度；普通日志不打印完整 id。

---

# 6. Student Profile API

新增：

```text
GET /api/student/profile
PUT /api/student/profile
```

owner 来自 `X-Client-Id`。

GET 存在时返回：

```json
{"age":8,"grade":3,"english_level":"beginner"}
```

不存在返回 `404`。

PUT 使用相同 JSON，语义为 idempotent upsert：missing→create，existing→update。输入非法不得写 DB。

---

# 7. Tutor Chat Integration

正常 `/api/tutor/chat` contract 删除 `body.student`。

新主路径：

```text
POST /api/tutor/chat + X-Client-Id
→ Profile Repository
→ StudentProfile
→ TutorService.reply(message, student)
```

正常 JSON：

```json
{"message":"苹果英文怎么说？","context":{"mode":"chat"}}
```

要求：
- TutorService / PromptBuilder 不访问 DB；
- Profile missing → `409`（或统一 prerequisite 4xx）；
- 不 fallback 到 `8/3/beginner`；
- missing Profile 时 LLM 不调用；
- provider error isolation 不退化。

直接调用 TutorService 的 provider tests 仍可显式构造 StudentProfile。

---

# 8. Voice Turn Integration

当前 multipart：

```text
file + age + grade + english_level
```

改为主路径仅：

```text
file
```

Profile 从 `X-Client-Id` 读取：

```text
file → STT
stored Profile + transcript → Tutor
reply → TTS
```

要求：
- `miniprogram/services/voice.js` 删除 hardcoded profile form fields；
- Backend 不再依赖 form age/grade/level；
- Profile missing 时 STT/LLM/TTS 都不调用；
- latency log、temporary audio cleanup、provider error isolation 不退化。

---

# 9. MiniProgram Profile Service + UI

新增薄 service：

```text
getProfile()
saveProfile(profile)
```

只调用项目自己的 Profile API。

新增轻量“学习设置”页，字段仅年龄/年级/英语水平，使用原生 MiniProgram + 现有 TDesign。

要求：
- 可读取已有 Profile 并回填；
- 保存后 Chat/Voice 立即使用新 Profile；
- Home 保留现有五个主入口，设置页不要变成第六个同级核心入口；
- 提供自然的设置入口；
- 首次进入 Chat 且 Profile 不存在时，引导设置，不要等发消息后只显示“服务不可用”；
- 不做复杂 onboarding。

---

# 10. Error Semantics

至少区分：

```text
400/422  client/profile 输入非法
404      GET profile 尚不存在
409      Tutor/Voice 缺 Profile 前置条件
503      AI Provider unavailable
```

MiniProgram 不得把“缺 Profile”显示成 provider outage。

---

# 11. Tests

默认全部 offline，不需要真实 Qwen Key。

Backend 至少覆盖：
- temp SQLite session；
- Alembic empty DB upgrade/downgrade/upgrade；
- Repository create/get/upsert/update/client isolation/missing；
- Profile GET missing、PUT create/update、validation、client-id validation；
- API response 不暴露 internal id/client id；
- Tutor 从 stored Profile 构造 prompt，request 不再要求 `student`；
- 不同 client Profile 正确隔离；
- missing Profile → 409 且 LLM 不调用；
- Voice 不再要求 age/grade/level form；
- missing Profile → 409 且 STT/LLM/TTS 都不调用；
- Fake voice loop / audio cleanup 不退化。

更新 real-provider HTTP E2E setup：

```text
PUT profile → tutor/chat → voice/turn
```

real-provider tests 继续 opt-in，本 Task DoD 不要求真实网络调用。

MiniProgram tests 至少覆盖：
- client id 第一次生成 + storage + 稳定复用；
- request/upload 自动带相同 `X-Client-Id`；
- chat 不再发 hardcoded student；
- voice 不再发 hardcoded age/grade/level；
- profile GET/PUT；
- Profile 页面读取/保存核心逻辑；
- missing Profile 的 Chat 设置引导；
- 现有 chat/audio tests 不退化。

不得删除/skip 旧 tests 强行通过。

---

# 12. Docs / Security

根据最终实现更新至少：

```text
.env.example
.gitignore
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/DATA_MODEL.md
docs/PRIVACY_SECURITY.md
docs/SETUP.md
docs/TEST_PLAN.md
```

`.gitignore` 增加本地 DB 产物，例如：

```text
*.db
*.sqlite
*.sqlite3
```

不要忽略 Alembic migrations。

文档明确：Profile 现在是持久化学习数据；当前只收集 age/grade/english_level；client id 只作匿名 namespace、不是认证；不收集姓名/学校/生日；SQLite 文件不提交；未来 User/WeChat identity 与 StudentProfile 分离；启动前执行 `alembic upgrade head`。

---

# 13. Definition of Done — Codex Only

执行并报告：

```bash
uv run pytest
```

使用临时 SQLite 验证：

```text
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

如已配置 autogenerate，再执行：

```bash
uv run alembic check
```

MiniProgram：

```bash
cd miniprogram
npm test
```

Static hygiene：

```bash
git diff --check
```

确认：`.env` 未提交；DB 文件未提交；无真实儿童数据；无 provider secret；无无追溯的 Spoken 大段复制。

不做 commit / push / remote 修改 / 微信扫码 / 真机 / 人工 UI 验收。

---

## Completion Report

最终报告：

```text
1. dependencies
2. DATABASE_URL / async session 方案
3. Alembic revision + student_profiles schema
4. Repository / Service 边界
5. X-Client-Id 生成与统一 header 注入
6. Profile API contract
7. Tutor / Voice 如何使用 stored Profile
8. MiniProgram Profile UI/service
9. pytest / npm test / migration / git diff --check 结果
10. 实际阅读的 Spoken reference 文件
11. 是否复制第三方代码；若有，列 provenance/NOTICE
12. 为本 Task 必须做的相邻修改及原因
```
