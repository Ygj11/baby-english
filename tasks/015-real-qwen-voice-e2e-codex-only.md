# TASK 015 — Real Qwen Voice E2E (Codex Only)

## Goal

完成并自动验证第一版真实 Voice Backend 闭环：

```text
Qwen Audio STT
qwen-audio-3.0-asr-flash
↓
Child Tutor
↓
Qwen LLM
qwen3.7-flash
↓
Qwen Audio TTS
qwen-audio-3.0-tts-flash
↓
TemporaryMediaStore
↓
/api/voice/media/{media_id}
```

本 Task 只包含 Codex 能通过：

- 源码
- CLI
- pytest
- HTTP
- 真实 Provider API
- 本地文件
- 日志

直接执行和验证的工作。

不包含任何：

- 微信扫码
- 真机调试
- 麦克风授权
- 人工试听
- 视觉/UI 主观验收
- 手机网络配置

---

## Required Context

执行前阅读：

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/PROVIDER_DECISION.md`
- `docs/PROVIDER_STRATEGY.md`
- `docs/PRIVACY_SECURITY.md`
- `docs/TEST_PLAN.md`
- 本 Task

---

## Preconditions

以下能力必须已经存在：

- Qwen LLM adapter
- Qwen Audio STT adapter
- Qwen Audio TTS adapter
- `LLMGateway`
- `STTGateway`
- `TTSGateway`
- `/api/voice/turn`
- `/api/voice/media/{media_id}`
- TemporaryMediaStore
- Child Tutor
- FakeLLM / FakeSTT / FakeTTS

如果 Qwen LLM 或 Qwen TTS adapter 尚未完成，可以在本 Task 内补齐最小实现，但：

- 不得绕过现有 Gateway；
- 不得创建第二条 Voice API；
- 不得重构总体架构。

---

## Default Provider Configuration

默认真实 Voice MVP：

```env
APP_ENV=development

DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing

LLM_PROVIDER=qwen
LLM_MODEL=qwen3.7-flash
LLM_TIMEOUT=60

STT_PROVIDER=qwen_audio
STT_MODEL=qwen-audio-3.0-asr-flash
STT_LANGUAGE_HINTS=zh,en
STT_TIMEOUT=60

