# TASK 012 — Real LLM: DeepSeek V4 Pro

## Goal

在不破坏现有 `FakeLLM` 测试基线的前提下，为现有 `LLMGateway` 接入 repository owner 已选择的 DeepSeek OpenAI-compatible API。

完成后：

```text
/api/tutor/chat
/api/voice/turn
```

在配置真实 LLM provider 时使用 DeepSeek。

---

## Preconditions

- TASK 011 Audit Fix 已完成并测试通过。
- 阅读：
  - `AGENTS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/PROVIDER_DECISION.md`
  - `docs/PROVIDER_STRATEGY.md`
  - `docs/PRIVACY_SECURITY.md`
  - 本 task
- 现有 FakeLLM 测试必须继续可用。

---

## Owner-selected Configuration

使用：

```env
LLM_PROVIDER=openai_compatible

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro
OPENAI_TIMEOUT=1800
```

`OPENAI_TIMEOUT=1800` 为 owner 明确选择，不得自行修改。

---

## Implementation

1. 通过 `uv` 增加正式 runtime dependency：
   ```text
   openai
   ```
2. 在现有 `server/app/tutor/llm.py` 或等价最小模块中实现：
   ```text
   OpenAICompatibleLLM
   ```
3. 使用官方 `AsyncOpenAI`。
4. 调用 OpenAI-compatible chat API。
5. 将：
   ```text
   system_prompt
   message
   ```
   映射为 system/user messages。
6. 正常返回 assistant 文本。
7. provider timeout、network error、invalid response、authentication error 等统一转换为现有 `LLMError`。
8. 不向前端返回 DeepSeek raw error。
9. 不改变 Child Tutor prompt 逻辑。
10. `create_llm()`：
    - `fake` → FakeLLM
    - `openai_compatible` → OpenAICompatibleLLM
    - 未知 provider → configuration error
11. real provider 被选择但缺少：
    - API Key
    - Base URL
    - Model
    时必须明确 configuration error。
12. 更新 `.env.example`，Key 留空。

---

## Tests

普通 pytest 必须完全离线。

至少测试：

- factory 选择 real adapter；
- 环境变量映射；
- system/user message mapping；
- mock OpenAI response → reply；
- timeout → `LLMError`；
- auth/provider error → `LLMError`；
- 缺少配置 → configuration error；
- FakeLLM 原测试无回归；
- Child Tutor prompt 仍进入 LLM。

不得在普通 pytest 消耗真实 API。

---

## Optional Real Integration

如果本地 `.env` 已有真实 `OPENAI_API_KEY`，提供 opt-in 验证方式，例如：

```bash
RUN_REAL_PROVIDER_TESTS=1 uv run pytest -m real_provider -k deepseek
```

或等价独立 script。

真实测试输入建议：

```text
苹果英文怎么说？
```

要求：

- 返回非空文本；
- 不检查随机生成的精确句子；
- 不输出 API Key；
- 不将真实 integration 纳入默认 CI。

---

## Do Not

- 不接 STT
- 不接 TTS
- 不修改 Pipecat realtime
- 不实现 streaming chat
- 不加入 memory/database
- 不改变 provider 选择
- 不改变 `OPENAI_TIMEOUT=1800`
- 不执行 git push
- 不开始 TASK 013

---

## Verification

```bash
uv sync
uv run pytest
```

若存在 opt-in real test，在 owner 配置 Key 后额外执行。

---

## Definition of Done

- [ ] DeepSeek real LLM adapter 已存在
- [ ] `deepseek-v4-pro` 由 env 配置
- [ ] Child Tutor 继续生效
- [ ] FakeLLM 继续工作
- [ ] 默认 pytest 不访问网络
- [ ] provider error 不泄露 raw response
- [ ] `.env.example` 无真实 secret
- [ ] 全量测试通过
