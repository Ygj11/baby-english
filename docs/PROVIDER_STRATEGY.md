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

环境规则：

```text
APP_ENV=development | test | production
```

- `development` / `test` 允许空 provider 或 `fake`，并使用对应 Fake；
- `production` 禁止空 provider 和 `fake`，缺少真实 provider 配置时必须明确失败；
- LLM、STT、TTS 使用同一条 fail-safe 规则。

## 3. LLM

MVP 目标：

- 中文理解好
- 英文教学能力稳定
- 支持 OpenAI-compatible 或 Pipecat 已支持的 service
- 中国大陆可用性良好

当前默认：Qwen `qwen3.7-flash`。DeepSeek adapter 保留给未来高级/复杂任务，但不自动路由或 fallback。

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

当前默认：Qwen Audio `qwen-audio-3.0-asr-flash`。

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

当前默认：Qwen Audio `qwen-audio-3.0-tts-flash`；MiniMax adapter 保留但不是默认值。

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
