const api = require("../../services/api");

Page({
  data: {
    backendStatus: "checking",
    entries: [
      {
        id: "chat",
        icon: "🎤",
        label: "和我说英语",
        url: "/pages/chat/index"
      },
      {
        id: "camera",
        icon: "📷",
        label: "拍一拍",
        url: "/pages/photo/index"
      },
      {
        id: "textbook",
        icon: "📖",
        label: "我的课本",
        url: "/pages/textbooks/index"
      },
      {
        id: "scenario",
        icon: "🎭",
        label: "场景英语",
        url: "/pages/scenarios/index"
      },
      { id: "story", icon: "📚", label: "英语故事" }
    ]
  },

  onLoad() {
    this.checkBackend();
  },

  checkBackend() {
    this.setData({ backendStatus: "checking" });

    api
      .get("/api/health")
      .then((health) => {
        const isConnected = health && health.status === "ok";
        this.setData({
          backendStatus: isConnected ? "connected" : "unavailable"
        });
      })
      .catch(() => {
        this.setData({ backendStatus: "unavailable" });
      });
  },

  goToProfile() {
    wx.navigateTo({ url: "/pages/profile/index" });
  }
});
