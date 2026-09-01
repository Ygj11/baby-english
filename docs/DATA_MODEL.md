# DATA_MODEL.md

第一阶段不提前创建大量表。

## 长期核心实体

```text
User
StudentProfile
Conversation
LearningSession
Word
Textbook
TextbookUnit
StudentTextbook
PronunciationAttempt
ScenarioSession
Order
Membership
WeChatIdentity
```

## StudentProfile

Task 016 当前 schema：

```text
id
client_id (unique/indexed anonymous namespace)
age (6–12)
grade
english_level
created_at
updated_at
```

API 不暴露 `id` 或 `client_id`。当前不收集姓名、生日、学校、班级、性别、手机号、头像、家长信息、学习偏好或教材。

未来登录后的 `User` / `WeChatIdentity` 与 `StudentProfile` 保持分离；Task 016 不提前增加 `user_id`。

English level：

```text
starter
beginner
elementary
```

## PronunciationAttempt

Task 017 当前表 `pronunciation_attempts`：

```text
id
client_id (indexed anonymous namespace)
reference_text
category (read_word | read_sentence)
overall_score
accuracy_score
fluency_score
completeness_score (nullable)
standard_score (nullable)
rejected
detail_json (normalized word/error detail only)
created_at
```

分数约束在 0–100。该表不保存儿童音频、讯飞原始 XML、鉴权或 session payload；
`rejected` 使后续聚合可以排除不可信评测。当前只实现 save，不提前增加历史/趋势 API。

## ScenarioSession / ScenarioTurn / SceneGoalProgress

Task 018 当前 schema：

```text
scenario_sessions
  id, client_id, scene_id, status
  completed_goal_ids_json, summary, tip
  created_at, completed_at

scenario_turns
  id, session_id, idx, role, content, created_at

scene_goal_progress
  id, client_id, scene_id, goal_id
  completion_count, first_completed_at, last_completed_at
  UNIQUE(client_id, scene_id, goal_id)
```

`scenario_turns` 只服务 active session 的 Conversation Memory；完成 assessment 后删除。
Durable Learning Progress 只保存 catalogue goal ID、完成次数和时间。`missing_goal_ids`
由 catalogue goals 减去已完成 rows 得出，不落库。不保存 child audio、system prompt 或
provider raw response。

## PhotoLearningRecord

Task 019 当前表 `photo_learning_records`：

```text
id
client_id (indexed anonymous namespace)
primary_word_en
primary_meaning_zh
simple_sentence_en
simple_sentence_zh
practice_phrase
related_words_json (safe normalized educational list only)
question_en
created_at
```

只保存 `status=ok` 的规范化教学事实。表中没有图片/缩略图、文件路径、Base64、EXIF、
OCR、provider request/response 或身份数据。当前 repository 只实现 `save` 与 owner-scoped
`get_owned`，不提前增加历史、列表或搜索 API。

## Conversation

```text
id
user_id
mode
started_at
ended_at
```

Mode：

```text
chat
scenario
story
textbook
photo
```

## LearningSession

```text
id
user_id
conversation_id
mode
duration_seconds
new_words_count
pronunciation_attempts
created_at
```

## Textbook

```text
id
slug (unique)
publisher
series
grade
semester
title
version
source_sha256
embedding_model
embedding_dimensions
index_schema_version
indexed_at
created_at
updated_at
```

不保存正文、chunk、embedding、source path 或 index path。

## TextbookUnit

```text
id
textbook_id
unit_no
title
created_at
```

`(textbook_id, unit_no)` 唯一。

## StudentTextbook

```text
id
client_id (unique)
textbook_id
current_unit_no (nullable)
updated_at
```

选择以当前匿名 `X-Client-Id` namespace 隔离；非空 Unit 必须属于所选课本。

## RAG Metadata

```json
{
  "textbook_slug": "synthetic-rag-book",
  "grade": 3,
  "semester": 1,
  "unit_no": 4,
  "lesson": "A Let's Talk",
  "page": 42
}
```

## Persistence 规则

允许：

- SQLAlchemy 2.x async session；
- Alembic migration；
- 当前业务表还包括 TASK 018 的三个 scenario 专用表。
- 当前业务表还包括 TASK 019 的 `photo_learning_records`。
- 当前业务表还包括 TASK 020 的 `textbooks`、`textbook_units`、`student_textbooks`；
  LlamaIndex chunks/embeddings 位于受保护的 Git-ignored runtime index，不进入 SQL。

禁止：

- 提前建设全部长期表
- 为支付/订阅消息或未落地功能提前建表
- 无业务使用前做复杂 migration
