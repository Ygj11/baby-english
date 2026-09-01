# TASK 019 — Photo English + Qwen Vision + Safe Learning Record

## Goal

Turn the existing Home entry `📷 拍一拍` into a real child-focused “see something → learn English from it” flow.

Target product loop:

```text
Home
→ 拍一拍
→ camera / album
→ local preview
→ POST /api/photo/analyze
→ Image validation + metadata stripping
→ VisionGateway
→ Qwen Vision
→ strict structured learning result
→ persist safe learning record (no image)
→ child-friendly learning card

Actions:
🔊 听一听
🎤 跟我读
💬 和我练
```

This task is **Codex-only**.

Do not include WeChat DevTools visual acceptance, real-device camera checks, QR scan, LAN configuration, human review, commit, push, or remote changes in the DoD.

---

# Current-source audit conclusion

TASK 018 is healthy enough to build on. No blocking defect was found.

Verified strengths in the current `baby-english` source:

```text
StudentProfile
→ Repository / SQLAlchemy / Alembic

TutorService
→ StudentProfile
→ ChildTutorPolicy
→ LLMGateway

PronunciationPracticeService
→ PronunciationGateway
→ normalized persisted attempt

Scenario
→ server-owned catalogue
→ persisted active-session turns
→ ordered LLM history
→ structured goal progress
→ raw-turn deletion after completion
```

The Scenario API also keeps internal persona / success criteria out of public responses, and the MiniProgram reuses Recorder / audio-player / pronunciation services rather than cloning new implementations.

## Non-blocking technical debt discovered

Do not create a TASK 018.1 for these. Record them and avoid spreading the patterns where inappropriate.

### 1. Scenario read transaction lives across provider latency

Current scenario turn flow loads session/history through the request-scoped `AsyncSession`, then awaits the LLM, then writes/commits.

With SQLAlchemy autobegin this can keep a DB transaction/session state alive across a slow network provider call.

This is tolerable for the current local SQLite MVP, but **TASK 019 must not intentionally hold an image DB write transaction open while waiting for Qwen Vision**.

Preferred pattern for TASK 019:

```text
load required owner/profile facts
→ provider call outside any explicit write transaction
→ validate normalized provider result
→ short DB write/commit
```

Do not introduce a generic UnitOfWork framework.

### 2. Scenario structured assessment is prompt-JSON only

`LLMSceneGoalAssessor` currently asks the generic `LLMGateway` for JSON and parses it with `json.loads`, but it does not use Qwen's native structured-output facility.

Offline behavior is well tested, but real Qwen structured assessment is still not verified.

This does **not** block TASK 019.

For Photo Vision, however, Qwen structured output is directly useful and should be used through the existing mature OpenAI-compatible client rather than repeating prompt-only JSON parsing.

### 3. ScenarioService exposes the concrete repository

`ScenarioService` currently types the repository as `SQLAlchemyScenarioRepository`, and parts of the API access `service.repository` directly.

This is acceptable for the current feature and not worth refactoring now.

Do not copy this into Photo code. Keep the Photo application API small and explicit.

### 4. Scenario voice can leave a short-lived media asset if DB append fails after TTS

The media asset is temporary/TTL-backed, so this is not a blocker or persistent privacy leak.

Do not create the same ordering issue in Photo listen flow: TTS listen should not require a new DB write.

---

# Reference guidance

## 1. Current baby-english is the primary architecture reference

Before implementation inspect the actual current files and reuse their established patterns:

```text
server/app/tutor/llm.py
server/app/tutor/child_policy.py
server/app/tutor/schemas.py

server/app/provider_environment.py
server/app/persistence/database.py

server/app/voice/tts.py
server/app/voice/media.py
server/app/voice/audio.py

server/app/pronunciation/
server/app/student_profile/
server/app/scenario/

server/app/api/dependencies.py
server/app/api/voice.py
server/app/api/pronunciation.py
server/app/api/scenarios.py

miniprogram/services/api.js
miniprogram/services/audio-player.js
miniprogram/services/pronunciation.js
miniprogram/pages/chat/
miniprogram/pages/scenario/
miniprogram/pages/home/
```

