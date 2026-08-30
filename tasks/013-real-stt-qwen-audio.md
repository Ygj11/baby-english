# TASK 013 — Real Batch STT: Qwen Audio 3.0 ASR Flash

## Goal

为现有 `STTGateway` 接入 Alibaba Cloud Model Studio：

```text
qwen-audio-3.0-asr-flash
```

用于当前 MiniProgram 的 batch Push-to-Talk。

不做 realtime STT。

---

## Preconditions

- TASK 012 已完成并通过。
- 阅读：
  - `AGENTS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/PROVIDER_DECISION.md`
  - `docs/PROVIDER_STRATEGY.md`
  - `docs/PRIVACY_SECURITY.md`
  - `docs/API_CONTRACT.md`
  - 本 task

---

## Owner-selected Configuration

```env
STT_PROVIDER=qwen_audio

DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing

STT_MODEL=qwen-audio-3.0-asr-flash
STT_LANGUAGE_HINTS=zh,en
STT_TIMEOUT=60
```

China Beijing endpoint：

```text
https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
```

不要把 Workspace ID 或 Key 写死源码。

---

## Current Audio Fact

当前 MiniProgram Recorder：

```text
sampleRate: 16000
numberOfChannels: 1
format: mp3
```

因此第一版真实 STT 可以直接使用 MP3：

```text
data:audio/mpeg;base64,...
parameters.format = mp3
parameters.sample_rate = 16000
```

当前主路径不需要 FFmpeg。

---

## Implementation

1. 确保 `httpx` 是正式 runtime dependency，不依赖仅 dev/transitive 安装。
2. 实现：
   ```text
   QwenAudioSTT
   ```
   并继续满足现有 `STTGateway`。
3. 将临时 MP3/WAV 音频读为 bytes。
4. 使用 Base64 Data URI 调官方 HTTP JSON API。
5. Header：
   ```text
   Authorization: Bearer ...
   Content-Type: application/json
   X-DashScope-SSE: disable
   ```
6. Request 使用：
   ```text
   model=qwen-audio-3.0-asr-flash
   ```
7. `language_hints` 默认从：
   ```text
   STT_LANGUAGE_HINTS=zh,en
   ```
   解析。
8. 不使用公网临时音频 URL。
9. 解析：
   ```text
   output.text
   usage.duration
   ```
10. 转换成现有：
    ```text
    Transcript(text=..., duration_ms=...)
    ```
11. provider 网络、超时、非 2xx、错误 JSON、空 transcript → `STTError`。
12. `create_stt()`：
    - fake → FakeSTT
    - qwen_audio → QwenAudioSTT
13. 缺少 API Key / Workspace ID / Model 时 real provider 必须 configuration error。

---

## Audio Format Handling

当前 MiniProgram MP3 必须直接工作。

如果 API endpoint 收到其他现有允许格式：

- 不得把 M4A/AAC 等文件伪装成 MP3；
- 如果当前 adapter 不支持，返回受控错误；
- 可在后续任务增加 FFmpeg normalization；
- 不为了本 task 扩大成完整 media transcoding framework。

---

## Future Extension Point

Qwen Audio 当前支持 context/hotwords。

本 task 可以保留一个清晰扩展点，但不要提前实现教材热词系统。

禁止硬编码：

```text
dog
cat
PEP Unit 4
```

等教材词汇。

---

## Tests

默认 pytest 不访问阿里云。

至少覆盖：

- endpoint 生成（cn-beijing）；
- MP3 → Base64 Data URI；
- `language_hints=["zh","en"]`；
- mock provider success → Transcript；
- duration 秒 → ms；
- timeout → `STTError`；
- 401/403/5xx → `STTError`；
- malformed response → `STTError`；
- empty output.text → `STTError`；
- missing Workspace/Key → config error；
- FakeSTT 无回归；
- voice `/transcribe` 与 `/turn` 现有 tests 无回归。

---

## Optional Real Integration

有真实 key 时：

使用一段本地 MP3 实测。

建议至少测：

1. 中文：
   ```text
   苹果英文怎么说
   ```
2. 英文：
   ```text
   What's this?
   ```
3. 中英混说：
   ```text
   我想学 dog
   ```

只记录 transcript 和 latency，不记录/提交原始儿童录音。

---

## Do Not

- 不接 realtime WebSocket ASR
- 不接 Pipecat streaming STT
- 不实现教材 hotwords
- 不长期保存录音
- 不接 TTS
- 不执行 git push
- 不开始 TASK 014

---

## Verification

```bash
uv sync
uv run pytest
```

---

## Definition of Done

- [ ] Qwen Audio STT real adapter 已存在
- [ ] 当前微信 MP3 可直接调用
- [ ] Base64 audio 不落公网 URL
- [ ] zh/en hints 正确
- [ ] provider error 正常映射
- [ ] FakeSTT 继续可用
- [ ] 默认测试不访问网络
- [ ] 原始上传音频继续 cleanup
- [ ] 全量测试通过
