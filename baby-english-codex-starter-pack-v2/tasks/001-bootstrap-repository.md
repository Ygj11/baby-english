# TASK 001 — Bootstrap Repository

## Goal

建立可持续开发的仓库基线，不实现产品功能。

## Preconditions

- 当前目录是用户新建的 `baby-english` private repo。
- 本文档包已经存在。
- macOS 已安装 Git。

## Allowed Changes

```text
pyproject.toml
uv.lock
.gitignore
.env.example
server/**
README.md（仅补充实际启动命令）
```

禁止修改：

```text
docs/PRODUCT.md
docs/ARCHITECTURE.md
tasks/002-* 及以后
```

## Implementation

1. 检查 repo 状态。
2. 如无 Python 项目，使用 `uv init`。
3. Python 最低版本 3.11。
4. 添加最小依赖：
   - fastapi
   - uvicorn
   - pytest
   - pytest-asyncio
   - httpx
5. 创建：
   ```text
   server/app/__init__.py
   server/app/main.py
   server/tests/
   ```
6. 创建 `GET /api/health`。
7. 新增 `.env.example`。
8. `.gitignore` 忽略：
   - `.env`
   - `.venv`
   - `__pycache__`
   - `.pytest_cache`
   - `.DS_Store`
9. 添加 health test。

## API

```json
{
  "status": "ok",
  "service": "baby-english"
}
```

## Do Not

- 不安装 Pipecat
- 不建数据库
- 不建用户系统
- 不建小程序
- 不实现 Chat
- 不引入 Docker

## Verification

```bash
uv sync
uv run pytest
uv run uvicorn server.app.main:app --reload
```

## Definition of Done

- [ ] `uv sync` 成功
- [ ] FastAPI 可启动
- [ ] `/api/health` 正确
- [ ] pytest 通过
- [ ] `.env` 不会提交
- [ ] 无产品业务代码

## Completion Report

输出：

1. 修改文件
2. 测试命令与结果
3. 启动命令
4. 阻塞项
