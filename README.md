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

`🎭 场景英语` 当前提供餐厅、学校、儿童商店和旅行问路四个服务端场景。进行中的
场景在 Backend 临时保存文字对话以支持多轮记忆；完成评估后只保留结构化目标进度
与简短总结，并删除原始场景对话。

`📷 拍一拍` 当前支持相机/相册单图 Photo English：Backend 验证并去除图片元数据，
用 Qwen Vision 生成一个儿童安全的小课程，只保存规范化单词、例句与练习短语，
不保存原图、缩略图、EXIF、OCR 或 provider 原始响应。

`📖 我的课本` 当前提供服务端安装的教材目录、Unit 选择和 grounded QA。教材由 owner
以 repo 外的 `manifest.json + content.jsonl` 包通过 CLI 导入；LlamaIndex 使用
`SentenceSplitter(384/48)`、Qwen `qwen3.7-text-embedding` 1024 维向量和本地持久化
索引检索，现有 `LLMGateway` 只依据取回的有限上下文生成短答案。仓库不包含真实教材正文。

## 技术基线

- 后端：Python + FastAPI
- Voice Agent：Pipecat（dependency，不 Fork 框架源码）
- Python 包管理：uv
- 小程序：微信原生 MiniProgram
- UI：TDesign MiniProgram
- 教材 RAG：LlamaIndex
- 发音评测：讯飞流式 ISE（独立 PronunciationGateway）
- 图片理解：Qwen `qwen3.7-flash`（独立 VisionGateway，严格结构化输出）
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
uv run --env-file .env alembic upgrade head
uv run uvicorn server.app.main:app --reload
```

使用本地 `.env` 中的真实 Qwen Provider 配置启动：

```bash
uv run --env-file .env alembic upgrade head
uv run --env-file .env uvicorn server.app.main:app --reload
```

发音练习默认使用离线 `FakePronunciationGateway`。真实讯飞 ISE 仅在后端 `.env` 配置
`ISE_PROVIDER=xunfei` 及 `XFYUN_APP_ID`、`XFYUN_API_KEY`、`XFYUN_API_SECRET`
后启用；小程序不会持有这些凭据。首次启动及新增 migration 后都需先执行 Alembic
`upgrade head`。

Photo English 默认复用 `.env` 中的 `DASHSCOPE_API_KEY`、北京 Workspace，并使用
`VISION_PROVIDER=qwen`、`VISION_MODEL=qwen3.7-flash`。开发或离线测试可显式设为
`VISION_PROVIDER=fake`；production 禁止 Fake provider。

教材导入同样复用北京 Workspace。先准备 repo 外的授权结构化教材包，再运行：

```bash
uv run --env-file .env python -m server.app.textbook.ingest /absolute/path/outside/repo/textbook-package
```

索引写入 Git 忽略的 `.data/textbook_indexes/`；其中包含教材 chunks 和 embeddings，应按
受保护的服务端运行数据管理。导入时教材块会发送给百炼 Embedding API，问答时只有命中的
有界上下文会发送给当前 Qwen LLM。

Pipecat 作为当前项目的 core dependency 管理，不使用 scaffold 重建项目。验证安装：

```bash
uv run python -c "import pipecat; print('pipecat import ok')"
```

## 微信开发者工具

首次打开小程序前，复制本地项目配置：

```bash
cp miniprogram/project.config.json.example miniprogram/project.config.json
```

然后在微信开发者工具中导入 `miniprogram/` 目录。示例配置使用 `touristappid`，真实 AppID 只填写在已被 Git 忽略的 `project.config.json` 中。

安装 TDesign MiniProgram：

```bash
cd miniprogram
npm install
```

安装完成后，在微信开发者工具中选择“工具 → 构建 npm”，再编译小程序。

### 本地 API 联调

小程序开发环境的 Base URL 集中配置在 `miniprogram/config/api.js`，默认连接 `http://127.0.0.1:8000`。启动后端：

```bash
uv run uvicorn server.app.main:app --reload
```

- 微信开发者工具联调 localhost 时，必要时在“详情 → 本地设置”关闭合法域名校验。
- 真机不能使用 Mac 的 `127.0.0.1`，需要把本地配置改为手机可访问的 Mac LAN IP，或使用 HTTPS 测试地址。
- 正式环境必须在微信后台配置 request/upload/download/socket 合法域名，并使用 HTTPS 地址。
