const chatService = require("../../services/chat");
const audioPlayer = require("../../services/audio-player");
const recorder = require("../../services/recorder");
const profileService = require("../../services/profile");
const pronunciationService = require("../../services/pronunciation");
const voiceService = require("../../services/voice");

let messageSequence = 0;

const ACTION_LABELS = {
  listen: "🔊 再听",
  repeat: "🎤 跟读",
  explain_zh: "🇨🇳 中文讲讲"
};

function createMessage(role, text) {
  messageSequence += 1;
  return {
    id: `message-${messageSequence}`,
    role,
    placement: role === "user" ? "right" : "left",
    name: role === "user" ? "我" : "AI Tutor",
    status: "complete",
    content: [{ type: "text", data: text }]
  };
}

function mapSuggestedActions(actions, repeatText) {
  return (actions || [])
    .filter(
      (action) => ACTION_LABELS[action] && (action !== "repeat" || repeatText)
    )
    .map((action) => ({ id: action, label: ACTION_LABELS[action] }));
}

function safePrefill(rawDraft) {
  if (typeof rawDraft !== "string" || !rawDraft || rawDraft.length > 240) {
    return "";
  }
  let decoded = rawDraft;
  try {
    decoded = decodeURIComponent(rawDraft);
  } catch (error) {
    return "";
  }
  const normalized = decoded.trim();
  if (!normalized || normalized.length > 160 || /[\u0000-\u001f\u007f]/.test(normalized)) {
    return "";
  }
  return normalized;
}

