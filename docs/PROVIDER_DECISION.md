# PROVIDER_DECISION.md

本文件记录 repository owner 已确认的第一版真实 Provider 方案。

除非 repository owner 明确要求，Codex 不得自行替换模型或厂商。

## 1. LLM — DeepSeek

使用 OpenAI-compatible API。

真实开发环境：

```env
LLM_PROVIDER=openai_compatible

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
OPENAI_TIMEOUT=1800
```

说明：

- `OPENAI_TIMEOUT=1800` 是 repository owner 当前明确指定值。
- Codex 不得自行改成 60/90/其他值。
- `.env.example` 只能保留空 Key，不得写真实 Key。
- `deepseek-v4-pro` 使用 DeepSeek 当前兼容 OpenAI API 的模型名。

官方参考：

- https://api-docs.deepseek.com/

---

## 2. STT — Alibaba Cloud Model Studio

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

## 3. TTS — MiniMax

第一版 Batch TTS：

```env
TTS_PROVIDER=minimax

MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/t2a_v2

TTS_MODEL=speech-2.8-turbo
MINIMAX_VOICE_ID=
TTS_SPEED=0.9
TTS_TIMEOUT=60
```

`MINIMAX_VOICE_ID` 不在源码硬编码，由 repository owner 从 MiniMax 控制台选定。

第一版输出：

```text
MP3
mono
```

TTS adapter 返回项目自己的：

```text
SynthesizedAudio
```

不把 provider URL 暴露给 MiniProgram。

官方/框架参考：

- https://solutions.minimaxi.com/debug/speech
- https://docs.pipecat.ai/api-reference/server/services/tts/minimax

---

## 4. Architecture Boundary

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

## 5. Secrets

真实 Key 只放：

```text
.env
```

绝不提交：

```text
OPENAI_API_KEY
DASHSCOPE_API_KEY
MINIMAX_API_KEY
```

自动测试必须 mock provider。

真实 API integration test 必须是 opt-in。
