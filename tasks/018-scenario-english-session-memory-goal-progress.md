# TASK 018 — Scenario English + Session Memory + Scene Goal Progress

## Goal

Turn the existing Home entry `🎭 场景英语` into a real child-focused role-play learning flow.

This task should introduce two memory capabilities that are now justified by a concrete product feature:

```text
Conversation Memory
= current scenario session history

Learning Progress
= which learning goals this child has completed in each scene
```

Target flow:

```text
Home
→ 场景英语
→ choose child-safe scene
→ deterministic scene opener
→ text or voice role-play
→ optional pronunciation practice on curated goal phrase
→ complete scene
→ structured goal assessment
→ persist scene goal progress
→ short child-friendly summary
```

This task is **Codex-only**. Do not include WeChat DevTools visual acceptance, real-device microphone checks, QR scan, LAN configuration, human listening, commit, push, or remote changes in the DoD.

---

# Current-source audit conclusion

TASK 017 is healthy enough to build on.

The real iFlytek ISE integration has **not** yet been verified against a real English MP3, but this is **not a blocker for TASK 018**:

- TASK 018 core role-play uses the already verified LLM/STT/TTS architecture.
- pronunciation inside a scene reuses the existing `/api/pronunciation/evaluate` contract.
- offline FakePronunciation tests are sufficient for TASK 018 implementation.
- keep the missing real ISE verification as an explicit integration checkpoint; do not pretend it passed and do not make TASK 018 depend on it.

Verified current boundaries worth preserving:

```text
StudentProfile
→ persisted through Repository / SQLAlchemy / Alembic

TutorService
→ domain StudentProfile
→ LLMGateway

PronunciationPracticeService
→ PronunciationGateway
→ normalized result
→ PronunciationAttemptRepository

MiniProgram
→ shared api / recorder / audio-player / pronunciation services
```

Important current-source observations:

1. `/api/tutor/chat` and `/api/voice/turn` are single-turn Tutor flows and should remain backward-compatible.
2. `LLMGateway` currently accepts one user message only. Scenario role-play is the first concrete feature that needs multi-turn model history. Extend this boundary minimally; do not flatten history into a giant prompt string.
3. `pages/chat/index.js` already owns normal chat + voice + pronunciation state. Do **not** keep adding scenario-specific branches until it becomes a god-page. Prefer dedicated scenario catalogue/session pages while reusing existing services.
4. existing `Repeat after me:` / `repeat_text` is useful for free Tutor chat, but forcing that marker onto every role-play reply would damage natural conversation. Scene pronunciation should use curated goal practice phrases instead.
5. existing repositories currently commit their own single-aggregate writes. TASK 018 introduces the first operation that spans a scenario session + goal progress + turn cleanup. Keep that operation atomic locally, but do not introduce a generic UnitOfWork framework.
6. `X-Client-Id` remains an anonymous namespace, not authentication.

---

# Spoken reference audit

## Inspect these local files before implementation

Use the local `references/spoken` source as final reference truth and verify the real call paths:

```text
backend/app/data/scenarios.py
backend/app/schemas/scenario.py
backend/app/api/scenarios.py

backend/app/services/dialogue.py
backend/app/schemas/chat.py
backend/app/api/chat.py

backend/app/models/session.py
backend/app/schemas/session.py
backend/app/services/sessions.py
backend/app/api/sessions.py

backend/app/services/feedback.py
backend/app/schemas/feedback.py
backend/app/api/feedback.py

backend/app/services/turn_correction.py
backend/app/schemas/turn_correction.py
backend/app/api/turn_correction.py

backend/app/models/practice.py
backend/app/services/practice.py

backend/tests/test_scenarios.py
backend/tests/test_chat.py
backend/tests/test_sessions.py
backend/tests/test_feedback.py

frontend/src/data/scenarios.ts
frontend/src/store/session.ts
frontend/src/lib/sessionSave.ts
```

## Directly useful product ideas

Borrow/adapt these ideas:

1. **server-side scenario catalogue is the source of truth**;
2. public scene fields are separated from hidden prompt/persona fields;
3. a scene has a role, opener, learning purpose and difficulty;
4. empty session starts with a **deterministic opener without an LLM call**;
5. fast role-play and slow post-session assessment are separate paths;
6. multi-turn conversation history is explicitly supplied to the LLM;
7. Session / Turn are real persisted learning structures;
8. completed practice becomes material for progress/history later.

