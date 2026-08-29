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

```text
id
user_id
nickname
avatar_url
age_band
grade
english_level
preferred_language
current_textbook_id
created_at
updated_at
```

English level：

```text
starter
beginner
elementary
```

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
publisher
series
grade
semester
title
version
cover_url
```

## TextbookUnit

```text
id
textbook_id
unit_no
title
```

## RAG Metadata

```json
{
  "textbook_id": "...",
  "grade": 3,
  "semester": 1,
  "unit": 4,
  "lesson": "A Let's Talk",
  "page": 42
}
```

## Tasks 001–010 规则

允许：

- 内存状态
- fixture
- 简单配置
- 必要的最小持久层

禁止：

- 提前建设全部长期表
- 为支付/教材/订阅消息提前建表
- 无业务使用前做复杂 migration
