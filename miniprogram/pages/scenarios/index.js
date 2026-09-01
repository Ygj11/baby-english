const scenariosService = require("../../services/scenarios");

Page({
  data: {
    errorMessage: "",
    loading: true,
    profileRequired: false,
    scenes: []
  },

  onLoad() {
    this.initialLoad = this.loadScenes();
    return this.initialLoad;
  },

  onShow() {
    if (!this.hasShown) {
      this.hasShown = true;
      return this.initialLoad;
    }
    return this.loadScenes();
  },

  async loadScenes() {
    this.setData({ loading: true, errorMessage: "", profileRequired: false });
    try {
      const scenes = await scenariosService.list();
      this.setData({ scenes });
    } catch (error) {
      if (error.code === "PROFILE_REQUIRED") {
        this.setData({ profileRequired: true });
      } else {
        this.setData({ errorMessage: "场景暂时没有准备好，请稍后再试。" });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  openScene(event) {
    const sceneId = event.currentTarget.dataset.sceneId;
    if (sceneId) {
      wx.navigateTo({ url: `/pages/scenario/index?scene_id=${sceneId}` });
    }
  },

  goToProfile() {
    wx.navigateTo({ url: "/pages/profile/index" });
  }
});
