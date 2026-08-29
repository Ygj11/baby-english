# TASK 008 — Recorder UI

## Goal

在 Chat 页实现 Push-to-Talk 录音 UI。

不调用 Backend ASR。

## Allowed Changes

```text
miniprogram/services/recorder.js
miniprogram/pages/chat/**
miniprogram/components/**
THIRD_PARTY_NOTICES.md（若复制示例）
```

## Source Rule

优先参考微信官方 `miniprogram-demo` RecorderManager 示例。

如果复制代码，登记：

- repo
- commit
- path
- license
- modifications

## Recorder

使用：

```text
wx.getRecorderManager()
```

封装：

```text
start()
stop()
cancel()
onStart()
onStop()
onError()
```

状态：

```text
idle
recording
processing
error
```

录音结束当前 task 只需拿到：

- temp file
- duration

儿童 UI 不显示文件路径。

## Do Not

- 不调用 STT
- 不做 WebSocket
- 不做 PCM streaming
- 不做 TTS
- 不自行写 native recorder

## Acceptance

真机/开发者工具：

- 开始录音
- 停止录音
- 得到临时文件
- error 可恢复

Codex 无设备时给人工 smoke test 步骤。