## Do not copy blindly

Spoken is adult-oriented. Its catalogue contains job interviews, business negotiation, parties, performance reviews, doctor visits, etc. Those are not the baby-english catalogue.

Do **not** import its adult catalogue.

Spoken has one broad `goal` string. baby-english should extend this into **multiple trackable learning goals**.

Spoken persists complete raw transcripts for finished sessions. For a 6–12-year-old product, TASK 018 should improve the privacy design:

```text
active session:
raw text turns may be persisted to provide Conversation Memory

completed session:
use the transcript for final assessment
→ persist structured result/progress
→ delete raw turns
```

Do not persist audio.

Spoken produces a generic numeric session score and grammar/vocabulary corrections. TASK 018 should **not** add a generic child score or automatic correction system yet. Use explicit goal completion + a short summary/tip.

`turn_correction` is worth learning from, but is out of scope for this task.

Spoken uses sync SQLAlchemy patterns. Keep baby-english async SQLAlchemy/Alembic architecture.

If substantial source code is copied rather than independently adapted, update `THIRD_PARTY_NOTICES.md` with MIT source/license/path/revision information. If only the design is studied, do not claim copied source.

---

# Product model

## 1. SceneDefinition

Create a small server-side curated catalogue, for example:

```text
server/app/scenario/
  domain.py
  catalog.py
  prompt.py
  service.py
  repository.py
  model.py
  assessment.py
```

Exact file split may follow current repository style.

A scene should conceptually contain:

```text
id
title
title_zh
subtitle
icon
difficulty

partner_role
opening_line
persona          # internal, never exposed

goals[]
```

## 2. SceneGoal

Each goal should have at least:

```text
id
title_zh
practice_phrase
hint_zh
success_criteria   # internal, never exposed
```

`success_criteria` is for assessment/prompting, not an exact-string rule.

A goal means:

> what communicative ability this scene hopes the child will practice

It is **not** a whitelist of allowed conversation topics.

If the child briefly goes off-topic, the scene partner may answer simply and gently return to the scene.

---

# Initial child-safe catalogue

Implement only a small curated MVP catalogue: **4 scenes, 3 goals each**.

Exact copy may be refined for natural English, but preserve this product intent.

## restaurant — 餐厅点餐

Partner: friendly waiter.

Goals:

```text
order_food
→ ask for a food item
→ practice: "Can I have a sandwich, please?"

ask_for_drink
→ ask for water/a drink
→ practice: "Can I have some water, please?"

say_thank_you
→ close politely
→ practice: "Thank you!"
```

## school — 学校日常

Partner: friendly classmate/teacher appropriate to the prompt.

Goals:

```text
say_hello
→ greet someone
→ practice: "Hi! How are you?"

ask_for_help
→ ask for simple help
→ practice: "Can you help me, please?"

borrow_an_item
→ politely borrow a school item
→ practice: "Can I borrow a pencil, please?"
```

## shopping — 商店买东西

Use a child-friendly toy/book/shop setting, not adult returns/financial negotiation.

Goals:

```text
ask_price
→ practice: "How much is this?"

choose_item
→ practice: "I'd like the blue one, please."

say_thank_you
→ practice: "Thank you!"
```

## travel — 旅行问路

Partner: friendly information-desk helper/local.

Do not ask for passport, hotel room, address, phone number, or other unnecessary personal data.

Goals:

```text
ask_directions
→ practice: "Excuse me, where is the museum?"

understand_direction
→ practice: "Turn left here?"

say_thank_you
→ practice: "Thank you for your help!"
```

Do not implement custom/user-generated scenes in this task.

---

# Scene prompt composition

Create a scene-specific prompt builder.

Conceptually:

```text
StudentProfile
+
ChildTutorPolicy
+
SceneDefinition
+
Scene Goals
+
session conversation history
↓
scene system prompt
↓
LLMGateway
```

Requirements:

- use age / grade / english_level;
- one or two short spoken sentences per partner turn;
- age-appropriate, child-safe content;
- starter/beginner may receive very brief Chinese support only when genuinely stuck;
- stay in role;
- naturally steer toward uncompleted scene goals;
- goals are navigation, not hard topic restrictions;
- if the child asks an unrelated simple English question, answer briefly then return gently;
- do not ask for unnecessary personal information;
- do not use adult-only situations;
- do not diagnose health, legal, financial or other adult matters;
- do not grade every turn;
- do not require `Repeat after me:` on every role-play reply;
- no internal persona/success criteria in API responses.

Keep existing free-chat Child Tutor behavior unchanged.

---

# Multi-turn LLM boundary

Extend the existing `LLMGateway` minimally to support real model conversation history.

A reasonable shape is:

```text
generate(
    system_prompt=...,
    message=current_user_message,
    history=[user/assistant domain messages]
)
```

or an equivalent small provider-neutral type.

Requirements:

- existing TutorService callers should continue to work without supplying history;
- OpenAI-compatible/Qwen adapters should construct actual model role messages, not a flattened transcript string;
- only `user` and `assistant` history roles are accepted from business code;
- internal `system` messages cannot be injected by the client;
- FakeLLM/tests remain deterministic;
- no new agent/workflow framework.

This is a justified extension of `LLMGateway`, not a second scenario-specific LLM provider stack.

---

# Persistence

Add a new Alembic revision after TASK 017.

Do not edit previous revisions.

## 1. `scenario_sessions`

Suggested normalized fields:

```text
id
client_id
scene_id
status               active | completed
completed_goal_ids_json
summary
tip
created_at
completed_at
```

Requirements:

- `client_id` indexed;
- `scene_id` indexed;
- status constrained;
- completed goal IDs stored only as a small normalized JSON array/string for idempotent completed-session reads;
- no provider raw response.

## 2. `scenario_turns`

```text
id
session_id
idx
role                  user | assistant
content
created_at
```

Requirements:

- FK/reference to scenario session;
- deterministic ordering by `idx`;
- application limits on turn count/content size;
- only needed while session is active;
- no audio/media path;
- no internal system prompt.

## 3. `scene_goal_progress`

Use one row per completed scene goal, rather than storing duplicated `missing_goals`.

Suggested:

```text
id
client_id
scene_id
goal_id
completion_count
first_completed_at
last_completed_at
```

Unique:

```text
(client_id, scene_id, goal_id)
```

Meaning:

- absence = not completed yet;
- first successful session inserts the row;
- later successful sessions may increment `completion_count` and update `last_completed_at`.

API derives:

```text
completed_goal_ids
missing_goal_ids
```

from:

```text
catalogue goals - persisted completed goals
```

Do not create a generic Memory table/framework.

---

# Transaction / privacy rule

TASK 018 is the first place where several related DB changes belong to one business operation.

Do **not** introduce a generic UnitOfWork framework.

Instead make scene completion atomic inside the scene persistence/application boundary:

```text
final assessment succeeds
→ mark session completed
→ save completed_goal_ids_json / summary / tip
→ upsert scene_goal_progress
→ delete raw scenario_turns
→ commit once
```

If any part fails:

```text
session/progress must not be half-completed
```

A completed session should not retain the child's raw transcript.

This is intentionally more privacy-preserving than Spoken.

On completion keep:

```text
scene_id
structured goal result
summary/tip
timestamps
progress counts
```

Delete:

```text
raw user/assistant turns
```

No child audio is persisted.

An active unfinished session may temporarily retain text turns only for conversation continuity.

When starting a fresh session for the same client + scene, clean up any stale prior `active` session/turns rather than accumulating abandoned raw transcripts.

---

# SceneGoal assessment — slow path

Do not determine goal completion on every conversational turn.

Follow Spoken's useful fast-path / slow-path separation:

```text
role-play turns
→ fast natural conversation

child taps 完成练习
→ one structured assessment
```

Add a small scene assessment boundary, e.g.:

```text
SceneGoalAssessor
  ├── FakeSceneGoalAssessor
  └── LLMSceneGoalAssessor
```

The real assessor may reuse the existing `LLMGateway`; do not create a second vendor client.

Input:

```text
SceneDefinition
goals + internal success criteria
full active-session transcript
```

Output:

```text
completed_goal_ids
summary
tip
```

No numeric overall score in TASK 018.

Assessment rules:

