# TEST_PLAN.md

## 1. 原则

每个 task 必须独立可验收。

外部 provider 不能成为普通自动测试硬依赖。

所有外部能力必须支持 mock/fake。

## 2. Backend

推荐：

- pytest
- pytest-asyncio
- httpx

至少覆盖：

- health
- tutor chat
- child policy
- audio validation
- provider adapter
- voice orchestration
- Alembic 空 SQLite upgrade/downgrade/upgrade
- StudentProfile repository create/get/upsert/client isolation
- Profile API validation 与 internal id 隐藏
- Tutor/Voice stored Profile prerequisite 和 provider zero-call
- Pronunciation ISE 协议帧、评分解析、Profile 前置条件与 attempt 持久化
- Scenario catalogue/public projection、prompt/history、session ownership/limit
- Scenario text/voice 成功 pair、provider failure、assessment/idempotency/atomic cleanup
- Scene goal progress derivation 与跨 session completion count
- Photo JPEG/PNG/WebP 校验、byte/pixel bomb、EXIF orientation、resize、metadata strip 与全路径 cleanup
- Fake/Qwen Vision structured-output request、domain guard、owner persistence/listen/TTS 与安全错误
- Textbook source package validation/fingerprint/path traversal/line-safe errors
- Fake/Qwen embedding config、LlamaIndex ingestion/persist/reload/manifest compatibility/atomic failure cleanup
- Unit exact metadata retrieval、bounded top-k、grounded prompt/no-context zero-LLM path
- Textbook catalogue/unit/client selection repository 与 API ownership/safe 409/503/public projection

## 3. MiniProgram

自动化能力有限时至少：

- npm install/build 可完成
- service 层可测试则测试
- 微信开发者工具 smoke test
- client id 稳定复用及 request/upload header 注入
- Profile service/page load/save 与 Chat 设置引导
- `repeat_text` 缺失时隐藏跟读、普通 Voice 与 Pronunciation 上传分流、评分状态展示
- Home → scenario catalogue、opener、text/voice session endpoint、goal phrase 跟读与完成总结
- Home → Photo、单张压缩 `wx.chooseMedia`、本地 preview、analyze/listen/repeat/Chat prefill/retake
- Home → backend-driven textbook catalogue、selection、Unit persistence、QA answer/source/not-found state

## 4. Provider Tests

Unit/CI：

全部 mock。

Manual Integration：

本地有 key 时运行真实：

- Qwen LLM `qwen3.7-flash`
- Qwen STT `qwen-audio-3.0-asr-flash`
- Qwen TTS `qwen-audio-3.0-tts-flash`
- Xunfei streaming ISE（需显式提供 repo 外英文 MP3 和 reference text）
- Qwen Vision `qwen3.7-flash`（需显式提供 repo 外 JPEG/PNG/WebP）
- Qwen Embedding `qwen3.7-text-embedding`（1024 维 harmless synthetic strings）
- synthetic temporary textbook → real Qwen embedding/retrieval → existing real Qwen LLM grounded E2E

真实 key 不进入源码。

默认 pytest 使用 `FakePronunciationGateway`，不连接讯飞。真实 ISE 仅通过
`RUN_REAL_PROVIDER_TESTS=1` 和 `REAL_ISE_AUDIO_PATH` opt-in；测试只断言规范化结果，
不输出鉴权 URL、原始 XML 或 secret。

真实 Vision 仅通过 `RUN_REAL_PROVIDER_TESTS=1` 和 repo 外
`REAL_VISION_IMAGE_PATH` opt-in；普通 pytest 使用 Fake/Mock，不输出图片 Base64 或原始
provider response。

真实教材 RAG 测试只使用测试运行时生成的虚构玩具/动物事实，不需要也不得提交真实教材正文；
普通 pytest 使用 LlamaIndex `MockEmbedding`，不连接 Embedding API。

## 5. E2E

### Text

```text
MiniProgram
↓
PUT/GET /api/student/profile
↓
/api/tutor/chat
↓
儿童回答
```

### Voice

```text
Recorder
↓
stored StudentProfile
↓
Upload
↓
STT
↓
Tutor
↓
TTS
↓
Playback
```

Task 010 自动测试使用 Fake/Mock STT、LLM、TTS，验证：

- 上传音频到 transcript；
- transcript 进入 Child Tutor；
- reply 进入 TTS；
- 返回本项目临时 media URL；
- provider failure 映射为安全错误；
- 上传临时文件和过期回复音频 cleanup。

## 6. Child Tutor Golden Cases

### Age 8 / Beginner

Input：

> apple怎么说

要求：

- 短
- 有 apple
- 鼓励跟读
- 不讲复杂语法

### Age 11 / Elementary

Input：

> apple和apples有什么区别

允许简单解释单复数。

测试尽量验证 prompt/policy 与结构，不依赖真实 LLM 随机输出。

## 7. Regression Rule

禁止通过：

- 删除测试
- skip 测试
- 把断言改到失去意义

来“修复”失败。


## 8. Batch vs Realtime Voice

Tasks 009–010 测试的是 batch Push-to-Talk orchestration，不要求 Pipecat realtime transport。

未来 realtime milestone 需要新增 Pipecat pipeline behavioral/e2e tests，不复用 batch test 假装已经覆盖 realtime。
