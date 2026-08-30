# TASK 015 — Real Provider Voice E2E

## Goal

使用真实 Provider 验证第一版产品闭环：

```text
微信 MiniProgram Recorder
↓
Qwen Audio STT
↓
Child Tutor
↓
DeepSeek V4 Pro
↓
MiniMax Speech 2.8 Turbo
↓
MiniProgram Playback
```

本 task 的重点是集成、错误处理、延迟观测和真机验收。

不增加新产品功能。

---

## Preconditions

- TASK 011–014 全部完成。
- `.env` 已由 repository owner 在本地配置真实：
  - `OPENAI_API_KEY`
  - `DASHSCOPE_API_KEY`
  - `DASHSCOPE_WORKSPACE_ID`
  - `MINIMAX_API_KEY`
  - `MINIMAX_VOICE_ID`
- `.env` 已 git ignored。
- 微信开发者工具可编译 TDesign npm。
- 默认 unit tests 全部通过。

---

## Required Configuration

```env
APP_ENV=development

LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
OPENAI_TIMEOUT=1800

STT_PROVIDER=qwen_audio
DASHSCOPE_API_KEY=...
DASHSCOPE_WORKSPACE_ID=...
DASHSCOPE_REGION=cn-beijing
STT_MODEL=qwen-audio-3.0-asr-flash
STT_LANGUAGE_HINTS=zh,en
STT_TIMEOUT=60

TTS_PROVIDER=minimax
MINIMAX_API_KEY=...
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/t2a_v2
TTS_MODEL=speech-2.8-turbo
MINIMAX_VOICE_ID=...
TTS_SPEED=0.9
TTS_TIMEOUT=60
```

不要把真实值复制进 task/docs/test fixtures。

---

## Implementation

### 1. Real integration path

确认现有：

```text
POST /api/voice/turn
```

真实依次使用：

```text
QwenAudioSTT
→ TutorService
→ OpenAICompatibleLLM
→ MiniMaxTTS
→ TemporaryMediaStore
```

不要创建第二条平行 Voice API。

### 2. Stage latency

在 server 内增加不含敏感内容的开发期 timing：

```text
stt_ms
llm_ms
tts_ms
total_ms
```

可以写 structured log。

禁止 log：

- 原始音频
- API Key
- 完整 provider response
- 不必要的儿童内容

### 3. Friendly failures

真实 provider 任一失败：

MiniProgram 仍只看到儿童友好错误。

server log 可以记录：

```text
provider stage
HTTP status category
request id（若安全）
exception class
```

但不要记录 secret/raw audio。

### 4. Existing cleanup

确认：

- 上传音频完成后删除；
- TTS temporary media 继续 TTL；
- 页面 unload audio/recorder cleanup 不回归。

---

## Automated Tests

默认：

```bash
uv run pytest
```

必须继续使用 mock/fake，不消耗真实 API。

另提供 opt-in real integration test 或 script，例如：

```bash
RUN_REAL_PROVIDER_TESTS=1 uv run pytest -m real_provider
```

真实测试未配置 Key 时：

- skip；
- 不 fail 普通 test suite。

---

## Real Text Integration

先不通过录音，单独验证：

```text
/api/tutor/chat
```

输入：

```text
苹果英文怎么说？
```

确认：

- DeepSeek 真正返回；
- Child Tutor prompt 生效；
- 回复不是 Fake 固定文本。

---

## Real STT Integration

用 Mac/微信真实录音测试：

1. 中文：
   ```text
   苹果英文怎么说
   ```
2. English：
   ```text
   What's this?
   ```
3. Mixed：
   ```text
   我想学 dog
   ```

记录识别结果。

不要把儿童真实录音提交到 repo。

---

## Real TTS Integration

至少试听：

```text
Apple. Repeat after me: apple.
```

确认：

- 当前 media URL 返回 `audio/mpeg`；
- MiniProgram 可播放；
- replay 播放的是当前回复；
- 英文发音清楚；
- 语速约 0.9 符合 Beginner。

---

## End-to-End MiniProgram Smoke Test

真机/微信开发者工具：

1. 进入 Chat。
2. 录音：
   ```text
   苹果英文怎么说
   ```
3. 确认：
   - processing state；
   - transcript 是真实 STT；
   - reply 是真实 DeepSeek；
   - TTS 是真实 MiniMax；
   - 自动播放；
   - “再听”正常；
   - “跟读”重新录音；
   - “中文讲讲”仍工作。
4. 停掉 Backend：
   - UI 可恢复；
   - 无 traceback。
5. 临时删除一个 provider key：
   - server 给受控错误；
   - 不自动误用 Fake（遵循 TASK 011 规则）。

---

## Latency Report

记录至少 5 次真实 turn：

```text
STT
LLM
TTS
TOTAL
```

输出：

- median
- min
- max

当前只做观测，不因为公网波动设置强制 CI 门槛。

产品目标参考：

```text
尽可能让短句总等待时间接近或低于 10 秒
```

如果明显高于，应在报告中指出主要瓶颈。

---

## Security Check

确认：

```bash
git diff
git status
```

没有：

- `.env`
- API keys
- provider raw response dump
- 原始录音
- 生成音频 fixture 大文件

---

## Do Not

- 不做 realtime Pipecat
- 不做 WebSocket/WebRTC
- 不做数据库 memory
- 不做微信登录
- 不做场景英语
- 不做 pronunciation/ISE
- 不做 Vision
- 不做 Textbook/RAG
- 不做支付
- 不调整 provider 选型
- 不执行 git push

---

## Definition of Done

- [ ] DeepSeek real text chat 成功
- [ ] Qwen Audio real STT 成功
- [ ] MiniMax real TTS 成功
- [ ] `/api/voice/turn` 真实三 Provider 闭环成功
- [ ] MiniProgram 可实际播放真实 TTS
- [ ] Child Tutor 仍生效
- [ ] provider failure 显示友好
- [ ] Fake tests 继续全部通过
- [ ] real tests opt-in
- [ ] latency report 已产生
- [ ] 无 secret / 原始儿童音频进入 Git

---

## Completion Report

完成后输出：

1. 每个真实 provider 的实际模型
2. Text Chat 实测结果
3. STT 三类样例识别结果
4. TTS 人工试听结果
5. 至少 5 次 latency 数据与统计
6. End-to-End 是否成功
7. 全量 pytest 结果
8. 微信真机人工验证步骤/结果
9. 已知问题
10. 下一步建议，但不要自行开始后续 Roadmap
