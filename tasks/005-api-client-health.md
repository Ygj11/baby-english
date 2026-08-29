# TASK 005 — MiniProgram API Client + Health

## Goal

建立小程序到 FastAPI 的最小通信能力。

## Allowed Changes

```text
miniprogram/services/api.js
miniprogram/pages/home/**
miniprogram/app.js
miniprogram/config/**
server/app/main.py（仅 health 相关最小修正）
server/tests/**
.env.example
README.md（仅本地联调说明）
docs/API_CONTRACT.md（仅实际差异）
```

## Implementation

创建：

```text
services/api.js
```

至少支持：

```text
get(path)
post(path, body)
upload(path, file)
```

要求：

- Base URL 集中配置
- 页面不重复直接写 `wx.request`
- 非 2xx 统一处理
- raw backend error 不直接给儿童

Home development 状态显示：

```text
Backend: connected / unavailable
```

## WeChat Local Development

不要把浏览器 CORS 当作小程序主要网络问题。

需要明确：

- 微信开发者工具本地开发 Base URL；
- 必要时开发者工具关闭合法域名校验；
- 真机如何访问 Mac（LAN IP 或 HTTPS 测试地址）；
- 正式环境需要微信后台合法域名。

不要为了本 task 给 FastAPI 添加没有必要的宽松 `*` CORS。

## Acceptance

Home 请求：

```text
GET /api/health
```

成功：

```text
connected
```

Backend 停止：

```text
unavailable
```

页面不 crash。

## Tests

```bash
uv run pytest
```

## Do Not

- 不实现 auth
- 不实现 retry framework
- 不实现 chat
- 不引入 Axios
- 不加入无必要 CORS 中间件
