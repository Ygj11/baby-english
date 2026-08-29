# OPEN_SOURCE_POLICY.md

## 1. Usage Classes

### A. Dependency

通过包管理器：

- Pipecat
- TDesign MiniProgram
- LlamaIndex
- wechatpayv3（后续）

不复制整个源码。

### B. Source Donor

允许迁移最小代码：

- pipecat-examples
- Spoken
- 微信官方 miniprogram-demo

必须记录来源。

### C. Reference Only

只看设计，不复制，除非重新核实 License：

- License 不明确的教育项目
- 带附加商业限制的项目
- 与当前架构不匹配的大型应用

## 2. Source Copy Checklist

复制前确认：

- [ ] License 明确
- [ ] 允许商业使用
- [ ] source commit 已记录
- [ ] 原路径已记录
- [ ] 新路径已记录
- [ ] 修改说明已记录
- [ ] 必要版权声明已保留

## 3. 登记

更新：

```text
THIRD_PARTY_NOTICES.md
```

模板：

```text
## Project Name

Repository:
License:
Source commit:
Original path:
Destination:
Usage:
Modifications:
```

## 4. 禁止

- 把“GitHub 可见”当作“允许商业复制”
- 删除必须保留的版权声明
- 引入来源不明的大段代码
- Codex 从未知网页复制源码却不登记