TTS_PROVIDER=qwen_audio
TTS_MODEL=qwen-audio-3.0-tts-flash
TTS_SPEED=0.9
TTS_TIMEOUT=60
```

真实 Key 只从本地 `.env` 读取。

禁止把真实 secret 写入：

- 源码
- Markdown
- pytest fixture
- snapshot
- log
- completion report

---

## DeepSeek Position

现有 DeepSeek V4 Pro adapter：

```text
deepseek-v4-pro
```

继续保留，定位为未来高级/复杂任务模型。

本 Task：

- 不删除 DeepSeek；
- 不将 DeepSeek 作为默认 Tutor LLM；
- 不实现自动 fallback；
- 不实现模型路由；
- 不做 A/B。

---

## MiniMax Position

现有 MiniMax adapter 可以保留。

本 Task：

- 不删除；
- 不继续处理 MiniMax 余额问题；
- 不作为默认 TTS；
- 不纳入成功条件。

---

# 1. Runtime Factory Verification

确认当前真实配置下：

```text
create_llm() → Qwen LLM adapter
create_stt() → QwenAudioSTT
create_tts() → Qwen Audio TTS adapter
```

测试要求：

- fake 配置仍返回 Fake Provider；
- qwen 配置返回真实 Qwen adapter；
- production 环境禁止 Fake 的规则继续生效；
- 缺少真实 Provider 必要配置时明确 configuration error。

---

# 2. Real Qwen LLM Integration

使用 opt-in 真实测试验证：

```text
qwen3.7-flash
```

输入建议：

```text
苹果英文怎么说？
```

要求：

- 真实网络调用成功；
- 返回非空 reply；
- 不是 Fake 固定文本；
- Child Tutor system prompt 实际进入 LLM；
- provider 原始错误不暴露给 API client。

真实测试必须：

```text
RUN_REAL_PROVIDER_TESTS=1
```

才能执行。

默认 pytest 不访问真实 API。

---

# 3. Real Qwen STT Integration

使用本地真实音频文件测试：

```text
REAL_STT_AUDIO_PATH=/tmp/baby-english-stt-test.wav
```

至少支持当前项目真实主路径：

```text
WAV / MP3
```

测试内容可使用：

```text
香蕉英文怎么说
```

要求：

- Qwen STT 真实网络调用成功；
- 返回非空 transcript；
- duration 正常解析；
- 原始测试音频不复制到 repo；
- 原始音频内容不写日志。

如果测试文件不存在：

- 明确 skip 或报告缺少测试资源；
- 不伪造成功。

---

# 4. Real Qwen TTS Integration

使用：

```text
qwen-audio-3.0-tts-flash
```

输入：

```text
Banana. Repeat after me: banana.
```

要求：

- 真实网络调用成功；
- 返回非空音频 bytes；
- content type 与实际输出格式一致；
- extension 与实际输出格式一致；
- 不返回 provider URL 给 API client；
- provider raw response 不写入日志。

真实 integration test 应验证音频至少满足：

- bytes 非空；
- 长度明显大于空壳 header；
- 可被现有 TemporaryMediaStore 保存和读取。

不要求 Codex 人工听音质。

---

# 5. Real `/api/tutor/chat`

启动真实配置 Backend，使用 HTTP 调用：

```text
POST /api/tutor/chat
```

输入：

```text
苹果英文怎么说？
```

验证：

- HTTP 200；
- reply 非 Fake 固定回复；
- Child Tutor prompt 生效；
- suggested_actions 符合 API contract；
- response 不包含 Provider secret/raw response。

---

# 6. Real `/api/voice/turn` E2E

使用本地真实音频文件，通过 HTTP 调用：

```text
POST /api/voice/turn
```

完整真实链：

```text
audio upload
↓
Qwen STT
↓
Child Tutor
↓
Qwen LLM
↓
Qwen TTS
↓
TemporaryMediaStore
```

验证：

```text
HTTP 200
```

响应至少包含：

```text
transcript
reply
audio_url / media_url
suggested_actions
```

具体字段名称以当前 `docs/API_CONTRACT.md` 为准。

要求：

- transcript 非 Fake 固定文本；
- reply 非 Fake 固定文本；
- media URL 为项目自己的 endpoint；
- 不返回 DashScope URL；
- 不返回 base64 音频；
- suggested actions 与当前 reply 一致。

---

# 7. Real Media Endpoint

从 `/api/voice/turn` 得到真实 media URL 后：

```text
GET /api/voice/media/{media_id}
```

验证：

- HTTP 200；
- content type 正确；
- body 非空；
- body 与 TTS 生成格式一致。

继续验证现有 TTL 行为：

- 未过期 media 可读；
- cleanup 后不可继续永久读取。

不为了本 Task 引入 Redis / Object Storage。

---

# 8. Input Audio Cleanup

真实 `/api/voice/turn` 成功和失败路径都检查：

```text
上传的儿童音频临时文件
```

必须：

- 成功后删除；
- STT 失败后删除；
- LLM 失败后删除；
- TTS 失败后删除。

不得在测试完成后遗留真实录音临时文件。

---

# 9. Provider Error Logging

确保 Server 能区分失败阶段：

```text
STT
LLM
TTS
```

安全日志允许记录：

```text
provider stage
HTTP status/category
provider error code（如果安全）
exception class
request id（如果安全）
```

禁止记录：

```text
API Key
Authorization header
原始音频
完整 provider response
不必要的儿童内容
```

用户/API client 只看到已有安全错误，不暴露 provider raw message。

---

# 10. Latency Observation

为真实：

```text
POST /api/voice/turn
```

记录：

```text
stt_ms
llm_ms
tts_ms
total_ms
```

使用现有 logging / timing 即可。

不要引入：

- OpenTelemetry
- Prometheus
- tracing platform
- observability SaaS

执行至少 5 次真实短音频 turn。

输出：

```text
min
median
max
```

分别针对：

- STT
- LLM
- TTS
- total

这是观察数据，不作为 CI 强制性能阈值。

若 total 明显高于约 10 秒：

- 在 completion report 指出主要耗时阶段；
- 不在本 Task 自动更换模型或建设性能平台。

---

# 11. Default Automated Test Suite

执行：

```bash
uv sync
uv run pytest
```

要求：

- 默认测试完全离线；
- 不消耗真实 API；
- Fake Provider 测试继续通过；
- Qwen adapter 使用 mock 测试；
- 现有 Voice Loop 测试无回归；
- production 禁止 Fake 的测试无回归。

---

# 12. Opt-in Real Provider Tests

真实 Provider 测试必须显式 opt-in，例如：

```bash
RUN_REAL_PROVIDER_TESTS=1 \
REAL_STT_AUDIO_PATH=/tmp/baby-english-stt-test.wav \
uv run --env-file .env pytest -m real_provider
```

要求：

- 未设置 `RUN_REAL_PROVIDER_TESTS=1` → skip；
- 缺少真实 Key → skip 或明确配置错误；
- 不影响普通 CI；
- 不把真实 Key 写入 pytest output。

---

# 13. Security / Repository Check

执行：

```bash
git status
git diff --check
```

检查项目中不存在：

```text
.env
真实 API Key
Authorization header dump
原始测试录音
生成的真实 TTS 音频
provider raw response dump
大型临时 binary fixture
```

如需 `git diff` / grep 扫描 secret，只做本地检查，不修改 remote。

---

## Do Not

本 Task 禁止：

- 微信扫码
- 微信真机调试
- 手机麦克风测试
- 人工试听
- UI 视觉验收
- 修改手机/局域网配置
- realtime Pipecat
- WebSocket/WebRTC
- 微信登录
- 场景英语
- pronunciation / ISE
- Vision
- Textbook/RAG
- Payment
- 数据库 memory
- 模型自动路由
- 自动 fallback
- A/B
- 删除 DeepSeek adapter
- 删除 MiniMax adapter
- 引入新的核心框架
- 执行 `git push`
- 修改 Git remote
- 默认创建 commit
- 开始 TASK 015 之后的 Roadmap

---

## Codex Definition of Done

Codex 只有在以下全部完成后，才标记 TASK 015 完成：

- [ ] Qwen LLM runtime factory 正确
- [ ] Qwen STT runtime factory 正确
- [ ] Qwen TTS runtime factory 正确
- [ ] Qwen LLM real integration 成功
- [ ] Qwen STT real integration 成功
- [ ] Qwen TTS real integration 成功
- [ ] `/api/tutor/chat` 真实 HTTP 验证成功
- [ ] `/api/voice/turn` 真实三 Provider E2E 成功
- [ ] media endpoint 真实音频读取成功
- [ ] Child Tutor 在真实 LLM 中生效
- [ ] input audio cleanup 成功/失败路径无回归
- [ ] media TTL 无回归
- [ ] provider failure 日志可定位且安全
- [ ] 默认 `uv run pytest` 全部通过
- [ ] real provider tests 保持 opt-in
- [ ] 至少 5 次真实 turn latency 已统计
- [ ] repository secret/binary 检查通过
- [ ] 未开始后续 Roadmap

---

## Completion Report

完成后只报告 Codex 实际执行并验证的结果：

1. 当前默认 Provider
2. 实际模型名称
3. Qwen LLM real integration 结果
4. Qwen STT real integration transcript
5. Qwen TTS real integration 结果：
   - content type
   - byte length
6. `/api/tutor/chat` HTTP 实测结果
7. `/api/voice/turn` HTTP 实测结果
8. media endpoint 实测结果
9. 5 次 latency：
   - STT min/median/max
   - LLM min/median/max
   - TTS min/median/max
   - total min/median/max
10. `uv run pytest` 最终结果
11. cleanup/security 检查结果
12. 修改文件清单
13. 已知技术限制
14. 阻塞项（如有）

完成后停止。
