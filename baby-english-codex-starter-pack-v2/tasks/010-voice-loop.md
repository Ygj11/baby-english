# TASK 010 — End-to-End Batch Voice Loop

## Goal

完成第一阶段最重要的 Push-to-Talk 闭环：

```text
Recorder
↓
upload
↓
STTGateway
↓
Child Tutor
↓
LLM
↓
TTSGateway
↓
MiniProgram playback
```

这是 batch voice MVP，不是 realtime Pipecat transport milestone。

## Preconditions

Tasks 001–009 完成。

## Allowed Changes

```text
server/app/api/voice.py
server/app/voice/**
server/app/tutor/**
server/tests/**
miniprogram/services/voice.js
miniprogram/services/audio-player.js
miniprogram/pages/chat/**
.env.example
docs/API_CONTRACT.md
docs/TEST_PLAN.md
docs/PRIVACY_SECURITY.md（仅实际实现差异）
```

## API

新增：

```text
POST /api/voice/turn
```

orchestration：

1. 接收录音；
2. STTGateway；
3. Child Tutor；
4. LLM；
5. TTSGateway；
6. 返回：
   - transcript
   - reply
   - audio reference
   - suggested actions

前端不拼第三方 provider API。

## TTS Gateway

创建极薄：

```text
TTSGateway.synthesize(...)
```

策略：

1. 若当前 Pipecat TTS service 有自然适合 batch 的调用方式，可复用；
2. 否则使用 owner 选定 provider 的官方 SDK/API；
3. provider-specific 逻辑限制在 voice adapter 层。

必须提供：

```text
FakeTTS
```

Codex 不得自行选择收费 TTS 厂商。

## Audio Response

选择一种：

A. 本项目临时 audio URL  
B. media endpoint + ID

不要：

- 大量 base64 音频塞 JSON
- 长期暴露 provider 原始 URL

选定后更新 `docs/API_CONTRACT.md`。

## MiniProgram Playback

创建：

```text
services/audio-player.js
```

使用微信官方音频播放能力。

支持：

- play
- stop
- replay
- page unload cleanup

## UX

成功：

```text
我听到：
苹果英文怎么说

AI：
Apple 🍎
Repeat after me: apple.

[🔊 再听一次]
[🎤 跟我读]
[🇨🇳 中文讲讲]
```

失败不得显示 traceback/provider/raw error。

## Tests

必须 mock：

- STT
- LLM
- TTS

验证：

```text
audio
→ transcript
→ tutor
→ reply
→ audio
```

并验证：

- provider failure
- temp cleanup

## Manual Integration

如果 owner 已提供合法 keys：

真实测试：

> 苹果英文怎么说？

没有 key 时 Fake 测试仍必须完成，本 task 代码结构不得阻塞。

## Pipecat Note

完成本 task 只证明：

```text
Batch Push-to-Talk Product Loop
```

不代表 realtime voice 已实现。

后续 realtime milestone 应：

- 使用 Pipecat pipeline
- 使用 current Pipecat transport patterns
- 单独设计 MiniProgram transport compatibility

## Do Not

- 不做 realtime streaming
- 不做 WebSocket
- 不做 ISE
- 不做场景
- 不做教材
- 不做 memory
- 不做微信登录
- 不做支付

## Definition of Done

- [ ] 小程序可录音
- [ ] 可上传
- [ ] STT 得 transcript
- [ ] Child Tutor 生效
- [ ] LLM 回复
- [ ] TTS 生成音频
- [ ] 小程序播放
- [ ] Fake provider tests 全通过
- [ ] API contract 更新
- [ ] 临时儿童音频 cleanup
- [ ] 无超范围实现

完成后达到：

**Milestone 2 — Batch Push-to-Talk Voice Tutor**