- count evidence only from learner/user turns;
- communicative success matters more than perfect grammar;
- do not require exact practice-phrase match;
- completed IDs must be a subset of the current scene's defined goal IDs;
- malformed JSON / unknown structure → controlled assessment failure;
- on assessment failure do not complete the session and do not update progress;
- Fake assessor must support fully offline default tests.

Do not use pronunciation score as a requirement for scene goal completion.

---

# Idempotent scene completion

`complete` must be safe to retry.

If a session is already completed:

- do not call the LLM assessor again;
- do not increment progress again;
- return the persisted completion result + current progress.

This prevents duplicate completion counts when the network retries.

---

# API

Use the existing `/api/scenarios/*` namespace.

All current scene endpoints require valid `X-Client-Id` and an existing Student Profile.

## GET `/api/scenarios`

Return the child-safe catalogue plus current child's compact progress.

Public scene data should include:

```text
id
title
title_zh
subtitle
icon
difficulty
partner_role
opening_line
goals[]
progress
```

Never expose:

```text
persona
success_criteria
system prompt
```

Example progress:

```json
{
  "completed_goal_ids": ["say_thank_you"],
  "missing_goal_ids": ["order_food", "ask_for_drink"],
  "completed_count": 1,
  "total_count": 3
}
```

## GET `/api/scenarios/{scene_id}`

Return one public scene + progress.

Unknown scene → 404.

## POST `/api/scenarios/{scene_id}/sessions`

Start a new session.

Requirements:

- validate scene;
- remove/abandon stale active session data for this client + scene;
- create active session;
- persist the deterministic assistant opening line as turn `idx=0`;
- **do not call LLM** for the opener.

Response contains at least:

```text
session_id
scene
opening_message
progress
```

## POST `/api/scenarios/sessions/{session_id}/turn`

Text turn request:

```json
{"message":"Can I have a sandwich, please?"}
```

Backend:

```text
validate ownership + active state
→ load persisted ordered history
→ scene prompt + StudentProfile
→ LLM conversation call
→ persist user + assistant pair
→ return reply
```

If LLM fails, do not leave a half-written user turn.

Bound history/turn count. A sensible MVP maximum is ~40 total persisted turns per session; reject/ask the user to complete/restart rather than create unbounded prompt growth.

## POST `/api/scenarios/sessions/{session_id}/voice-turn`

Multipart:

```text
file=<existing MiniProgram audio>
```

Backend:

```text
validate ownership/profile/session
→ temporary_audio
→ STT
→ scene role-play with stored conversation history
→ TTS
→ temporary project media URL
→ persist successful user transcript + assistant reply pair
```

Reuse existing:

```text
STTGateway
TTSGateway
TemporaryMediaStore
temporary_audio
```

Do not create new provider adapters.

Do not persist child audio.

On provider failure, preserve the same safe-error/logging rules as normal Voice.

Do not expose provider URL.

## POST `/api/scenarios/sessions/{session_id}/complete`

Requirements:

- must contain at least one learner turn;
- run the slow SceneGoalAssessor once;
- atomically persist completion + progress + raw-turn cleanup;
- completed retry is idempotent.

Suggested response:

```json
{
  "session_id": 12,
  "scene_id": "restaurant",
  "completed_goal_ids": ["order_food", "say_thank_you"],
  "summary": "很棒！你已经会点餐和礼貌地说谢谢了。",
  "tip": "下次练习怎么主动要饮料吧。",
  "progress": {
    "completed_goal_ids": ["order_food", "say_thank_you"],
    "missing_goal_ids": ["ask_for_drink"],
    "completed_count": 2,
    "total_count": 3
  }
}
```

Do not return raw transcript after completion.

---

# MiniProgram

## 1. Home

Make the existing:

```text
🎭 场景英语
```

entry navigable.

Do not change the five main Home entries.

## 2. Scenario catalogue page

Add a page such as:

```text
pages/scenarios/index
```

Use existing TDesign MiniProgram.

Show only the four server-returned scenes.

Each card should show:

```text
icon
Chinese title + short English title if useful
subtitle
difficulty
progress: 已完成 1/3
```

Do not duplicate the entire scene catalogue in MiniProgram JS. Backend is the source of truth.

## 3. Scenario session page

Add a focused page such as:

```text
pages/scenario/index
```

Do not overload the existing normal Chat page.

Show:

```text
scene title
AI partner role
three learning goals
current completed state
conversation
text sender
normal voice recorder
完成练习
```

