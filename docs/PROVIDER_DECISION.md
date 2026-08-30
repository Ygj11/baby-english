# PROVIDER_DECISION.md

本文件记录 repository owner 已确认的第一版真实 Provider 方案。

除非 repository owner 明确要求，Codex 不得自行替换模型或厂商。

## 1. 默认共享配置 — Alibaba Cloud Model Studio

Qwen LLM、STT、TTS 共用 owner 的北京 Workspace：

```env
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing
```

Key 和 Workspace ID 只存在本地 `.env`，不得写入源码、测试、日志或文档。

---

## 2. 默认 LLM — Qwen

```env
LLM_PROVIDER=qwen
LLM_MODEL=qwen3.7-flash
LLM_TIMEOUT=60
```

通过 Workspace 专属 OpenAI-compatible endpoint 调用：

```text
https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
```

DeepSeek `deepseek-v4-pro` adapter 保留，定位为未来高级/复杂任务模型；当前不做自动路由、fallback 或 A/B。

官方参考：

- https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions

---

## 3. 默认 STT — Qwen Audio

第一版 Batch STT：

```env
STT_PROVIDER=qwen_audio

DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing

STT_MODEL=qwen-audio-3.0-asr-flash
STT_LANGUAGE_HINTS=zh,en
STT_TIMEOUT=60
```

中国北京 endpoint：

```text
https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
```

当前官方接口：

- HTTP JSON
- Authorization Bearer API Key
- 支持 Base64 Data URI
- `qwen-audio-3.0-asr-flash` 支持 `zh` / `en` language hints
- 支持 inline hotwords
- 当前 MiniProgram Recorder 输出 16 kHz mono MP3，可直接作为当前 MVP 输入

本项目第一版使用 Base64 Data URI，不要求先上传音频到公网 URL。

官方参考：

- https://www.alibabacloud.com/help/en/model-studio/non-real-time-speech-recognition-for-fun-asr-flash

---

## 4. 默认 TTS — Qwen Audio

```env
TTS_PROVIDER=qwen_audio
TTS_MODEL=qwen-audio-3.0-tts-flash
TTS_VOICE=longanhuan_v3.6
TTS_SPEED=0.9
TTS_TIMEOUT=60
```

使用官方 DashScope SDK 访问 Workspace WebSocket：

```text
wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference
```

`longanhuan_v3.6` 是官方示例中的中英双语 system voice；第一版固定使用，不做 voice routing。输出为 mono MP3，并继续包装为：

```text
SynthesizedAudio
```

MiniMax adapter 保留但不再是默认 TTS，也不纳入当前成功条件。

官方参考：

- https://www.alibabacloud.com/help/en/model-studio/realtime-tts-user-guide
- https://www.alibabacloud.com/help/en/model-studio/qwen-audio-tts-voice-list

---

## 5. Architecture Boundary

Tasks 012–015 属于：

```text
Batch Voice MVP
```

仍然使用：

```text
LLMGateway
STTGateway
TTSGateway
```

不要为了接真实 provider 重构成 Pipecat realtime pipeline。

Pipecat 继续保留给后续：

- realtime streaming
- turn detection
- barge-in
- realtime transport

---

## 6. Retained Adapters

- DeepSeek：`LLM_PROVIDER=openai_compatible`，保留原 `OPENAI_*` 配置；
- MiniMax：`TTS_PROVIDER=minimax`，保留原 `MINIMAX_*` 配置；
- 两者均不是默认 Voice MVP provider。

---

## 7. Secrets

真实 Key 只放：

```text
.env
```

绝不提交：

```text
DASHSCOPE_API_KEY
OPENAI_API_KEY
MINIMAX_API_KEY
```

自动测试必须 mock provider。

真实 API integration test 必须是 opt-in。
