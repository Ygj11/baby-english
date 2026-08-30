# TASK 011 — Audit Fix / Milestone 2.1

## Goal

在接入真实 LLM / STT / TTS provider 之前，修复 Milestone 2 源码审计中发现的几个明确问题，并让微信原生 MiniProgram 可以稳定构建 TDesign npm 组件。

本 task 只做“审计修复”，不接真实 provider，不进入后续产品 Roadmap。

---

## Required Context

执行前阅读：

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/API_CONTRACT.md`
- `docs/PROVIDER_STRATEGY.md`
- `docs/PRIVACY_SECURITY.md`
- `docs/TEST_PLAN.md`
- 本 task

---

## Scope Rule

本 task 中列出的文件是主要范围，不是绝对文件白名单。

如果为了完成本 task 必须修改少量相邻配置、注册、测试或依赖文件，可以直接修改，但：

1. 必须直接服务于本 task；
2. 不得接入真实 LLM / STT / TTS；
3. 不得引入新的核心框架；
4. 不得开始微信登录、场景英语、ISE、Vision、Textbook、Payment；
5. 最终报告中说明额外修改文件及原因。

---

# Fix 1 — TDesign npm 构建基线

## Problem

MiniProgram 已通过 npm 安装 `tdesign-miniprogram`，但微信开发者工具在未构建 npm 时无法解析：

```text
tdesign-miniprogram/cell/cell
```

开发者工具会尝试寻找：

```text
miniprogram_npm/tdesign-miniprogram/...
```

当前构建环境需要明确、可重复的 npm 安装与“构建 npm”流程。

## Requirements

1. 保留：

```text
miniprogram/package.json
miniprogram/package-lock.json
```

2. `node_modules/` 保持 git ignore，但本地安装后不要在任务结束时主动删除。
3. 将生成的 `miniprogram_npm/` 视为构建产物，不作为源码手工维护。
4. `.gitignore` 应忽略：

```text
miniprogram/miniprogram_npm/
```

5. README / SETUP 中明确本地首次运行步骤：

```bash
cd miniprogram
npm install
```

然后在微信开发者工具：

```text
菜单栏 → 工具 → 构建 npm
```

6. 验证当前 `usingComponents` 路径与安装的 TDesign 版本一致。
7. 不复制 TDesign 源码进入仓库。

---

# Fix 2 — Suggested Actions 语义正确

## Problem A

后端返回：

```text
listen
repeat
explain_zh
```

但 MiniProgram 当前只实现：

```text
listen
repeat
```

`explain_zh` 按钮存在但点击无行为。

## Requirement

`explain_zh` 必须有真实、可测试的行为。

推荐实现：

- 将当前最后一个 AI 回复作为上下文；
- 向已有 `/api/tutor/chat` 发起一个明确的“用简短中文解释刚才内容”请求；
- 或在 Tutor API 中增加最小 action-aware 输入。

选择最简单、最清晰的方案。

不得：

- 在前端硬编码中文解释；
- 根据 AI 文本内容猜语义；
- 引入新 Agent Framework。

---

## Problem B

Text Chat 返回 `listen`，但 text chat 本身没有生成对应 TTS。

这可能导致点击“再听”时重播上一次 voice turn 的旧音频。

## Requirement

必须消除 stale-audio 行为。

优先方案：

### Option A — MVP 最小修复

Text Chat 暂时不返回 `listen`，只在存在当前 reply 对应音频时显示 `listen`。

### Option B — 如果实现足够小

实现当前 API contract 中已有的：

```text
POST /api/voice/speak
```

让 Text Chat 的当前 reply 生成对应 TTS，并绑定新的 audio URL。

本 task 默认优先 Option A，除非 Option B 能在不扩大 scope 的情况下干净完成。

无论选择哪种方案：

- `listen` 只能播放“当前回复”对应音频；
- 不得重播旧 reply 的音频。

---

# Fix 3 — API Contract 与代码一致

检查并统一：

- `/api/tutor/chat`
- `/api/voice/transcribe`
- `/api/voice/turn`
- `/api/voice/media/{media_id}`
- `/api/voice/speak`（如果本 task 实际实现）

重点修复：

1. `audio_url` 示例路径必须与真实代码一致：
   ```text
   /api/voice/media/{media_id}
   ```
2. `suggested_actions` 示例必须与实际语义一致。
3. 未实现的 endpoint 不应在文档中伪装成已经可用。
4. API 文档不得描述 provider-specific 数据。

---

# Fix 4 — Fake Provider Production Fail-Safe

## Problem

当前未配置 provider 时：

```text
FakeLLM
FakeSTT
FakeTTS
```

会自动启用。

开发阶段很好，但生产环境如果漏配 provider，产品会无声地运行 Fake。

## Requirements

引入明确环境：

```text
APP_ENV=development
```

至少支持：

```text
development
test
production
```

规则：

```text
development / test
→ Fake provider allowed