Page({
  data: {
    draft: "",
    errorMessage: "",
    actionLoading: false,
    loading: false,
    messages: [createMessage("assistant", "Hi! What would you like to learn?")],
    profileRequired: false,
    profileStatus: "checking",
    pronunciationResult: null,
    pronunciationTarget: "",
    recorderMessage: "点一下，开始说英语",
    recorderState: "idle",
    recordingDuration: 0,
    senderActions: [{ name: "send", type: "icon" }],
    suggestedActions: [],
    transcript: ""
  },

  onLoad(options = {}) {
    this.recorderUnsubscribers = [
      recorder.onStart(() => {
        this.setData({
          recorderMessage:
            this.recordingMode === "pronunciation"
              ? "正在跟读…读完请点停止"
              : "正在录音…说完请点停止",
          recorderState: "recording"
        });
      }),
      recorder.onStop((result) => this.completeRecording(result)),
      recorder.onError(() => {
        this.recordedFile = null;
        this.setData({
          recorderMessage: "没录好，再试一次吧 🎤",
          recorderState: "error",
          recordingDuration: 0
        });
      })
    ];
    const draft = safePrefill(options.draft);
    if (draft) {
      this.setData({ draft });
    }
    this.checkProfile();
  },

  onShow() {
    this.checkProfile();
  },

  async checkProfile() {
    this.setData({ profileStatus: "checking" });
    try {
      await profileService.getProfile();
      this.setData({ profileRequired: false, profileStatus: "ready" });
    } catch (error) {
      if (error.code === "PROFILE_NOT_FOUND") {
        this.setData({ profileRequired: true, profileStatus: "missing" });
        return;
      }
      this.setData({ profileStatus: "unavailable" });
    }
  },

  goToProfile() {
    wx.navigateTo({ url: "/pages/profile/index" });
  },

  onUnload() {
    if (this.data.recorderState === "recording") {
      recorder.cancel();
    }
    audioPlayer.cleanup();
    (this.recorderUnsubscribers || []).forEach((unsubscribe) => unsubscribe());
  },

  startRecording() {
    this.beginRecording("voice");
  },

  startPronunciation() {
    if (!this.lastRepeatText) {
      return;
    }
    this.beginRecording("pronunciation");
  },

  beginRecording(mode) {
    if (this.data.profileRequired || this.data.profileStatus === "checking") {
      return;
    }
    if (
      !["idle", "error"].includes(this.data.recorderState) ||
      this.data.loading ||
      this.data.actionLoading
    ) {
      return;
    }
    if (mode === "pronunciation" && !this.lastRepeatText) {
      return;
    }
    this.recordingMode = mode;
    this.recordingReferenceText =
      mode === "pronunciation" ? this.lastRepeatText : "";
    audioPlayer.cleanup();
    this.voiceAudioUrl = "";
    this.recordedFile = null;
    this.setData({
      recorderMessage: "准备录音…",
      recorderState: "processing",
      pronunciationResult: mode === "pronunciation" ? null : this.data.pronunciationResult,
      pronunciationTarget:
        mode === "pronunciation" ? this.lastRepeatText : this.data.pronunciationTarget,
      recordingDuration: 0,
      suggestedActions: [],
      transcript: ""
    });

    try {
      recorder.start();
    } catch (error) {
      this.setData({
        recorderMessage: "没录好，再试一次吧 🎤",
        recorderState: "error"
      });
    }
  },

  stopRecording() {
    if (this.data.recorderState !== "recording") {
      return;
    }
    this.setData({
      recorderMessage: "正在处理录音…",
      recorderState: "processing"
    });
    recorder.stop();
  },

  cancelRecording() {
    if (this.data.recorderState === "recording") {
      recorder.cancel();
    }
    this.recordedFile = null;
    this.recordingMode = "voice";
    this.setData({
      recorderMessage: "已取消，点一下可以重录",
      recorderState: "idle",
      recordingDuration: 0,
      transcript: ""
    });
  },

  completeRecording(result) {
    if (this.recordingMode === "pronunciation") {
      return this.completePronunciation(result);
    }
    return this.completeVoiceTurn(result);
  },

  async completeVoiceTurn(result) {
    this.recordedFile = result.tempFilePath;
    this.setData({
      recorderMessage: "正在听你说的话…",
      recorderState: "processing",
      recordingDuration: result.duration,
      transcript: ""
    });

    try {
      const response = await voiceService.turn(result.tempFilePath);
      this.voiceAudioUrl = voiceService.resolveAudioUrl(response.audio_url);
      this.lastAssistantReply = response.reply;
      this.lastRepeatText = response.repeat_text || "";
      this.setData({
        recorderMessage: `录音完成 ${Math.ceil(result.duration / 1000)} 秒`,
        recorderState: "idle",
        transcript: `我听到：${response.transcript}`,
        pronunciationResult: null,
        pronunciationTarget: this.lastRepeatText,
        messages: [
          ...this.data.messages,
          createMessage("user", response.transcript),
          createMessage("assistant", response.reply)
        ],
        suggestedActions: mapSuggestedActions(
          response.suggested_actions,
          this.lastRepeatText
        )
      });
      audioPlayer.play(this.voiceAudioUrl);
    } catch (error) {
      this.setData({
        recorderMessage: "没听清楚，再说一次吧 🎤",
        recorderState: "error",
        transcript: ""
      });
    } finally {
      this.recordedFile = null;
      this.recordingMode = "voice";
    }
  },

  async completePronunciation(result) {
    const target = this.recordingReferenceText;
    this.recordedFile = result.tempFilePath;
    this.setData({
      recorderMessage: "正在评测发音…",
      recorderState: "processing",
      recordingDuration: result.duration,
      pronunciationTarget: target
    });

    try {
      const response = await pronunciationService.evaluate(
        result.tempFilePath,
        target
      );
      this.setData({
        recorderMessage: "评测完成，想再读一次也可以！",
        recorderState: "idle",
        pronunciationResult: response
      });
    } catch (error) {
      this.setData({
        recorderMessage: "这次没评好，我们再试一次吧 🎤",
        recorderState: "error"
      });
    } finally {
      this.recordedFile = null;
      this.recordingReferenceText = "";
      this.recordingMode = "voice";
    }
  },

  onSuggestedAction(event) {
    const action = event.currentTarget.dataset.action;
    if (action === "listen") {
      audioPlayer.replay();
    } else if (action === "repeat") {
      this.startPronunciation();
    } else if (action === "explain_zh") {
      return this.explainLastReply();
    }
  },

  async explainLastReply() {
    if (!this.lastAssistantReply || this.data.actionLoading || this.data.loading) {
      return;
    }

    audioPlayer.cleanup();
    this.voiceAudioUrl = "";
    this.setData({
      actionLoading: true,
      errorMessage: "",
      suggestedActions: this.data.suggestedActions.filter(
        (action) => action.id !== "listen"
      )
    });

    try {
      const response = await chatService.explainInChinese(this.lastAssistantReply);
      this.lastAssistantReply = response.reply;
      this.lastRepeatText = response.repeat_text || "";
      this.setData({
        messages: [
          ...this.data.messages,
          createMessage("assistant", response.reply)
        ],
        pronunciationResult: null,
        pronunciationTarget: this.lastRepeatText,
        suggestedActions: mapSuggestedActions(
          response.suggested_actions,
          this.lastRepeatText
        )
      });
    } catch (error) {
      this.setData({
        errorMessage: "中文解释暂时没准备好，请再试一次吧。"
      });
    } finally {
      this.setData({ actionLoading: false });
    }
  },

  onInputChange(event) {
    this.setData({
      draft: event.detail.value,
      errorMessage: ""
    });
  },

  async onSend(event) {
    const message = (event.detail.value || this.data.draft).trim();
    if (
      !message ||
      this.data.loading ||
      this.data.actionLoading ||
      this.data.profileRequired ||
      this.data.profileStatus === "checking"
    ) {
      return;
    }

    audioPlayer.cleanup();
    this.voiceAudioUrl = "";
    this.setData({
      draft: "",
      errorMessage: "",
      loading: true,
      messages: [...this.data.messages, createMessage("user", message)],
      suggestedActions: []
    });

    try {
      const response = await chatService.sendMessage(message);
      this.lastAssistantReply = response.reply;
      this.lastRepeatText = response.repeat_text || "";
      this.setData({
        messages: [
          ...this.data.messages,
          createMessage("assistant", response.reply)
        ],
        pronunciationResult: null,
        pronunciationTarget: this.lastRepeatText,
        suggestedActions: mapSuggestedActions(
          response.suggested_actions,
          this.lastRepeatText
        )
      });
    } catch (error) {
      this.setData({
        errorMessage: "现在有点忙，请再试一次吧。"
      });
    } finally {
      this.setData({ loading: false });
    }
  }
});
