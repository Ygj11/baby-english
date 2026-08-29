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
如果本机环境允许，Task 002 应安装并初始化 Context Hub，让 Codex 查询当前 Pipecat docs/examples/API，而不是依赖模型旧知识。

## 4. Node

```bash
node --version
npm --version
```

## 5. FFmpeg

```bash
ffmpeg -version
```

## 6. Environment

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

LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=

STT_PROVIDER=
STT_API_KEY=

TTS_PROVIDER=
TTS_API_KEY=
TTS_VOICE=

WECHAT_APP_ID=
WECHAT_APP_SECRET=
```

后续：

```text
XF_APP_ID=
XF_API_KEY=
XF_API_SECRET=

DATABASE_URL=
```

## 7. 用户开工步骤

1. 创建 GitHub private repo
2. clone 到 Mac
3. 把本开工包内容复制到 repo 根目录
4. commit
5. 从 `tasks/001-*.md` 开始交给 Codex

## 8. Secret

不要把生产 secret 粘进 Codex task。

真实 integration test 通过本地 `.env` 提供。


## 9. WeChat Developer Tool Local API

本地开发时，小程序是否能访问 `localhost` / LAN API 取决于开发者工具和设备环境。

开发阶段应：

- Base URL 集中配置；
- 必要时在开发者工具关闭“校验合法域名”；
- 真机测试使用可访问的 LAN IP 或 HTTPS 测试域名；
- 正式发布时配置微信后台 request/upload/download/socket 合法域名。

不要用浏览器 CORS 问题替代微信小程序的域名配置问题。
