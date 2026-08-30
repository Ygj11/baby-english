# TASK 014 — Real Batch TTS: MiniMax Speech 2.8 Turbo

## Goal

为现有 `TTSGateway` 接入 MiniMax：

```text
speech-2.8-turbo
```

让 `/api/voice/turn` 返回真正可播放的 AI Teacher 音频。

不做 realtime Pipecat TTS。

---

## Preconditions

- TASK 013 完成并通过。
- 阅读：
  - `AGENTS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/PROVIDER_DECISION.md`
  - `docs/PRIVACY_SECURITY.md`
  - `docs/API_CONTRACT.md`
  - 本 task

---

## Owner-selected Configuration

```env
TTS_PROVIDER=minimax

MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/t2a_v2

TTS_MODEL=speech-2.8-turbo
MINIMAX_VOICE_ID=
TTS_SPEED=0.9
TTS_TIMEOUT=60
```

`MINIMAX_VOICE_ID` 必须由 owner 在 MiniMax 平台选择，不在源码里决定儿童老师音色。

---

## Implementation

1. 实现：
   ```text
   MiniMaxTTS
   ```
   并满足现有 `TTSGateway`。
2. 使用 async HTTP client。
3. 调用当前 MiniMax domestic T2A endpoint。
4. Header：
   ```text
   Authorization: Bearer ...
   Content-Type: application/json
   ```
5. Request 至少包括：
   ```text
   model
   text
   stream=false
   voice_setting.voice_id
   voice_setting.speed
   audio_setting.format=mp3
   audio_setting.channel=1
   ```
6. 使用 `speech-2.8-turbo`。
7. 第一版输出 MP3。
8. 正确解析 MiniMax 非流式返回的 audio data。
9. 若 provider 返回 hex audio，decode 成真实 bytes。
10. 返回：
    ```text
    SynthesizedAudio(
      data=<mp3 bytes>,
      content_type="audio/mpeg",
      extension=".mp3"
    )
    ```
11. 不向 MiniProgram 暴露 MiniMax provider URL。
12. 继续通过现有 TemporaryMediaStore 提供：
    ```text
    /api/voice/media/{media_id}
    ```
13. provider timeout、network、non-2xx、provider error code、invalid/empty audio → `TTSError`。
14. `create_tts()`：
    - fake → FakeTTS
    - minimax → MiniMaxTTS
15. real provider 缺少 API Key / Voice ID / Model → configuration error。

---

## Voice Behavior

默认：

```text
TTS_SPEED=0.9
```

本 task 不实现复杂 voice profile。

不实现：

- 慢速按钮动态参数更新
- emotion 自动决策
- voice cloning
- story voice
- multiple characters

这些后续再做。

---

## Tests

默认 pytest 不调用 MiniMax。

至少：

- env → MiniMaxTTS；
- request payload model；
- voice ID；
- speed；
- MP3 mono settings；
- mock hex audio → bytes；
- correct `audio/mpeg`；
- empty audio → TTSError；
- provider error → TTSError；
- timeout → TTSError；
- missing voice/key → config error；
- FakeTTS 无回归；
- TemporaryMediaStore / media endpoint 无回归。

---

## Optional Real Integration

有真实 MiniMax Key + Voice ID 后：

生成：

```text
Apple. Repeat after me: apple.
```

验收：

- 返回 MP3；
- 文件实际可播放；
- 英文发音可理解；
- 没有空文件；
- 不把 Key 写入日志。

owner 人工试听并记录：

- 自然度
- 英文口音
- 语速
- 儿童友好程度

---

## Do Not

- 不做 voice cloning
- 不做 emotion routing
- 不做 streaming Pipecat
- 不换 TTS provider
- 不做 ISE
- 不执行 git push
- 不开始 TASK 015

---

## Verification

```bash
uv sync
uv run pytest
```

---

## Definition of Done

- [ ] MiniMax real TTS adapter 已存在
- [ ] speech-2.8-turbo 由 env 配置
- [ ] Voice ID 由 owner 配置
- [ ] 输出 MP3 可进入现有 media store
- [ ] FakeTTS 继续工作
- [ ] provider error 不泄露
- [ ] 默认测试无网络消费
- [ ] 全量测试通过
