const audioPlayer = require("../../services/audio-player");
const mediaService = require("../../services/media");
const photoService = require("../../services/photo");
const profileService = require("../../services/profile");
const pronunciationService = require("../../services/pronunciation");
const recorder = require("../../services/recorder");

Page({
  data: {
    errorMessage: "",
    listening: false,
    previewPath: "",
    profileRequired: false,
    profileStatus: "checking",
    pronunciationResult: null,
    recorderMessage: "点一下，跟读照片里的英语",
    recorderState: "idle",
    result: null,
    state: "idle"
  },

  onLoad() {
    this.recordingReferenceText = "";
    this.recorderUnsubscribers = [
      recorder.onStart(() => {
        this.setData({
          recorderMessage: "正在跟读…读完请点停止",
          recorderState: "recording"
        });
      }),
      recorder.onStop((recording) => this.completePronunciation(recording)),
      recorder.onError(() => {
        this.setData({
          recorderMessage: "没录好，再试一次吧 🎤",
          recorderState: "error"
        });
      })
    ];
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

  chooseCamera() {
    return this.chooseImage("camera");
  },

  chooseAlbum() {
    return this.chooseImage("album");
  },

  async chooseImage(sourceType) {
    if (this.data.state === "analyzing") {
      return;
    }
    try {
      const previewPath = await mediaService.chooseSingleImage(sourceType);
      this.resetLearningState();
      this.setData({ previewPath, state: "selected" });
    } catch (error) {
      if (!error || !String(error.errMsg || error.message || error).includes("cancel")) {
        this.setData({ errorMessage: "没有选好照片，请再试一次。", state: "error" });
      }
    }
  },

  async analyzePhoto() {
    if (
      !this.data.previewPath ||
      this.data.state === "analyzing" ||
      this.data.profileRequired ||
      this.data.profileStatus !== "ready"
    ) {
      return;
    }
    this.setData({ errorMessage: "", state: "analyzing" });
    try {
      const result = await photoService.analyze(this.data.previewPath);
      this.setData({
        result,
        state: ["ok", "unclear", "unsuitable"].includes(result.status)
          ? result.status
          : "error"
      });
    } catch (error) {
      if (error.code === "PROFILE_REQUIRED") {
        this.setData({ profileRequired: true, profileStatus: "missing" });
      }
      this.setData({
        errorMessage: "照片暂时没有看清，请换一张再试。",
        state: "error"
      });
    }
  },

  async listen() {
    if (
      this.data.state !== "ok" ||
      !this.data.result ||
      !this.data.result.record_id ||
      this.data.listening
    ) {
      return;
    }
    audioPlayer.cleanup();
    this.setData({ listening: true, errorMessage: "" });
    try {
      const response = await photoService.listen(this.data.result.record_id);
      audioPlayer.play(photoService.resolveAudioUrl(response.audio_url));
    } catch (error) {
      this.setData({ errorMessage: "声音暂时没准备好，请稍后再试。" });
    } finally {
      this.setData({ listening: false });
    }
  },

  startPronunciation() {
    if (
      this.data.state !== "ok" ||
      !this.data.result ||
      !this.data.result.practice_phrase ||
      !["idle", "error"].includes(this.data.recorderState)
    ) {
      return;
    }
    audioPlayer.cleanup();
    this.recordingReferenceText = this.data.result.practice_phrase;
    this.setData({
      pronunciationResult: null,
      recorderMessage: "准备录音…",
      recorderState: "processing"
    });
    try {
      recorder.start();
    } catch (error) {
      this.setData({ recorderMessage: "没录好，再试一次吧 🎤", recorderState: "error" });
    }
  },

  stopRecording() {
    if (this.data.recorderState !== "recording") {
      return;
    }
    this.setData({ recorderMessage: "正在评测发音…", recorderState: "processing" });
    recorder.stop();
  },

  async completePronunciation(recording) {
    const phrase = this.recordingReferenceText;
    if (!phrase) {
      return;
    }
    this.setData({ recorderMessage: "正在评测发音…", recorderState: "processing" });
    try {
      const result = await pronunciationService.evaluate(
        recording.tempFilePath,
        phrase
      );
      this.setData({
        pronunciationResult: result,
        recorderMessage: "评测完成，想再读一次也可以！",
        recorderState: "idle"
      });
    } catch (error) {
      this.setData({
        recorderMessage: "这次没评好，我们再试一次吧 🎤",
        recorderState: "error"
      });
    } finally {
      this.recordingReferenceText = "";
    }
  },

  practiceChat() {
    if (this.data.state !== "ok" || !this.data.result) {
      return;
    }
    const word = String(this.data.result.primary_word_en || "")
      .replace(/[^A-Za-z '\-]/g, "")
      .trim()
      .slice(0, 48);
    if (!word) {
      return;
    }
    const draft = `Let's practice the word "${word}".`;
    wx.navigateTo({
      url: `/pages/chat/index?draft=${encodeURIComponent(draft)}`
    });
  },

  retake() {
    this.resetLearningState();
    this.setData({ previewPath: "", state: "idle" });
  },

  resetLearningState() {
    if (this.data.recorderState === "recording") {
      recorder.cancel();
    }
    audioPlayer.cleanup();
    this.recordingReferenceText = "";
    this.setData({
      errorMessage: "",
      listening: false,
      pronunciationResult: null,
      recorderMessage: "点一下，跟读照片里的英语",
      recorderState: "idle",
      result: null
    });
  },

  onUnload() {
    if (this.data.recorderState === "recording") {
      recorder.cancel();
    }
    audioPlayer.cleanup();
    (this.recorderUnsubscribers || []).forEach((unsubscribe) => unsubscribe());
  }
});
