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
