const textbooksService = require("../../services/textbooks");

Page({
  data: {
    books: [],
    loading: true,
    selectingId: null,
    profileRequired: false,
    errorMessage: ""
  },

  onLoad() {
    return this.loadBooks();
  },

  async loadBooks() {
    this.setData({ loading: true, profileRequired: false, errorMessage: "" });
    try {
      const books = await textbooksService.list();
      this.setData({ books: Array.isArray(books) ? books : [] });
    } catch (error) {
      if (error.code === "PROFILE_REQUIRED") {
        this.setData({ profileRequired: true });
      } else {
        this.setData({ errorMessage: "课本目录暂时不可用，请稍后再试。" });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  async chooseBook(event) {
    const textbookId = Number(event.currentTarget.dataset.textbookId);
    if (!textbookId || this.data.selectingId) return;
    this.setData({ selectingId: textbookId, errorMessage: "" });
    try {
      await textbooksService.select(textbookId, null);
      wx.navigateTo({ url: "/pages/textbook/index" });
    } catch (error) {
      if (error.code === "PROFILE_REQUIRED") {
        this.setData({ profileRequired: true });
      } else {
        this.setData({ errorMessage: "暂时不能选择这本课本，请重试。" });
      }
    } finally {
      this.setData({ selectingId: null });
    }
  },

  goToProfile() {
    wx.navigateTo({ url: "/pages/profile/index" });
  }
});
