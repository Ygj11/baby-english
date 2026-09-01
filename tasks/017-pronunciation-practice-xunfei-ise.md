# TASK 017 — Pronunciation Practice + Xunfei ISE

## Goal

Turn the existing `🎤 跟读` action into a real pronunciation-practice loop:

```text
Tutor reply
→ stable English repeat target
→ MiniProgram Recorder (16 kHz / mono / MP3)
→ POST /api/pronunciation/evaluate
→ PronunciationGateway
→ Xunfei ISE streaming WebSocket
→ normalized pronunciation result
→ persist pronunciation attempt
→ child-friendly score UI
```

This task is **Codex-only**. Do not include WeChat DevTools visual acceptance, real-device microphone checks, human listening, QR scan, LAN configuration, commit, push, or remote changes in the DoD.

---

## Current-source audit conclusion

TASK 016 is healthy enough to build on. No blocker was found.

Keep these boundaries:

```text
FastAPI route
→ application/service boundary
→ Repository
→ SQLAlchemy AsyncSession
→ Alembic-managed SQLite

TutorService
→ domain StudentProfile
→ LLMGateway
```

Verified strengths in current `baby-english`:

- SQLAlchemy async engine/session is isolated under `server/app/persistence/`.
- Alembic owns schema creation; application startup does not call `create_all()`.
- `StudentProfileRepository` returns the existing domain `StudentProfile`, not ORM records.
- Tutor/PromptBuilder/LLMGateway do not depend on SQLAlchemy.
- Chat and Voice resolve the persisted profile before paid provider calls.
- missing Profile short-circuits Voice before STT/LLM/TTS.
- `X-Client-Id` is treated as a namespace, not authentication.
- backend tests run against an Alembic-managed temporary SQLite database.
- MiniProgram no longer sends hard-coded age/grade/level.

Non-blocking debt discovered:

1. `StudentProfileService` is currently a thin pass-through. Keep it for now; do not invent a generic service/repository framework.
2. `SQLAlchemyStudentProfileRepository.save()` commits its own transaction. This is acceptable for the current single-aggregate flow, but revisit transaction ownership when a future task needs one atomic operation spanning multiple repositories/tables.
3. `miniprogram/services/api.js` maps errors only from HTTP status, so any `404` is currently classified as `PROFILE_NOT_FOUND`. While touching the API client in this task, make Profile-specific error mapping path-aware or otherwise prevent unrelated endpoints from being misclassified as missing Profile. Do not introduce a generic error framework.

---

## Reference guidance

### Local reference: `references/spoken`

Before implementation, inspect the current local files and verify their real definitions/call paths:

```text
backend/app/services/xf_auth.py
backend/app/services/xf_ise.py
backend/app/services/pronunciation.py
backend/app/api/pronunciation.py
backend/app/schemas/pronunciation.py
backend/app/models/practice.py
backend/app/services/practice.py
backend/tests/test_pronunciation.py
backend/tests/test_practice.py
frontend/src/components/PronounceButton.tsx
frontend/src/components/PronunciationFeedback.tsx
frontend/src/lib/recorder.ts
frontend/src/lib/api.ts
```

Use Spoken as a **product + business-code donor**, not as the architecture template.

Useful ideas to borrow:

- HMAC-authenticated iFlytek WebSocket boundary.
- async WebSocket client dependency instead of hand-writing WebSocket.
- reference text + learner audio as separate ISE inputs.
- provider response normalized before reaching UI.
- pronunciation attempts persisted for later progress/history.
- overall + accuracy + fluency + completeness/word-level feedback.
- opt-in provider test with a stubbed offline default.

Do **not** copy these assumptions blindly:

- Spoken records browser PCM; baby-english already records 16 kHz mono MP3.
- Spoken sends `aue=raw`; baby-english should use the official MP3 path (`aue=lame`) for MiniProgram recordings.
- Spoken hardcodes a `0–5 × 20` score conversion. Current iFlytek streaming ISE can return percentage-oriented results when configured accordingly; parser must normalize based on actual response instead of assuming only one scale.
- Spoken exposes phoneme labels directly in the UI. For a 6–12-year-old product, keep raw phoneme detail internal/normalized for future learning memory; do not make ARPAbet-style labels the primary child UI.
- Do not copy Spoken's DB/session architecture; use the existing async SQLAlchemy/Alembic foundation.

Spoken is MIT licensed. If substantial source is copied rather than independently implemented/adapted from the official protocol, update `THIRD_PARTY_NOTICES.md` with source URL, license, source paths, revision if available, copied paths, and modifications.

### Provider source of truth

Implement against the **current iFlytek streaming ISE API contract**, using local Spoken only as implementation guidance.

Important current protocol expectations to verify while implementing:

```text
WSS endpoint:
wss://ise-api.xfyun.cn/v2/open-ise

English:
ent=en_vip

Question types:
read_word
read_sentence

Audio:
16 kHz / mono
MP3 supported with aue=lame

Text:
UTF-8 BOM required
read_word uses [word]
read_sentence uses [content]

Streaming:
ssb → auw frames → final status=2

Do not exceed provider frame-size limits.
```

Prefer the percentage-oriented full result configuration needed for:
- overall
- accuracy
- fluency
- completeness/integrity
- standard
- word-level/error detail

Also parse provider rejection (`is_rejected`) when present; a rejected result must not be presented as a trustworthy pronunciation score.

---

# Scope

## 1. Mature WebSocket dependency

Add a maintained async WebSocket dependency suitable for the iFlytek streaming protocol.

Preferred:

```text
websockets
```

Do not implement WebSocket framing, handshake transport, reconnect machinery, or socket parsing manually.

The existing `websocket-client` dependency may remain for DashScope compatibility; do not remove/change its current pin unless directly required.

---

## 2. Pronunciation domain boundary

Create a thin provider-neutral boundary, for example under:

```text
server/app/pronunciation/
```

Expected concepts:

```text
PronunciationGateway
PronunciationResult
WordPronunciationScore
FakePronunciationGateway
XunfeiISEPronunciationGateway
PronunciationError
PronunciationConfigurationError
```

The exact file split may follow current project style.

The business/API layer must not parse iFlytek XML or construct provider WebSocket frames.

A normalized result should contain at least:

```text
overall_score        0..100
accuracy_score       0..100
fluency_score        0..100
completeness_score   0..100 when provider supplies it
standard_score       0..100 when provider supplies it
rejected             bool
words                normalized word-level results
```

Word detail may retain normalized provider-neutral error/phoneme information for persistence/future memory, but API/UI must not depend on raw iFlytek XML.

Do not return or persist the raw provider XML.

---

## 3. Provider factory / environment

Follow the existing STT/LLM/TTS provider pattern.

Add configuration similar to:

```env
ISE_PROVIDER=fake

XFYUN_APP_ID=
XFYUN_API_KEY=
XFYUN_API_SECRET=

ISE_TIMEOUT=60
```

For real use:

```env
ISE_PROVIDER=xunfei
```

Requirements:

- secrets must be `repr=False` / excluded from logs where relevant;
- fake-provider production protection must reuse the existing `provider_environment` policy;
- missing/invalid config produces `PronunciationConfigurationError`;
- provider request failures become normalized `PronunciationError`;
- never log auth URL query parameters because they contain derived authorization material;
- never log raw child audio;
- never log provider raw XML;
- only sanitized provider code/session id/error category may be logged.

Do not add routing, A/B, fallback, or multiple ISE vendors.

---

## 4. Xunfei ISE adapter

Implement the streaming ISE adapter with the mature WebSocket dependency.

The adapter receives:

```text
reference_text
validated temporary MP3 path
evaluation category
```

MVP only needs English:

```text
read_word
read_sentence
```

Choose category deterministically:

- one simple English lexical target → `read_word`;
- multi-word target / sentence → `read_sentence`.

Validate the reference text before provider invocation.

