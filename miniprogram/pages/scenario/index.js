const audioPlayer = require("../../services/audio-player");
const pronunciationService = require("../../services/pronunciation");
const recorder = require("../../services/recorder");
const scenariosService = require("../../services/scenarios");

let messageSequence = 0;

function message(role, text) {
  messageSequence += 1;
  return {
    id: `scenario-message-${messageSequence}`,
    role,
    placement: role === "user" ? "right" : "left",
    name: role === "user" ? "我" : "场景伙伴",
    status: "complete",
    content: [{ type: "text", data: text }]
  };
}

function decorateScene(scene, progress) {
  const completed = new Set((progress || scene.progress).completed_goal_ids || []);
  return {
    ...scene,
    goals: scene.goals.map((goal) => ({ ...goal, completed: completed.has(goal.id) }))
  };
}

Page({
  data: {
    completed: false,
    completion: null,
    draft: "",
    errorMessage: "",
    loading: true,
    messages: [],
    pronunciationResult: null,
    pronunciationTarget: "",
    recorderMessage: "点麦克风，也可以直接打字",
    recorderState: "idle",
    scene: null,
    sending: false,
    sessionId: null
  },

  async onLoad(options) {
    this.sceneId = options.scene_id;
    this.recorderUnsubscribers = [
      recorder.onStart(() => this.setData({ recorderState: "recording", recorderMessage: this.recordingMode === "pronunciation" ? "正在跟读…" : "正在说场景对话…" })),
      recorder.onStop((result) => this.completeRecording(result)),
      recorder.onError(() => this.setData({ recorderState: "error", recorderMessage: "没录好，再试一次吧 🎤" }))
    ];
    try {
      const started = await scenariosService.start(this.sceneId);
      this.setData({
        scene: decorateScene(started.scene, started.progress),
        sessionId: started.session_id,
        messages: [message("assistant", started.opening_message)]
      });
    } catch (error) {
      this.setData({ errorMessage: error.code === "PROFILE_REQUIRED" ? "请先完成学习设置。" : "场景暂时无法开始，请返回重试。" });
    } finally {
      this.setData({ loading: false });
    }
  },

  onUnload() {
    if (this.data.recorderState === "recording") recorder.cancel();
    audioPlayer.cleanup();
    (this.recorderUnsubscribers || []).forEach((unsubscribe) => unsubscribe());
  },

  onInputChange(event) {
    this.setData({ draft: event.detail.value, errorMessage: "" });
  },

  async onSend(event) {
    const text = (event.detail.value || this.data.draft).trim();
    if (
      !text || this.data.sending || this.data.completed || !this.data.sessionId ||
      !["idle", "error"].includes(this.data.recorderState)
    ) return;
    this.setData({ draft: "", sending: true, errorMessage: "" });
    try {
      const response = await scenariosService.turn(this.data.sessionId, text);
      this.setData({ messages: [...this.data.messages, message("user", text), message("assistant", response.reply)] });
    } catch (error) {
      this.setData({ errorMessage: "场景伙伴暂时没听清，请再试一次。" });
    } finally {
      this.setData({ sending: false });
    }
  },

  startVoice() {
    this.beginRecording("voice", "");
  },

  practiceGoal(event) {
    this.beginRecording("pronunciation", event.currentTarget.dataset.phrase);
  },

  beginRecording(mode, phrase) {
    if (this.data.completed || this.data.sending || !["idle", "error"].includes(this.data.recorderState)) return;
    this.recordingMode = mode;
    this.recordingReferenceText = phrase;
    audioPlayer.cleanup();
    this.setData({
      pronunciationResult: mode === "pronunciation" ? null : this.data.pronunciationResult,
      pronunciationTarget: mode === "pronunciation" ? phrase : this.data.pronunciationTarget,
      recorderMessage: "准备录音…",
      recorderState: "processing"
    });
    recorder.start();
  },

  stopRecording() {
    if (this.data.recorderState !== "recording") return;
    this.setData({ recorderState: "processing", recorderMessage: "正在处理…" });
    recorder.stop();
  },

  completeRecording(result) {
    return this.recordingMode === "pronunciation"
      ? this.completePronunciation(result)
      : this.completeVoice(result);
  },

  async completeVoice(result) {
    try {
      const response = await scenariosService.voiceTurn(this.data.sessionId, result.tempFilePath);
      this.setData({
        messages: [...this.data.messages, message("user", response.transcript), message("assistant", response.reply)],
        recorderMessage: "录音完成，可以继续说",
        recorderState: "idle"
      });
      audioPlayer.play(scenariosService.resolveAudioUrl(response.audio_url));
    } catch (error) {
      this.setData({ recorderMessage: "这次没听清，再说一次吧 🎤", recorderState: "error" });
    } finally {
      this.recordingMode = "voice";
    }
  },

  async completePronunciation(result) {
    const phrase = this.recordingReferenceText;
    try {
      const evaluation = await pronunciationService.evaluate(result.tempFilePath, phrase);
      this.setData({ pronunciationResult: evaluation, recorderMessage: "跟读评测完成！", recorderState: "idle" });
    } catch (error) {
      this.setData({ recorderMessage: "跟读没评好，再试一次吧 🎤", recorderState: "error" });
    } finally {
      this.recordingMode = "voice";
      this.recordingReferenceText = "";
    }
  },

  async completeSession() {
    if (
      this.data.completed || this.data.sending || !this.data.sessionId ||
      !["idle", "error"].includes(this.data.recorderState)
    ) return;
    this.setData({ sending: true, errorMessage: "" });
    try {
      const completion = await scenariosService.complete(this.data.sessionId);
      this.setData({
        completed: true,
        completion,
        scene: decorateScene(this.data.scene, completion.progress)
      });
    } catch (error) {
      this.setData({ errorMessage: error.code === "API_VALIDATION" ? "至少先说一句英语，再完成练习。" : "总结暂时没有生成，请稍后再试。" });
    } finally {
      this.setData({ sending: false });
    }
  }
});
