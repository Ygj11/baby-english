# AUDIT.md — 开工文档包审计结论

审计日期：2026-08-29

## 结论

整体产品方向、技术边界和 Codex task 拆分没有跑偏。

但 V1 有几处工程细节需要修正后再作为 Codex 的正式施工基线：

1. 明确 Pipecat 的职责：
   - Pipecat 是实时 Voice Agent / frame pipeline 核心依赖；
   - 不强迫“一句录音 HTTP 上传”这种 batch API 通过 Pipecat FrameProcessor 绕一圈；
   - batch STT/TTS 使用极薄 Gateway；如果某 Pipecat service 提供自然的 batch 接口可直接复用，否则使用官方 provider SDK；
   - 后续实时语音必须优先使用 Pipecat pipeline/transport。

2. Pipecat CLI：
   - 官方当前支持 `pipecat init --output`；
   - `pipecat init` 会生成官方 coding-agent guidance；
   - 不覆盖本项目 `AGENTS.md`；
   - Task 002 使用临时 scaffold 对照当前官方模式。

3. Codex / Pipecat Context：
   - Pipecat 官方推荐 coding agents 使用 Context Hub；
   - Task 002 增加可选但强烈推荐的 Context Hub 安装步骤。

4. 微信小程序联调：
   - `wx.request` 不是浏览器 fetch，不应把 CORS 当主要联调问题；
   - 真正需要关注的是微信开发者工具的“不校验合法域名”开发设置、真实设备的 HTTPS/合法域名、Base URL 配置；
   - Task 005 已修正。

5. Provider 决策：
   - Codex 不得自行替项目决定收费 STT/LLM/TTS 厂商；
   - 新增 `PROVIDER_STRATEGY.md`；
   - Fake provider 用于自动测试；
   - 真实 provider 由环境变量和项目 owner 决定。

6. 儿童数据：
   - 在真正上传音频/图片前必须明确最小化与临时数据策略；
   - 新增 `PRIVACY_SECURITY.md`。

## 保持不变的核心选型

- 母项目：自建 private repo
- Backend：FastAPI
- Voice Agent：Pipecat dependency
- Python：uv
- MiniProgram：微信原生
- UI：TDesign MiniProgram
- RAG：LlamaIndex
- Source donors：
  - pipecat-examples
  - Spoken
  - 微信官方 miniprogram-demo

## 不进入当前核心架构

- Dify
- FastGPT
- TEN
- LiveKit
- uni-app
- Flutter
- Taro
- RAGFlow（MVP 阶段）

## 审计后的开发原则

产品 Backend 可以拥有自己的 REST API 和业务结构。

Pipecat 不应反客为主成为整个业务 Backend。

正确关系：

```text
Baby English Application
├── FastAPI REST / business API
├── Tutor
├── Textbook
├── Vision
├── WeChat
└── Voice
    ├── BatchVoiceGateway (MVP)
    └── PipecatRealtimeAgent (later/realtime)
```

这样既不会为了框架而框架，也保留未来实时语音能力。
