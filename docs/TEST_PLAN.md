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

## 3. MiniProgram

自动化能力有限时至少：

- npm install/build 可完成
- service 层可测试则测试
- 微信开发者工具 smoke test

## 4. Provider Tests

Unit/CI：

全部 mock。

Manual Integration：

本地有 key 时运行真实：

- Qwen LLM `qwen3.7-flash`
- Qwen STT `qwen-audio-3.0-asr-flash`
- Qwen TTS `qwen-audio-3.0-tts-flash`

真实 key 不进入源码。

## 5. E2E

### Text

```text
MiniProgram
↓
/api/tutor/chat
↓
儿童回答
```

### Voice

```text
Recorder
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