production
→ Fake provider forbidden
→ provider 为空或 fake 时必须明确失败
```

实现应简单。

不要引入大型 Settings Framework，除非项目已经使用。

`.env.example` 更新：

```text
APP_ENV=development
```

测试至少验证：

- development + empty provider → Fake allowed
- test + fake → Fake allowed
- production + empty provider → configuration error
- production + fake → configuration error

LLM / STT / TTS 三者行为保持一致。

---

# Fix 5 — 输入验证

为第一阶段 API 增加最小合理验证。

## Chat

`message`：

- trim 后不能为空；
- 设置合理最大长度，例如 1000–2000 字符；
- 超限返回 422/4xx，不进入 LLM。

`student.age`：

- 合理儿童范围，例如 5–15。

`student.grade`：

- 合理小学/早期学习范围，例如 1–9。

`context.mode`：

- 当前至少限制为已知 mode，或在当前未实际使用时移除不必要自由字符串。

## Voice Turn

`age`、`grade` 使用与 Chat 一致的规则。

不要为了本 task 建数据库 StudentProfile。

---

# Fix 6 — MiniProgram 本地状态安全

检查 Chat 页面：

1. Text Chat 新回复后，不得保留与旧 voice reply 错误绑定的 audio 状态。
2. Voice Turn 成功后，`listen` 应播放当前 voice reply。
3. 页面 unload：
   - recorder listeners cleanup；
   - audio player cleanup。
4. `explain_zh` loading / error 不得破坏正常 Chat 状态。
5. 所有用户可见错误保持儿童友好，不显示 raw backend/provider error。

---

# Fix 7 — Build/Test 基线

## Backend

运行：

```bash
uv sync
uv run pytest
```

新增测试覆盖：

- production fake-provider fail-safe
- chat empty message
- invalid age / grade
- API contract action behavior
- explain_zh orchestration
- stale audio prevention 对应的 service/API 行为（可在前端静态/mock 层验证）

## MiniProgram

至少验证：

```bash
cd miniprogram
npm install
```

并进行：

- JSON syntax check
- JS syntax check
- usingComponents 路径检查

不要在任务结束时删除 `node_modules/`。

---

# Manual WeChat DevTools Smoke Test

Codex 无法完成 GUI 时，列出人工步骤。

Repository owner 应验证：

1. `npm install`
2. 微信开发者工具：
   ```text
   工具 → 构建 npm
   ```
3. 确认生成：
   ```text
   miniprogram_npm/tdesign-miniprogram/
   ```
4. 编译 Home 页面，无 `tdesign-miniprogram/cell/cell` 找不到组件错误。
5. 进入 Chat。
6. Text Chat：
   - 发送消息；
   - 不出现 stale “再听”；
   - `中文讲讲` 可工作。
7. Voice：
   - Fake voice turn 仍能完成；
   - “再听”只播放当前 voice reply。
8. 拒绝麦克风权限 / 停止后端：
   - 页面可恢复；
   - 不显示 raw error。

---

# Do Not

- 不接真实 LLM
- 不接真实 STT
- 不接真实 TTS
- 不做 realtime Pipecat
- 不做 WebSocket/WebRTC
- 不做微信登录
- 不做场景英语
- 不做 ISE
- 不做 Vision
- 不做 Textbook/RAG
- 不做 Payment
- 不做数据库重构
- 不执行 `git push`
- 不修改 Git remote
- 默认不创建 commit

---

# Definition of Done

- [ ] 微信开发者工具可通过构建 npm 正确解析 TDesign
- [ ] `miniprogram_npm/` 为可再生构建产物
- [ ] 不再清理正常 `node_modules/`
- [ ] `explain_zh` 有真实行为
- [ ] Text Chat 不会重播旧 Voice 音频
- [ ] API contract 与真实源码一致
- [ ] production 禁止 Fake provider
- [ ] Chat / Voice 基础输入验证存在
- [ ] 原 007–010 Fake Voice Loop 无回归
- [ ] `uv run pytest` 全部通过
- [ ] MiniProgram 静态检查通过
- [ ] 未接真实 provider
- [ ] 未进入后续 Roadmap

---

# Completion Report

完成后输出：

1. 修改摘要
2. 修改文件清单
3. 每个 Audit Fix 的处理方式
4. Backend 测试结果
5. MiniProgram/npm 验证结果
6. 微信开发者工具人工 smoke test 步骤
7. 仍存在的已知限制
8. 是否存在阻塞项
