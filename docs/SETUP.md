# SETUP.md

## 1. Mac 基础工具

建议：

- Git
- Python 3.11+
- uv
- Node.js 18+
- npm
- FFmpeg
- 微信开发者工具

## 2. uv

确认：

```bash
uv --version
```

如未安装，使用 uv 官方当前安装方式。

## 3. Pipecat CLI / Codex Context

Task 002 处理。

执行前：

```bash
pipecat --version
pipecat --help
pipecat init --help
```

不要猜 CLI flags。

Pipecat 官方当前也推荐 coding agents 使用 Pipecat Context Hub。
如果本机已经安装，则 Task 002 直接使用；索引未完成不阻塞 Task 002。

本项目已经有自己的母仓库和 `AGENTS.md`，因此不要在 `baby-english` 根目录执行：

```bash
pipecat init .
```

Task 002 只把 `pipecat-ai` 作为项目 dependency 接入。
如确实需要观察 Pipecat 官方 scaffold，只能在 repo 外临时目录按需生成。

## 4. Node

```bash
node --version
npm --version
```

## 5. FFmpeg

```bash
ffmpeg -version
```

## 6. MiniProgram 首次运行

安装并保留本地 npm 依赖：

```bash
cd miniprogram
npm install
```

然后在微信开发者工具中导入 `miniprogram/`，选择：

```text
菜单栏 → 工具 → 构建 npm
```

构建生成的 `miniprogram/miniprogram_npm/` 是可再生构建产物，不作为源码维护。

## 7. Environment

仓库提供：

```text
.env.example
```

开发者创建：

```text
.env
```

`.env` 不提交。

推荐变量：

```text
APP_ENV=development

DATABASE_URL=sqlite+aiosqlite:///./baby_english.db

DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
DASHSCOPE_REGION=cn-beijing

LLM_PROVIDER=qwen
LLM_MODEL=qwen3.7-flash

STT_PROVIDER=qwen_audio
STT_MODEL=qwen-audio-3.0-asr-flash

TTS_PROVIDER=qwen_audio
TTS_MODEL=qwen-audio-3.0-tts-flash
TTS_VOICE=longanhuan_v3.6

EMBEDDING_PROVIDER=qwen
EMBEDDING_MODEL=qwen3.7-text-embedding
EMBEDDING_DIMENSIONS=1024
EMBEDDING_TIMEOUT=60
TEXTBOOK_INDEX_DIR=.data/textbook_indexes
TEXTBOOK_RETRIEVAL_TOP_K=4

ISE_PROVIDER=fake
XFYUN_APP_ID=
XFYUN_API_KEY=
XFYUN_API_SECRET=
ISE_TIMEOUT=60

WECHAT_APP_ID=
WECHAT_APP_SECRET=
```

真实发音评测将 `ISE_PROVIDER` 改为 `xunfei`。讯飞凭据只放在 Backend 本地
`.env`，不进入小程序、源码或日志。

## 8. Database Migration

首次启动和拉取新 migration 后执行：

```bash
uv run --env-file .env alembic upgrade head
```

本地默认 SQLite 文件不会提交。应用启动不会调用 `create_all()`，schema 只由 Alembic 管理。

## 9. Textbook Ingestion

教材 source package 必须由 owner 授权并保存在 repository 外，格式为一个
`manifest.json` 和 manifest 指向的 UTF-8 `content.jsonl`。完成 migration 后运行：

```bash
uv run --env-file .env python -m server.app.textbook.ingest /absolute/path/outside/repo/textbook-package
```

相同 fingerprint/config 会安全 no-op；变更会在临时目录构建、重载验证后替换既有索引。
`.data/textbook_indexes/` 含教材 chunks 与 embeddings，不提交、不公开下载并按受保护运行数据备份。
导入会把教材块发送给百炼 Embedding；QA 仅把 top-k 有界命中上下文发送给已有 Qwen LLM。

可选真实验证：

```bash
RUN_REAL_PROVIDER_TESTS=1 uv run --env-file .env pytest -m real_provider -k qwen_textbook_embedding -vv -s
RUN_REAL_PROVIDER_TESTS=1 uv run --env-file .env pytest -m real_provider -k textbook_rag_e2e -vv -s
```

## 10. 用户开工步骤

1. 创建 GitHub private repo
2. clone 到 Mac
3. 把本开工包内容复制到 repo 根目录
4. commit
5. 从 `tasks/001-*.md` 开始交给 Codex

## 11. Secret

不要把生产 secret 粘进 Codex task。

真实 integration test 通过本地 `.env` 提供。

启动真实 Qwen 配置 Backend：

```bash
uv run --env-file .env uvicorn server.app.main:app --reload
```

真实 Provider tests 必须显式 opt-in，并使用 repo 外的本地音频：

```bash
RUN_REAL_PROVIDER_TESTS=1 \
REAL_STT_AUDIO_PATH=/tmp/baby-english-stt-test.wav \
uv run --env-file .env pytest -m real_provider
```

真实讯飞 ISE 测试需要一份 repo 外的 16 kHz、单声道英文 MP3：

```bash
RUN_REAL_PROVIDER_TESTS=1 \
REAL_ISE_AUDIO_PATH=/absolute/path/to/english-reading.mp3 \
REAL_ISE_REFERENCE_TEXT="banana" \
uv run --env-file .env pytest -m real_provider -k xunfei_ise -vv -s
```


## 12. WeChat Developer Tool Local API

本地开发时，小程序是否能访问 `localhost` / LAN API 取决于开发者工具和设备环境。

开发阶段应：

- Base URL 集中配置；
- 必要时在开发者工具关闭“校验合法域名”；
- 真机测试使用可访问的 LAN IP 或 HTTPS 测试域名；
- 正式发布时配置微信后台 request/upload/download/socket 合法域名。

不要用浏览器 CORS 问题替代微信小程序的域名配置问题。