Reuse boundaries and mature dependencies. Do not create a second API client, audio player, TTS adapter, identity mechanism, or persistence framework.

## 2. WeChat MiniProgram reference

The audit ZIP supplied for TASK 019 contains `references/spoken` but **does not contain `references/miniprogram-demo`**.

If Codex has the owner's existing local:

```text
references/miniprogram-demo
```

inspect only the relevant official-demo areas by searching for:

```text
chooseMedia
chooseImage
camera
uploadFile
image preview
```

Do not assume exact paths from this task file; verify the local reference source.

For API behavior, current WeChat MiniProgram documentation is the source of truth.

Use native MiniProgram media APIs. Do not add a camera/image-picker framework.

## 3. Spoken

Spoken is not a useful primary donor for TASK 019.

Do not spend time deeply auditing its scenario/session/pronunciation code again.

Only consult it if a directly relevant reusable product pattern is discovered.

## 4. Qwen provider source of truth

Use the current Alibaba Cloud Model Studio documentation as provider truth.

Current product facts to verify during implementation:

```text
qwen3.7-flash
- supports Image + Text input
- text output
- Beijing workspace supported
- OpenAI-compatible multimodal chat supported
- Base64 data-URI image input supported
- structured output supported
```

Use the owner's existing Alibaba credentials:

```text
DASHSCOPE_API_KEY
DASHSCOPE_WORKSPACE_ID
DASHSCOPE_REGION
```

Do not create a second Alibaba account/key scheme.

---

# Architecture

Introduce a thin provider-neutral vision boundary.

Conceptually:

```text
MiniProgram
→ /api/photo/analyze
→ TemporaryImage
→ PhotoLearningService
→ VisionGateway
   ├── FakeVision
   └── QwenVision
→ PhotoLearningResult
→ PhotoLearningRepository
→ SQLAlchemy / Alembic
```

The Vision provider must not leak OpenAI/DashScope response objects into API/business code.

A reasonable package:

```text
server/app/photo/
  domain.py
  image.py
  gateway.py
  qwen.py
  service.py
  model.py
  repository.py
  schemas.py
  prompt.py
```

Exact split may follow current code style.

Do not build:

```text
GenericMultimodalFramework
Agent
Workflow engine
Provider router
A/B system
Vision fallback chain
```

---

# Dependency strategy

## Use mature dependencies

Add:

```text
Pillow
```

for:

- image decoding / verification;
- safe dimension checks;
- EXIF orientation handling;
- metadata stripping by re-encoding;
- resize/normalization.

Do not hand-write JPEG/PNG parsers.

Reuse the already installed:

```text
openai
```

for Qwen OpenAI-compatible multimodal requests.

Do not add a second Qwen SDK unless the existing OpenAI-compatible client is proven insufficient.

No image-storage/cloud-storage dependency is needed in TASK 019.

---

# Provider configuration

Add config similar to:

```env
VISION_PROVIDER=fake
VISION_MODEL=qwen3.7-flash
VISION_TIMEOUT=60
```

Real local configuration:

```env
VISION_PROVIDER=qwen
VISION_MODEL=qwen3.7-flash
```

Reuse:

```env
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing
```

Requirements:

- default tests remain Fake/offline;
- production fake-provider protection must reuse the existing provider-environment policy;
- missing config → normalized `VisionConfigurationError`;
- provider failure → normalized `VisionError`;
- do not log API keys;
- do not log image Base64/data URI;
- do not log raw child images;
- do not log full provider response.

If useful, extract a tiny shared Qwen OpenAI-compatible base-URL/client helper from the existing Qwen LLM code.

Do **not** create a generic provider framework just to share a few lines.

---

# Image input pipeline

Create a dedicated image validation/normalization boundary.

Example concept:

```text
temporary_image(upload)
→ TemporaryImage
```

