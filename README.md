# Baby English — AI 英语陪读微信小程序

这是一个面向中国小学阶段儿童的 AI 英语陪读项目。

## 产品核心

第一阶段优先验证：

```text
孩子在微信小程序说一句话
↓
语音识别
↓
儿童 Tutor
↓
LLM
↓
TTS
↓
小程序播放回答
```

核心入口：

1. AI 陪聊
2. 拍一拍
3. 我的课本
4. 场景英语
5. 英语故事

## 技术基线

- 后端：Python + FastAPI
- Voice Agent：Pipecat（dependency，不 Fork 框架源码）
- Python 包管理：uv
- 小程序：微信原生 MiniProgram
- UI：TDesign MiniProgram
- 教材 RAG：LlamaIndex
- 发音评测：讯飞 ISE（后续）
- 支付：wechatpayv3（后续）
- 英语学习业务参考：Spoken（MIT source donor）
- 微信能力参考：微信官方 miniprogram-demo
- Voice/Tutor 示例参考：pipecat-examples

## Codex 使用顺序

请依次阅读：

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/PROVIDER_STRATEGY.md`
5. `docs/PRIVACY_SECURITY.md`
6. 当前要执行的 `tasks/NNN-*.md`

每次只执行一个 task。

推荐：

```text
完成 task
↓
跑测试
↓
人工检查 diff
↓
commit / PR
↓
进入下一个 task
```

## 第一批任务

- `tasks/001-bootstrap-repository.md`
- `tasks/002-pipecat-foundation.md`
- `tasks/003-miniprogram-init.md`
- `tasks/004-tdesign-ui-foundation.md`
- `tasks/005-api-client-health.md`
- `tasks/006-text-chat-mvp.md`
- `tasks/007-child-tutor.md`
- `tasks/008-recorder-ui.md`
- `tasks/009-audio-upload-stt.md`
- `tasks/010-voice-loop.md`

目标不是“代码全是自己的”，而是：

> 产品逻辑自己掌握，基础设施尽可能来自成熟开源生态。

## 本地启动

```bash
uv sync
uv run uvicorn server.app.main:app --reload
```

Pipecat 作为当前项目的 core dependency 管理，不使用 scaffold 重建项目。验证安装：

```bash
uv run python -c "import pipecat; print('pipecat import ok')"
```
