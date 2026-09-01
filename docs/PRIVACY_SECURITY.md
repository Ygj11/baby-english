# PRIVACY_SECURITY.md

本项目面向儿童，音频、图片和学习记录默认采用数据最小化原则。

## 1. Tasks 001–008

不需要存储儿童个人数据。

## 1.1 Student Profile — 从 Task 016 开始

Backend SQLite 持久化最小学习画像：`age`、`grade`、`english_level`。不收集姓名、学校、生日、班级、性别、手机号、头像或家长信息。

小程序只在 wx.storage 保存随机匿名 client id；Profile 主数据不保存在客户端。`X-Client-Id` 只是数据 namespace，不是登录或认证 token。不同 client 必须隔离，缺失时不得共享 `anon`。

本地 SQLite 文件被 Git 忽略，不提交仓库。未来微信登录时，User/WeChat identity 与 StudentProfile 分离设计，并另行实现匿名数据 claim 和删除能力。

## 2. Audio — 从 Task 009 开始

默认策略：

```text
上传录音
↓
完成 STT / voice turn
↓
删除临时原始音频
```

除非未来产品功能明确要求保存，否则：

- 不长期保存原始儿童录音；
- 不把音频内容写入普通 application log；
- 临时文件必须 cleanup。

Task 010 的 TTS 回复音频通过本项目临时 media ID 提供，默认 5 分钟过期并删除；不长期保存，也不暴露 provider 原始 URL。

发音评测同样只在请求期间保存上传 MP3，并在成功或失败后删除。数据库只保存
0–100 的规范化分数、拒绝标记及规范化逐词详情；不保存儿童音频、讯飞原始 XML、
鉴权 URL 或 provider session payload。

## 2.1 Scenario Conversation Memory

进行中的场景仅为下一轮上下文临时保存 user/assistant 文字 turns，并限制内容长度和
总 turn 数。同 client/scene 启动新 session 时会删除旧 active transcript。完成练习时，
transcript 仅用于一次 goal assessment，随后在同一事务中删除；持久保留的只有场景
ID、完成 goal IDs、次数、时间及简短 summary/tip。场景 voice 录音仍按请求期临时文件
处理，不进入数据库。

`X-Client-Id` 只提供匿名 namespace 隔离，不是登录或访问控制凭证。

## 3. Images — Photo English

当前默认：

```text
上传图片
↓
8 MiB/静态格式/像素上限校验
↓
EXIF orientation + RGB + 1600 px 长边 + 无元数据 JPEG
↓
Qwen Vision 儿童安全结构化分析
↓
删除原始与归一化临时图片
```

数据库只保存一个安全主词、短释义/例句、练习短语、最多四个相关词和问题；不保存
图片、缩略图、路径、Base64、EXIF/GPS、OCR、人物身份或 provider 原始内容。明显的
URL、邮箱、电话/长账号输出在落库前转换为安全 `unsuitable`。人物不得被识别，也不得
推断敏感属性。后期如用于教材收藏，需要单独设计保存授权和生命周期。

## 4. Third-party Data Map

接入任何真实 STT / LLM / TTS / VLM 前，记录：

- provider 名称
- 发送的数据类型
- 目的
- 是否跨境
- 保存策略
- 隐私政策链接
- 是否需要监护人告知/同意

当前 Batch Voice MVP：

| Provider | 发送数据 | 目的 | 区域/跨境 | 保存策略 |
| --- | --- | --- | --- | --- |
| DeepSeek | Tutor system prompt、儿童输入文本、年龄/年级/英语等级衍生的教学上下文 | 生成儿童 Tutor 回复 | 上线前按实际部署与官方条款确认跨境情况 | 本项目不保存 provider raw response；provider 侧策略上线前复核 |
| Alibaba Cloud Model Studio（cn-beijing） | Tutor prompt/儿童输入文本、单次临时录音 Base64 Data URI、语言提示、Tutor 回复文本、去元数据且有尺寸上限的单张临时 JPEG Base64 Data URI、Photo 安全教学 prompt | 默认 Qwen LLM、Batch STT、Batch TTS、Qwen Vision Photo English | 请求发送至 owner 配置的北京 Workspace | 请求结束删除本地原始音频/图片及归一化图片；只保存安全 Photo 教学字段；生成音频仅由临时 media ID 保存且默认 5 分钟过期；provider 侧策略上线前复核 |
| Alibaba Cloud Model Studio Embedding（cn-beijing） | owner 授权的教材文本块；QA 时另由 Qwen LLM 接收命中的有限教材上下文和儿童问题 | `qwen3.7-text-embedding` 教材向量化与 grounded QA | owner 配置的同一北京 Workspace | 原始教材包保持 repo 外；本地 LlamaIndex 索引含 chunks/embeddings，作为受保护运行数据，不提供下载 API |
| MiniMax（保留、非默认） | 仅在 owner 显式选择该 adapter 时发送 Tutor 回复文本和 Voice ID | 可选 Batch TTS | 使用 owner 配置的 endpoint；上线前复核实际处理区域 | 不参与默认链路；provider 侧策略上线前复核 |
| iFlytek ISE | 单次临时英文 MP3 与明确的英文跟读目标 | 英语单词/短句发音评测 | 请求发送至 owner 配置的讯飞 ISE 服务；上线前按官方条款复核处理区域 | 请求结束删除本地音频；仅持久化规范化结果，不保存原始 XML；provider 侧策略上线前复核 |

## 5. Logging

禁止日志记录：

- API keys
- AppSecret
- 完整支付密钥
- 原始儿童音频
- provider 原始评测 XML 或含鉴权参数的 WebSocket URL
- 原始图片（默认）
- 图片 Base64/Data URI、文件名、EXIF 或 Vision provider 原始响应
- 教材问题、命中正文、embedding 向量、source/index 文件路径
- 不必要的真实身份信息

## 6. User Identity

未来微信登录：

微信身份和 StudentProfile 分离。

不要把：

- openid
- 儿童昵称
- 年级
- 学习内容

全部塞进客户端明文日志。

## 7. Before Public Beta

必须完成：

- 隐私政策
- 第三方 SDK / API 清单
- 儿童/监护人相关合规评审
- 数据删除能力
- 账号删除机制
- 临时文件生命周期
- 生产 secret 管理