The caller must never manually manage temporary-file cleanup.

## Supported MVP formats

Accept only ordinary still images:

```text
JPEG / JPG
PNG
WebP
```

Reject:

```text
GIF / animated images
video
PDF
HEIC unless the installed mature decoder genuinely supports it
arbitrary binary
```

Do not add HEIC conversion infrastructure in this task.

## Limits

Choose conservative documented constants, roughly:

```text
upload bytes: <= 8 MB
one image only
dimension/pixel bomb protection
normalized long edge: about 1600 px
```

The exact long-edge constant can be adjusted based on current Qwen image-token guidance, but keep it bounded.

## Required normalization

Use Pillow to:

1. stream upload to a temporary file with a byte limit;
2. verify it is a real supported image;
3. reject truncated/corrupt content;
4. reject decompression-bomb scale inputs;
5. apply EXIF orientation;
6. convert to RGB where needed;
7. resize if larger than the chosen bound;
8. re-encode as JPEG;
9. strip EXIF and other metadata;
10. provide the normalized temp path/content type;
11. always delete both original and normalized temporary files.

This is important for child privacy because location/camera metadata must not be sent upstream unnecessarily.

Do not persist the normalized file.

Do not upload it to OSS/object storage.

---

# VisionGateway domain

Create provider-neutral concepts similar to:

```text
VisionGateway
FakeVision
QwenVision
VisionError
VisionConfigurationError
PhotoLearningResult
RelatedWord
```

The normalized result should be deliberately small and educational.

Suggested domain:

```text
status:
  ok
  unclear
  unsuitable

primary_word_en
primary_meaning_zh

simple_sentence_en
simple_sentence_zh

practice_phrase

related_words[]
  word_en
  meaning_zh

question_en
encouragement_zh
```

Rules:

- `ok` → required lesson fields present;
- `unclear` → image is too unclear/ambiguous for a confident simple lesson;
- `unsuitable` → privacy/safety/person-heavy/private-document content should not become a normal learning record;
- no arbitrary OCR transcript;
- no full free-form scene description;
- related words max ~4;
- keep strings short;
- practice phrase roughly 1–8 English words;
- one primary learning target, not a vocabulary dump.

Do not expose a fake numeric “vision confidence” unless the provider has a meaningful calibrated value.

---

# Qwen Vision adapter

Reuse the owner's existing Beijing OpenAI-compatible endpoint.

Input should be:

```text
system/text teaching instruction
+
normalized image as Base64 data URI
```

Do not expose the local image through a public HTTP URL.

Do not add OSS just to give Qwen a URL.

## Structured output

Use Qwen's current structured-output capability.

Preferred approach:

```text
OpenAI SDK
+ Pydantic model / JSON Schema
+ strict structured output
```

Use the currently installed OpenAI SDK API that is actually supported after local verification.

Do not rely only on:

```text
"please output JSON"
→ json.loads()
```

when the configured `qwen3.7-flash` supports structured schema output.

Still validate the parsed provider result in the domain layer.

Provider schema must disallow unknown fields where practical.

## Prompt/product policy

Compose the Vision teaching prompt from:

```text
StudentProfile
+
ChildTutorPolicy
+
Photo learning policy
```

The prompt must instruct the model:

- choose one visible, concrete, age-appropriate English learning target;
- prefer everyday objects/actions/animals/food/school items;
- use the child's level;
- do not hallucinate details not visible;
- if uncertain, return `unclear`;
- do not identify real people;
- do not guess a person's name;
- do not infer race, religion, health, disability, politics, sexual orientation, financial status or other sensitive traits;
- do not transcribe/persist phone numbers, addresses, account numbers, IDs, school names, personal names or other unnecessary personal information;
- if the image is mainly a private document, ID card, account screen, address label or similarly sensitive material → `unsuitable`;
- if the image is mainly a face/person, teach only a generic safe concept if genuinely useful (for example a visible non-sensitive object/action), otherwise `unsuitable`;
- do not teach adult-only/unsafe content;
- no medical/legal/financial advice;
- child-facing explanations stay short.