Build the official test-paper format:

```text
read_word:
[word]
banana

read_sentence:
[content]
Can I have some water, please?
```

Include the required UTF-8 BOM when sending to ISE.

For MiniProgram MP3:

```text
aue=lame
auf=audio/L16;rate=16000
ent=en_vip
sub=ise
```

Use the official full/percentage-oriented result settings needed for multi-dimensional scoring and normalized word/error detail.

Do not copy Spoken's browser-PCM conversion or add FFmpeg/audio conversion for the MiniProgram path.

Streaming requirements:

- send `ssb`;
- send first/middle/final `auw` frames with correct `aus` and `data.status`;
- pace/chunk audio according to the provider contract;
- stay below provider frame-size limits;
- stop on provider error;
- consume until final response status;
- apply timeout;
- close WebSocket cleanly.

---

## 5. Robust ISE result parser

Parse XML in a provider-specific module and map it into the provider-neutral result.

Requirements:

- support the actual percentage-oriented response configured by this task;
- tolerate/normalize legacy-style lower-scale samples when useful for offline tests instead of blindly multiplying every score by 20;
- clamp exposed scores to `0..100`;
- extract overall dimensions when present;
- extract word scores where present;
- extract provider-neutral word/phoneme error information where available;
- ignore filler/silence pseudo-words;
- parse `is_rejected` when present;
- malformed/empty XML → normalized provider error, never an unhandled XML exception.

A provider-rejected reading must return a clear normalized `rejected=true` result (or an equivalent explicit domain outcome), not a normal high-confidence score.

---

## 6. Stable repeat target from Tutor replies

The current `repeat` button has no explicit reference text; it simply starts another normal voice turn. Fix this without adding a second LLM call.

Add a stable Tutor output convention:

- when the Tutor invites repetition, the reply ends with exactly one short marker:
  `Repeat after me: <English target>`
- target should be short (roughly 1–12 English words) and contain no Chinese/emoji;
- update the Child Tutor prompt accordingly;
- extract the target with a small deterministic helper;
- if the reply does not contain a valid target, `repeat_text` is null/absent and the `repeat` action must not be offered.

Do not attempt broad NLP extraction of arbitrary English from the whole reply.

Extend Chat and Voice response contracts with:

```text
repeat_text: string | null
```

Keep the visible tutor reply as normal text; no extra LLM/provider call is needed to determine the target.

Update FakeLLM/offline fixtures so the repeat target remains deterministic.

---

## 7. Pronunciation API

Add:

```text
POST /api/pronunciation/evaluate
```

Request:

```text
X-Client-Id
multipart/form-data:
  file
  reference_text
```

The backend determines `read_word` vs `read_sentence`.

Requirements:

- require a valid `X-Client-Id`;
- require an existing Student Profile before ISE invocation;
- validate reference text length/shape;
- accept the existing MiniProgram MP3 upload path;
- reuse the existing temporary-audio validation/cleanup mechanism where appropriate;
- no STT call;
- no LLM call;
- no TTS call;
- provider configuration/request failure → 503 with safe client-facing detail;
- invalid reference/audio → 400/413 as appropriate;
- temporary upload always deleted;
- response contains only normalized result + child-facing feedback + attempt id if useful;
- no provider raw XML, credentials, auth URL, or upstream WebSocket URL.

Suggested response shape:

```json
{
  "attempt_id": 123,
  "reference_text": "banana",
  "overall_score": 86,
  "accuracy_score": 82,
  "fluency_score": 91,
  "completeness_score": 100,
  "standard_score": 84,
  "rejected": false,
  "words": [
    {
      "word": "banana",
      "score": 82
    }
  ],
  "feedback": "不错！再慢一点读一次，会更清楚。"
}
```

Exact optional score fields may be nullable if the provider does not supply them.

---

## 8. Child-friendly feedback

Do not add another LLM call in this task.

Generate concise deterministic feedback from the normalized result.

Examples of behavior, not required literal copy:

```text
high score
→ 很棒！读得很清楚，再读一次巩固一下。

medium
→ 不错！慢一点，再试一次会更清楚。

low
→ 我们再来一次，先慢慢读，不着急。

rejected
→ 这次好像没有读到目标词/句，我们重新读一次吧。
```

Keep feedback short and encouraging.

Do not diagnose speech disorders.
Do not display technical provider terms.
Do not expose raw phoneme codes as the main child feedback.

---

## 9. Persistence: `pronunciation_attempts`

Add a new Alembic revision; do not edit the existing TASK 016 revision.

Add a small normalized table such as:

```text
pronunciation_attempts
----------------------
id
client_id
reference_text
category
overall_score
accuracy_score
fluency_score
completeness_score
standard_score
rejected
detail_json
created_at
```

Requirements:

- `client_id` non-null and indexed;
- scores constrained/validated to 0..100 where practical;
- `category` limited to current supported values;
- `detail_json` stores only normalized word/error detail useful for future learning memory;
- do not persist raw XML;
- do not persist child audio;
- do not persist provider auth/session payloads;
- keep schema SQLite/PostgreSQL friendly.

Create a thin `PronunciationAttemptRepository` following the existing persistence style.

For this task it only needs the operations actually used by pronunciation evaluation (primarily save). Do not create generic CRUD/base repositories.

Persist successful provider outcomes, including explicit rejected attempts if useful, but future score aggregation must be able to exclude rejected attempts.

Do not build growth curves/history endpoints yet; that belongs to the later Learning Progress work.

---

## 10. MiniProgram: real `🎤 跟读`

Reuse the existing Recorder service. Do not create a second recorder implementation.

Current recorder already requests:

```text
sampleRate: 16000
numberOfChannels: 1
format: mp3
```

Change Chat page behavior so recording has an explicit purpose:

```text
normal voice turn
pronunciation repeat
```

When the user taps `🎤 跟读`:

1. require a valid `repeat_text`;
2. show the target clearly;
3. start the existing recorder in pronunciation mode;
4. on stop, upload to `/api/pronunciation/evaluate`;
5. display score/result;
6. do **not** send this audio through `/api/voice/turn`;
7. offer a simple “再读一次” action using the same target.

Normal microphone behavior must remain unchanged:

```text
normal microphone
→ /api/voice/turn
```

Pronunciation result UI should prioritize:

```text
目标词/句
总分
准确
流利
完整
短反馈
逐词分数（when available）
```

Do not make raw phoneme labels the primary UI.

Do not add a separate full pronunciation page unless the existing Chat UX genuinely requires it; a focused result block/card in the current flow is preferred for MVP.

---

## 11. MiniProgram API error hardening

While adding the pronunciation API client, fix the current over-broad status mapping:

```text
404 != always PROFILE_NOT_FOUND
```

Profile-specific error codes must only be produced for the Profile contract (or from an explicit backend business code if implemented).

Do not build a generalized error framework.

---

## 12. Tests

### Offline backend tests

Add deterministic tests covering at least:

- auth-signing URL construction without exposing secret material;
- English `read_word` paper formatting;
- English `read_sentence` paper formatting;
- MP3 selects `aue=lame`;
- frame sequence first/middle/final;
- parser: normal percentage-style result;
- parser: malformed result;
- parser: rejected result;
- parser: word/error normalization;
- FakePronunciation provider remains offline;
- production fake-provider fail-safe;
- API success;
- API missing Profile short-circuits before ISE;
- invalid reference text does not call ISE;
- invalid/empty/oversize audio follows existing validation semantics;
- provider error → safe 503;
- temporary audio cleanup;
- successful/rejected attempt persistence;
- ownership isolation by `client_id`;
- migration `upgrade → downgrade → upgrade`;
- no raw XML/audio stored.

Do not hit iFlytek in the default test suite.

### MiniProgram tests

Cover the important behavior:

- Chat/Voice response accepts `repeat_text`;
- no `repeat_text` → repeat action hidden/not offered;
- repeat action starts pronunciation mode;
- pronunciation stop uploads to `/api/pronunciation/evaluate`;
- normal recording still calls `/api/voice/turn`;
- result rendering/state contains score + feedback;
- unrelated 404 is not classified as `PROFILE_NOT_FOUND`.

Do not introduce a heavy UI-test framework.

### Real provider integration test

Add opt-in marker-based real ISE test.

Suggested invocation:

```bash
RUN_REAL_PROVIDER_TESTS=1 \
REAL_ISE_AUDIO_PATH=/absolute/path/to/english-reading.mp3 \
REAL_ISE_REFERENCE_TEXT="banana" \
uv run --env-file .env pytest -m real_provider -k xunfei_ise -vv -s
```

If credentials or the real audio fixture are not available, skip clearly; never fake a real-provider pass.

Real test should verify:

- provider connection succeeds;
- normalized result returned;
- scores are within 0..100 when present;
- no raw XML/auth URL/secret printed;
- local audio file is not modified/deleted.

---

## 13. Docs / config

Update only documents affected by real implementation:

```text
.env.example
README.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/DATA_MODEL.md
docs/PRIVACY_SECURITY.md
docs/SETUP.md
docs/TEST_PLAN.md
```

Keep docs factual; do not document future Scene/SRS/long-term-memory schemas as if already implemented.

Document explicitly:

- ISE credentials stay backend-only;
- child audio is temporary and deleted after evaluation;
- normalized pronunciation scores are persisted;
- raw provider XML is not persisted;
- `X-Client-Id` is still only an anonymous namespace, not authentication.

---

# Out of scope

Do not implement:

- realtime Pipecat voice transport;
- pronunciation evaluation during every normal voice turn;
- Chinese pronunciation scoring;
- open-ended speaking evaluation;
- scenario goals/progress;
- Session/Turn/Score model;
- growth charts;
- SRS/vocabulary;
- long-term-memory inference;
- PostgreSQL deployment;
- WeChat login/auth;
- audio retention;
- generic memory framework;
- generic repository framework;
- LLM-generated pronunciation feedback;
- provider routing/A-B/fallback;
- manual WeChat/real-device acceptance;
- commit/push/remote changes.

---

# Definition of Done

TASK 017 is complete when:

1. `PronunciationGateway` and Fake/Xunfei implementations exist.
2. iFlytek streaming ISE uses a mature WebSocket dependency.
3. MiniProgram MP3 goes through the official `aue=lame` path; no custom transcoder is added.
4. provider response is normalized; raw XML does not leak outside provider parsing.
5. Tutor Chat/Voice expose a deterministic `repeat_text`, and repeat is offered only when valid.
6. `🎤 跟读` uses `/api/pronunciation/evaluate`, not `/api/voice/turn`.
7. normalized pronunciation attempts are persisted through SQLAlchemy + new Alembic revision.
8. raw child audio and raw provider XML are not persisted.
9. child UI shows understandable scoring/feedback and does not center raw phoneme codes.
10. default backend tests are fully offline and pass.
11. MiniProgram tests pass.
12. Alembic migration test/check passes.
13. opt-in real ISE test exists; run it if credentials + audio fixture are available and report exact result.
14. existing Qwen STT/LLM/TTS and normal batch voice tests remain green.
15. `git diff --check` passes.
16. secrets/DB/audio artifacts are not accidentally tracked.
17. no commit, push, or remote change is performed.

---

# Final Codex report

Report concisely:

```text
1. files/dependencies changed
2. PronunciationGateway structure
3. Xunfei ISE protocol/config used
4. normalized score model/parser behavior
5. repeat_text contract
6. pronunciation_attempts migration/schema
7. MiniProgram repeat flow
8. offline pytest result
9. MiniProgram test result
10. migration/alembic checks
11. real ISE test result or exact reason skipped
12. security/privacy checks
13. Spoken files actually inspected
14. whether any Spoken code was copied; if yes, THIRD_PARTY_NOTICES update
15. limitations/blockers
```
