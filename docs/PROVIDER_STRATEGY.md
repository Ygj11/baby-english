# PROVIDER_STRATEGY.md

## 1. 原则

架构和 provider 分离。

Codex 不得自行替项目 owner 选择或注册付费供应商。

代码必须允许 provider 被替换。

## 2. 自动测试

所有外部 provider 必须有 Fake：

```text
FakeLLM
FakeSTT
FakeTTS
```

普通：

```bash
uv run pytest
```

不得依赖真实 API key。

## 3. LLM

MVP 目标：

- 中文理解好
- 英文教学能力稳定
- 支持 OpenAI-compatible 或 Pipecat 已支持的 service
- 中国大陆可用性良好

候选：

- Qwen
- DeepSeek
- 其他 OpenAI-compatible provider

真实默认值由 owner 在 Task 006 开始前确定或通过 `.env` 配置。

不要在代码中把产品逻辑绑定模型品牌。

## 4. STT

分成两种路径。

### MVP Batch STT

```text
录完一句
↓
upload
↓
STTGateway.transcribe(...)
```

Gateway 可：

- 使用 provider 官方 SDK/API；
- 或使用 Pipecat service，如果其当前 API 自然支持该调用模式。

禁止为了“必须用 Pipecat”人为构造复杂 Frame pipeline。

### Realtime STT

实时/流式阶段：

优先使用 Pipecat pipeline + supported STT service。

## 5. TTS

### MVP Batch TTS

```text
text
↓
TTSGateway.synthesize(...)
↓
audio
```

与 STT 同原则。

### Realtime TTS

实时阶段：

优先通过 Pipecat TTS service 进入 Voice pipeline。

## 6. Pronunciation

发音评测独立于 STT。

第一候选：

- 讯飞 ISE

不要用“ASR 识别正确率”冒充发音评分。

## 7. Owner Decision Gates

在以下 Task 前，owner 需要决定/准备：

### Task 006

至少一种真实 LLM key（若希望真实联调）。

### Task 009

至少一种真实 STT 方案（若希望真实联调）。

### Task 010

至少一种真实 TTS 方案（若希望真实联调）。

没有 key 时：

Codex 仍应完成 Fake + Adapter + contract，不得阻塞代码基线。