Do not expose this system policy in the public API.

---

# Output validation / sensitive-result guard

Treat model output as untrusted.

Before persistence/API response:

- enforce max lengths;
- enforce related-word count;
- validate English target/practice phrase shape;
- reject blank/duplicate vocabulary;
- reject URLs/emails;
- reject obvious phone/account/long-digit patterns;
- reject provider output that violates the expected `status`/field consistency;
- if sensitive-looking output is detected, convert to a safe `unsuitable` result rather than persist it.

Do not attempt to build a universal PII detection engine.

This is a narrow last-line guard for obvious data that should never be stored in a child's photo-learning record.

---

# Persistence — `photo_learning_records`

TASK 019 should start collecting **safe structured learning memory**, but not image history.

Add a new Alembic revision after TASK 018.

Do not edit previous revisions.

Suggested table:

```text
photo_learning_records
----------------------
id
client_id

primary_word_en
primary_meaning_zh

simple_sentence_en
simple_sentence_zh

practice_phrase
related_words_json
question_en

created_at
```

Requirements:

- `client_id` indexed;
- no image path;
- no image bytes/blob;
- no Base64;
- no EXIF;
- no raw provider JSON;
- no OCR transcript;
- no provider request/response;
- no auth data;
- related words store only the normalized educational list;
- schema remains SQLite/PostgreSQL friendly.

Only persist:

```text
status == ok
```

For:

```text
unclear
unsuitable
```

return a safe response but do not create a durable learning record.

Create a thin:

```text
PhotoLearningRepository
```

It only needs operations used by TASK 019:

```text
save(...)
get_owned(record_id, client_id)
```

`get_owned` is needed for the TTS listen action.

Do not add history/list/search endpoints in this task.

Do not create a generic LearningMemory table.

---

# API

Add router namespace:

```text
/api/photo
```

All endpoints require:

```text
valid X-Client-Id
existing StudentProfile
```

## POST `/api/photo/analyze`

Multipart:

```text
file=<image>
```

Flow:

```text
validate profile
→ temporary image normalization
→ Qwen/Fake Vision
→ strict normalize/guard
→ if ok: persist safe learning record
→ cleanup image
→ return child-safe response
```

No TTS call during analysis.

No second text LLM call.

The Qwen Vision result itself should already be the structured child lesson.

Suggested response:

```json
{
  "status": "ok",
  "record_id": 42,
  "primary_word_en": "apple",
  "primary_meaning_zh": "苹果",
  "simple_sentence_en": "This is a red apple.",
  "simple_sentence_zh": "这是一个红苹果。",
  "practice_phrase": "apple",
  "related_words": [
    {"word_en": "red", "meaning_zh": "红色"},
    {"word_en": "fruit", "meaning_zh": "水果"}
  ],
  "question_en": "What color is the apple?",
  "encouragement_zh": "很好！来读一读 apple 吧。",
  "suggested_actions": ["listen", "repeat", "practice_chat"]
}
```

For unclear:

```json
{
  "status": "unclear",
  "record_id": null,
  "message_zh": "这张照片有点看不清，换个角度再拍一次吧。",
  "suggested_actions": ["retake"]
}
```

For unsuitable:

```json
{
  "status": "unsuitable",
  "record_id": null,
  "message_zh": "我们换一张动物、食物、玩具或学习用品的照片来学英语吧。",
  "suggested_actions": ["retake"]
}
```

Do not explain internal safety classification details to the child.

## POST `/api/photo/records/{record_id}/listen`

Purpose:

```text
🔊 听一听
```

Flow:

```text
ownership lookup
→ load persisted practice_phrase
→ existing TTSGateway
→ existing TemporaryMediaStore
→ project-owned /api/voice/media/... URL
```

Requirements:

- client does not submit arbitrary TTS text;
- only synthesize the owned persisted `practice_phrase`;
- no DB write required;
- TTS failure → safe 503;
- no provider URL exposure;
- media stays short-lived as in current Voice.