Use the deterministic opening message returned from the backend.

## 4. Voice

Reuse existing:

```text
recorder service
audio player
shared api upload
```

Scenario voice must call:

```text
/api/scenarios/sessions/{session_id}/voice-turn
```

not the normal `/api/voice/turn`.

Normal free chat remains unchanged.

## 5. Pronunciation inside a scene

Reuse TASK 017 rather than building a second pronunciation implementation.

A scene goal already contains a curated:

```text
practice_phrase
```

The UI may offer:

```text
🎤 跟读这句
```

for that goal.

Flow:

```text
goal.practice_phrase
→ existing Recorder
→ existing pronunciationService.evaluate()
→ existing /api/pronunciation/evaluate
→ show the normalized score/feedback
```

Do not force the scene partner's every reply to contain `Repeat after me:`.

Do not make ISE score determine whether a scene goal is completed.

If useful, extract a very small reusable pronunciation result component from the current Chat UI, but do not build a generic UI framework.

---

# Conversation Memory behavior

This task implements **session-scoped conversation memory for scenario mode only**.

Meaning:

```text
turn 1
AI remembers it on turn 2
...
until scene completion
```

This history is server-owned; the MiniProgram must not be trusted to resubmit or rewrite the whole transcript.

Normal `/api/tutor/chat` remains stateless in TASK 018.

Do not build global/chat long-term conversation memory yet.

---

# Learning Progress behavior

This task implements the first structured Scene Learning Progress.

Example:

```text
restaurant
├── order_food       ✅
├── ask_for_drink    ⬜
└── say_thank_you    ✅
```

Progress must survive a new scenario session because it is stored in SQLAlchemy.

`missing_goal_ids` is derived; do not persist it.

A completed goal does not prevent practicing it again.

Goals guide the partner; they are not a hard conversation allow-list.

---

# Child safety / product adaptation

The scenario catalogue and prompts are for ages 6–12.

Do not copy adult Spoken scenes such as:

```text
job interview
business negotiation
performance review
networking
adult party
customer complaint
adult medical consultation
```

The AI partner must not seek:

```text
full real name
school name
home address
phone
passport
payment/account information
other unnecessary identifying information
```

If the learner volunteers personal details, do not encourage further disclosure.

Keep role-play fictional and learning-oriented.

---

# Tests

## Backend offline tests

Cover at least:

### Catalogue

- exactly the intended child-safe MVP scenes;
- IDs/goals unique;
- public response hides persona and success criteria;
- unknown scene 404;
- profile required.

### Prompt

- age/grade/level included;
- role/persona/goals included internally;
- short child-safe constraints included;
- goals described as guidance;
- no free-chat `Repeat after me:` requirement;
- internal prompt never appears in public schema.

### LLM history

- adapter receives system + ordered user/assistant history + current message;
- existing normal Tutor calls remain backward-compatible;
- client cannot inject a `system` role.

### Session

- start returns deterministic opener with zero LLM calls;
- stale active session raw turns are cleaned when a new same-scene session starts;
- client A cannot access client B session;
- user+assistant pair persisted only after a successful text turn;
- LLM failure leaves no partial user turn;
- turn/history limit enforced.

### Voice scene turn

- STT → scene LLM → TTS;
- persisted pair contains transcript + assistant reply only after success;
- temporary upload cleaned;
- media URL is project-owned;
- provider errors remain safe;
- no child audio persistence.

### Assessment/progress

- FakeSceneGoalAssessor offline;
- valid completed IDs normalized/deduped;
- unknown goal IDs rejected/ignored according to one explicit safe rule;
- malformed assessment does not complete session;
- only current catalogue goals can be persisted;
- completion updates session + progress atomically;
- raw turns are deleted after successful completion;
- `missing_goal_ids` is derived correctly;
- second completion request is idempotent and does not increment progress;
- later separate successful session can increment `completion_count`.

### Persistence/migration

- new revision upgrade → downgrade → upgrade;
- constraints/unique goal progress;
- no raw transcript remains for completed session;
- no raw child audio/provider prompt/provider response persisted.

Default tests must remain offline.

## MiniProgram tests

Keep the current lightweight Node test approach.

Cover important service/state behavior:

- Home `scenario` entry navigates correctly;
- catalogue fetch uses backend, not local duplicated scene definitions;
- start session renders opener;
- text turn uses scenario session endpoint;
- voice recording uses scenario voice endpoint;
- goal pronunciation uses existing pronunciation API with `practice_phrase`;
- complete renders summary and updated progress;
- normal Chat still calls existing `/api/tutor/chat` and `/api/voice/turn`.

Do not introduce a heavy UI testing framework.

---

# Optional real-provider check

TASK 018 does **not** require a real ISE MP3 test.

If the configured real Qwen LLM credentials are available, Codex may run one opt-in scenario role-play / scene-assessment integration check to confirm that the real model produces usable scene dialogue and parseable structured assessment.

If not run, report it as not run. Do not block TASK 018.

Do not create a flaky real-provider test as part of the default suite.

---

# Docs

Update only documents affected by actual implementation, likely:

```text
README.md
docs/PRODUCT.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/DATA_MODEL.md
docs/PRIVACY_SECURITY.md
docs/ROADMAP.md
docs/TEST_PLAN.md
```

Document clearly:

```text
Student Profile
= who the child is for teaching adaptation

Scenario Conversation Memory
= temporary active-session transcript

Scene Goal Progress
= durable structured learning memory

completed raw scene transcript
= deleted after assessment
```

Do not document future generic Long-term Memory/SRS tables as implemented.

---

# Out of scope

Do not implement:

- custom/user-generated scenes;
- adult Spoken catalogue;
- instant per-turn grammar correction;
- generic numeric scene score;
- growth charts;
- global session history UI;
- long-term-memory inference;
- SRS/wordbook;
- Story;
- Vision/photo;
- Textbook/RAG;
- WeChat login/auth;
- PostgreSQL deployment;
- realtime Pipecat transport;
- a new pronunciation provider;
- pronunciation evaluation on every role-play turn;
- generic Repository framework;
- generic UnitOfWork framework;
- workflow/agent engine;
- manual WeChat/real-device acceptance;
- commit/push/remote changes.

---

# Definition of Done

TASK 018 is complete when:

1. server-owned child-safe scenario catalogue exists with 4 scenes × 3 goals;
2. public scenario API hides internal persona/success criteria;
3. StudentProfile + ChildTutorPolicy + Scene + Goals compose the scene prompt;
4. `LLMGateway` supports ordered multi-turn history without breaking current Tutor/Voice behavior;
5. deterministic scene opener requires no LLM call;
6. scenario text conversation remembers prior turns server-side;
7. scenario voice reuses existing STT/TTS/audio/media infrastructure;
8. scene goal pronunciation reuses TASK 017 and curated `practice_phrase`;
9. new Alembic migration creates `scenario_sessions`, `scenario_turns`, `scene_goal_progress`;
10. final scene assessment returns structured completed goals + child-friendly summary/tip;
11. `completed_goal_ids` are persisted; `missing_goal_ids` are derived;
12. successful completion atomically saves structured outcome/progress and deletes raw turns;
13. completion retry is idempotent;
14. stale active same-scene transcripts are not accumulated indefinitely;
15. no child audio is persisted;
16. MiniProgram has working scenario catalogue + session pages and Home route;
17. default backend tests pass offline;
18. MiniProgram tests pass;
19. migration/check tests pass;
20. existing Tutor, Voice, Pronunciation, Qwen/Fake tests remain green;
21. `git diff --check` passes;
22. `.env`, local DBs, audio and secrets are not tracked;
23. any copied Spoken source is properly noticed; design-only borrowing does not falsely claim copied code;
24. no commit, push or remote modification is performed.

---

# Final Codex report

Report concisely:

```text
1. files/dependencies changed
2. child-safe scene catalogue and goals
3. scene prompt composition
4. LLM multi-turn boundary change
5. scenario session/turn persistence
6. SceneGoalAssessor behavior
7. scene_goal_progress behavior
8. transcript retention/deletion behavior
9. text + voice role-play API
10. MiniProgram catalogue/session/pronunciation flow
11. offline pytest result
12. MiniProgram test result
13. Alembic/migration result
14. optional real Qwen scenario check result or "not run"
15. TASK 017 real ISE status remains unverified unless independently tested
16. security/privacy checks
17. Spoken files actually inspected
18. whether Spoken code was copied and notice status
19. limitations/blockers
```
