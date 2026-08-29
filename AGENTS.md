# AGENTS.md

本文件定义 Codex 在本仓库中的长期工程规则。

## 1. Product Context

这是一个面向中国小学阶段儿童的 AI 英语陪读微信小程序。

核心能力：

- AI 英语陪聊
- 语音输入与语音回复
- 场景英语
- 拍照理解课本
- 指定教材学习
- 英语故事
- 发音评测
- 生词与学习记录

主要用户年龄：6–12 岁。

## 2. Architecture Rules

### Backend

必须使用：

- Python
- FastAPI
- Pipecat
- uv

Pipecat 是 dependency，核心负责实时 Voice Agent / frame pipeline。

MVP 的“一句录音上传”属于 batch voice：
- 使用本项目薄 `STTGateway` / `TTSGateway`；
- 若 Pipecat service 当前 API 自然支持 batch 调用，可直接复用；
- 否则允许使用 provider 官方 SDK/API；
- 禁止为了“必须经过 Pipecat”人为制造复杂 pipeline。

进入 realtime/streaming voice 后，必须优先使用 Pipecat pipeline/transport。

禁止：

- Fork Pipecat framework 到本仓库魔改
- 重写 Pipecat 已提供的实时 voice pipeline 基础设施
- 未经 task 明确要求引入第二套 Voice Agent Framework
- 引入 Dify / FastGPT / TEN / LiveKit 作为核心框架

### Mini Program

必须使用：

- 微信原生 MiniProgram
- TDesign MiniProgram

禁止：

- React Native
- Flutter
- uni-app
- Taro

### RAG

第一阶段使用 LlamaIndex。

禁止为了第一本教材提前引入完整 RAGFlow 服务。

## 3. Reuse Before Rewrite

任何非产品差异化能力，先判断是否已有成熟 dependency 或官方示例。

优先级：

1. 官方 dependency
2. 官方 example
3. License 清晰的第三方源码
4. 薄 Adapter
5. 最后才自行实现基础设施

重点禁止重复造轮子：

- Voice pipeline
- VAD
- STT/TTS provider abstraction
- UI 基础组件
- 微信支付签名/验签
- RAG framework
- 通用网络基础设施

## 4. Source Donor Rules

允许研究/迁移：

- `pipecat-examples`
- `Spoken`
- 微信官方 `miniprogram-demo`

复制源码进入本仓库时必须更新：

- `THIRD_PARTY_NOTICES.md`

记录：

- repository
- URL
- license
- source commit hash
- original path
- destination path
- modifications

禁止复制：

- License 不明确的项目源码
- 带商业限制且未取得授权的源码

## 5. Scope Discipline

一次只执行当前 task。

禁止：

- 顺手大规模重构
- 顺手更换数据库
- 顺手引入新框架
- 顺手实现 Roadmap 后续功能
- 因“更优雅”而扩大修改范围

如果发现确实需要修改 task 允许范围外的文件，只做让当前 task 可通过的最小修复，并在 completion report 中说明。

## 6. Child Tutor Rules

儿童输出：

- 短句优先
- Beginner 允许中文辅助
- 一次只讲一个主要知识点
- 一次新增词汇尽量不超过 2–3 个
- 优先鼓励开口
- 避免长篇输出
- 避免成人化场景
- 不主动索取真实姓名、学校、地址、手机号等不必要个人信息

## 7. Secrets

禁止提交：

- API Key
- 微信 AppSecret
- 微信支付私钥
- 商户证书
- 生产数据库密码

所有 Secret 必须通过环境变量提供。

`.env` 必须加入 `.gitignore`。

## 8. Dependency Management

Python：

```bash
uv add <package>
uv sync
```

依赖进入：

- `pyproject.toml`
- `uv.lock`

MiniProgram 使用 npm。

禁止为了使用 dependency 把大型第三方 package 源码复制进仓库。

## 9. Testing

每个 task 完成前：

1. 执行 task 指定测试；
2. 执行现有相关测试；
3. 不允许删除/skip 测试来强行通过；
4. 新增业务逻辑应新增测试；
5. 外部 API 必须可 mock。

普通自动测试不得依赖真实 API key。

Codex 不得自行决定付费 STT / LLM / TTS 厂商；参见 `docs/PROVIDER_STRATEGY.md`。

## 10. API Stability

小程序只调用本项目 API。

小程序不应该知道：

- Pipecat provider 名称
- STT/TTS 第三方 API
- LlamaIndex 内部对象
- 微信支付 SDK 内部结构

## 11. Error Handling

儿童页面禁止显示：

- traceback
- provider raw error
- API key 错误详情
- Python exception
- raw diagnostic JSON

开发日志可以详细，但不得泄露 secrets。

## 12. Definition of Done

每个 task 至少满足：

- 需求已实现
- 无超范围功能
- 测试通过
- 文档/API schema 如有变化已同步
- 无 secret
- 无未登记的第三方复制代码
- git diff 无无关大改

完成后输出：

1. 修改摘要
2. 文件清单
3. 测试结果
4. 已知限制
5. 下一 task 阻塞项（若有）