Response:

```json
{
  "audio_url": "/api/voice/media/..."
}
```

Do not add a new audio-storage subsystem.

---

# MiniProgram

## 1. Home

Make the existing:

```text
📷 拍一拍
```

entry navigate to:

```text
/pages/photo/index
```

Keep the five main Home entries unchanged.

## 2. Photo page

Add a focused page:

```text
pages/photo/index
```

Do not add Photo behavior into the existing Chat page.

Use existing TDesign components.

Initial UI:

```text
📷 拍照
🖼️ 从相册选择
```

These can both call the same native media helper with different source settings, or use one combined chooser if that gives a cleaner UX.

Use native:

```text
wx.chooseMedia
```

with a single image and compressed output, e.g. conceptually:

```text
count: 1
mediaType: ["image"]
sizeType: ["compressed"]
sourceType: ["camera"] or ["album"]
```

Verify exact current API behavior from the local official demo/current docs.

Do not add a media-picker dependency.

## 3. Local preview

Show the selected local temporary image immediately with the native `<image>` component.

Do not upload/save the preview anywhere except the analysis request.

Do not call `wx.saveFile`.

Do not store image path in `wx.storage`.

## 4. Analyze state

Expected UI states:

```text
idle
selected/analyzing
ok
unclear
unsuitable
error
```

Prevent duplicate analysis taps while in flight.

Show child-friendly errors only.

## 5. Learning result

For `status=ok`, emphasize:

```text
APPLE
苹果

This is a red apple.
这是一个红苹果。

相关词:
red
fruit
```

Do not dump raw model description.

## 6. `🔊 听一听`

Call:

```text
POST /api/photo/records/{record_id}/listen
```

and reuse:

```text
audio-player.js
```

Do not build another player.

## 7. `🎤 跟我读`

Reuse TASK 017 exactly:

```text
practice_phrase
→ existing Recorder
→ pronunciationService.evaluate(...)
→ /api/pronunciation/evaluate
```

Do not add a Photo-specific ISE endpoint.

Use the same recorder lifecycle patterns already used by Chat/Scenario.

A small reusable pronunciation-result presentation can be extracted only if it materially reduces duplicated code; do not create a UI framework.

## 8. `💬 和我练`

Do not create Photo Conversation Memory yet.

Reuse the existing Tutor chat.

Create a deterministic draft such as:

```text
Let's practice the word "apple".
```

or a similarly short prompt.

Navigate to existing:

```text
/pages/chat/index
```

with an encoded draft/prefill parameter.

Update Chat page only enough to safely accept an optional bounded draft query parameter.

Do **not** auto-send the message on page load.

Do not send raw image or photo record to `/api/tutor/chat`.

## 9. Retake

For unclear/unsuitable/error:

```text
再拍一张
```

must reset result/audio/pronunciation state cleanly.

---

# MiniProgram service boundary

Add a thin:

```text
services/photo.js
```

Expected responsibilities:

```text
analyze(filePath)
listen(recordId)
resolveAudioUrl(path)
```

Image selection can live in a tiny native `media` helper if it is reused/testable.

Do not put API URLs directly throughout the page.

Reuse current:

```text
services/api.js
services/audio-player.js
services/recorder.js
services/pronunciation.js
```

---

# API upload behavior

The current shared `api.upload()` already sends:

```text
X-Client-Id
multipart/form-data
```

Reuse it.

If Photo needs content-type/filename behavior not exposed by the current helper, make the smallest adjacent improvement.

Do not create a second upload implementation.

Ensure existing audio upload callers remain unchanged.

---

# Child/privacy rules

Photo input is higher privacy risk than audio/text, so TASK 019 must make this explicit.

Backend rules:

```text
raw photo
→ temporary only
→ metadata stripped before provider
→ provider analysis
→ deleted
```

Persistent record:

```text
safe normalized English-learning fields only
```

Never persist:

