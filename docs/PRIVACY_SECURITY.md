# PRIVACY_SECURITY.md

本项目面向儿童，音频、图片和学习记录默认采用数据最小化原则。

## 1. Tasks 001–008

不需要存储儿童个人数据。

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

## 3. Images — Future Vision

默认：

```text
上传图片
↓
完成识别
↓
按临时数据策略删除
```

后期如用于教材收藏，需要单独设计保存授权和生命周期。

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
| Alibaba Cloud Model Studio（cn-beijing） | Tutor prompt/儿童输入文本、单次临时录音 Base64 Data URI、语言提示、Tutor 回复文本 | 默认 Qwen LLM、Batch STT、Batch TTS | 请求发送至 owner 配置的北京 Workspace | 请求结束删除本地原始上传；生成音频仅由临时 media ID 保存且默认 5 分钟过期；provider 侧策略上线前复核 |
| MiniMax（保留、非默认） | 仅在 owner 显式选择该 adapter 时发送 Tutor 回复文本和 Voice ID | 可选 Batch TTS | 使用 owner 配置的 endpoint；上线前复核实际处理区域 | 不参与默认链路；provider 侧策略上线前复核 |

## 5. Logging

禁止日志记录：

- API keys
- AppSecret
- 完整支付密钥
- 原始儿童音频
- 原始图片（默认）
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