```text
photo
thumbnail
Base64
EXIF/GPS
raw OCR
raw provider response
provider request
face embedding
person identity
```

The app must not claim facial recognition.

Do not identify real people in images.

Do not infer sensitive personal traits from a person.

Do not encourage photographing identity documents, addresses, accounts, private chats, medical documents or other personal records.

---

# Offline tests

## Backend — image validation

Cover at least:

- valid JPEG;
- valid PNG;
- valid WebP if supported by installed Pillow;
- empty file;
- unsupported extension/MIME;
- corrupt image;
- oversized byte upload;
- excessive/decompression-bomb image rejected;
- EXIF orientation handled;
- normalized image metadata/EXIF stripped;
- large image resized within configured bounds;
- temp files deleted after success and all failure paths.

Tests should generate tiny images with Pillow in temporary directories, not commit binary fixtures unless truly necessary.

## Vision provider

Cover:

- FakeVision deterministic and offline;
- fake provider production fail-safe;
- Qwen config missing → safe configuration error;
- Qwen multimodal request contains Base64 `data:image/...`;
- raw local path is not sent to provider;
- strict structured-output config/schema used;
- provider response normalized into domain type;
- malformed/invalid result → normalized provider error;
- no Base64/raw response in logs.

Mock the OpenAI client. Default tests must not call Alibaba.

## Learning-result guard

Cover:

- valid `ok`;
- `unclear`;
- `unsuitable`;
- blank required field;
- too many related words;
- duplicate related word;
- invalid/overlong practice phrase;
- URL/email rejected;
- obvious phone/long-account number rejected;
- unsuitable result not persisted.

## API

Cover:

- missing Profile short-circuits before Vision;
- valid analysis success;
- analysis success persists safe record;
- image bytes never stored in DB;
- raw provider JSON never stored;
- unclear returns no record;
- unsuitable returns no record;
- provider error → safe 503;
- temp image cleanup;
- client A cannot listen to client B record;
- listen uses persisted phrase, not client-supplied arbitrary text;
- listen reuses TTS + project media URL;
- TTS error safe 503.

## Migration

Cover new Alembic revision:

```text
upgrade → downgrade → upgrade
```

and:

```text
alembic check
```

---

# MiniProgram tests

Keep the current lightweight Node approach.

Cover important behavior:

- Home camera entry routes to `/pages/photo/index`;
- photo page uses native image selection rather than local hard-coded sample;
- chooser is constrained to one image;
- analyze uploads chosen temp file to `/api/photo/analyze`;
- local preview is retained only in page state;
- `ok` result renders core learning fields;
- `unclear` / `unsuitable` show retake state;
- listen calls owned record endpoint and uses existing audio player;
- repeat uses existing `pronunciationService.evaluate()` with `practice_phrase`;
- practice-chat navigation pre-fills existing Chat but does not auto-send;
- retake clears prior audio/pronunciation/result state;
- normal Chat, Voice, Scenario paths remain unchanged.

Do not add a heavy UI-test framework.

---

# Real provider integration test

Add an opt-in real Qwen Vision test.

Suggested usage:

```bash
RUN_REAL_PROVIDER_TESTS=1 \
REAL_VISION_IMAGE_PATH=/absolute/path/outside/repo/apple.jpg \
uv run --env-file .env \
pytest -m real_provider -k qwen_vision -vv -s
```

Requirements:

- fixture must be outside the repo;
- skip clearly if missing;
- do not delete/modify owner's input image;
- real call should verify a normalized result is returned;
- do not assert one exact word for a complex arbitrary image;
- if using a controlled apple/toy image, a modest semantic assertion is acceptable;
- no Base64/secrets/raw provider response printed.

Real Vision verification is useful but **not required to block TASK 019 offline completion** if no suitable image fixture is available.

TASK 017 real ISE may remain unverified independently; do not couple it to this test.

---

# Optional latency logging

Vision calls can be slow/costly.

Add sanitized timing similar to current Voice provider logging:

```text
photo_analysis_latency vision_ms=...
```

Do not log:

```text
image name
raw child content
Base64
full model result
```

No benchmark framework is needed.

---

# Docs

Update only docs affected by actual implementation, likely:

```text
README.md
docs/PRODUCT.md
docs/ARCHITECTURE.md
docs/API_CONTRACT.md
docs/DATA_MODEL.md
docs/PRIVACY_SECURITY.md
docs/PROVIDER_DECISION.md or PROVIDER_STRATEGY if appropriate
docs/TEST_PLAN.md
.env.example
```

Document distinctly:

```text
Photo input
= transient, not persistent

PhotoLearningRecord
= safe normalized learning facts only

VisionGateway
= provider boundary

Qwen Vision
= current default implementation
```

Do not document image history/gallery as implemented.

Do not document long-term-memory inference as implemented.

---

# Out of scope

Do not implement:

- image gallery/history UI;
- permanent photo storage;
- OSS/S3;
- OCR product;
- document scanning;
- face recognition;
- person identification;
- sensitive-trait inference;
- video understanding;
- multiple-image reasoning;
- image editing/generation;
- Photo Conversation Memory;
- photo-specific STT;
- photo-specific pronunciation provider;
- automatic pronunciation scoring immediately after image analysis;
- Scene changes;
- generic learning-memory engine;
- RAG/textbook;
- Story;
- WeChat login/auth;
- PostgreSQL deployment;
- realtime Pipecat;
- provider routing/A-B/fallback;
- manual WeChat/real-device acceptance;
- commit/push/remote changes.

---

# Definition of Done

TASK 019 is complete when:

1. Home `📷 拍一拍` navigates to a real Photo page.
2. MiniProgram uses native image selection/camera APIs with one compressed image.
3. backend has a dedicated temporary image validation/normalization boundary.
4. Pillow verifies/normalizes/resizes images and strips metadata.
5. raw child photo is never persisted.
6. `VisionGateway` + Fake/Qwen implementations exist.
7. current Qwen Vision call uses the existing Alibaba workspace/key and Base64 image input.
8. structured provider output is enforced with the current mature OpenAI-compatible structured-output mechanism.
9. provider output is normalized/guarded before persistence or public response.
10. unsafe/private/unclear input can return a safe non-learning outcome without persistence.
11. successful learning records persist only safe normalized educational fields.
12. new Alembic migration creates `photo_learning_records`.
13. `/api/photo/analyze` is profile/owner aware and cleans temporary images on all paths.
14. `🔊 听一听` reuses TTSGateway + TemporaryMediaStore and only speaks the owned persisted phrase.
15. `🎤 跟我读` reuses TASK 017 Pronunciation API.
16. `💬 和我练` reuses existing Tutor Chat through a safe prefilled draft; no image is passed to Chat.
17. default backend tests remain fully offline and pass.
18. MiniProgram tests pass.
19. migration/check passes.
20. existing Tutor/Voice/Pronunciation/Scenario tests remain green.
21. `git diff --check` passes.
22. `.env`, local DB, photos/audio, Base64 and provider secrets are not tracked.
23. opt-in real Qwen Vision test exists and is run if a suitable external image fixture is available; otherwise skip/report honestly.
24. no commit, push, or remote change is performed.

---

# Final Codex report

Report concisely:

```text
1. files/dependencies changed
2. TemporaryImage validation/normalization behavior
3. VisionGateway structure
4. Qwen Vision model/config and structured-output mechanism
5. child/privacy prompt + result guard behavior
6. photo_learning_records migration/schema
7. /api/photo/analyze behavior
8. listen/TTS reuse
9. pronunciation reuse
10. Chat prefill reuse
11. MiniProgram Photo flow
12. offline pytest result
13. MiniProgram test result
14. Alembic/migration result
15. real Qwen Vision result or exact reason skipped
16. TASK 017 real ISE status (unchanged unless independently tested)
17. security/privacy checks
18. local references actually inspected
19. whether any reference code was copied and notice status
20. limitations/blockers
```
