const textbooksService = require("../../services/textbooks");

const QUESTION_CHIPS = ["这个单元讲了什么？", "教我三个重点单词", "给我一个简单例句"];

Page({
  data: {
    textbook: null,
    units: [],
    unitIndex: -1,
    question: "",
    questionChips: QUESTION_CHIPS,
    answer: null,
    state: "idle",
    loading: true,
    asking: false,
    profileRequired: false,
    errorMessage: ""
  },

  onLoad() {
    return this.loadCurrent();
  },

  async loadCurrent() {
    this.setData({ loading: true, errorMessage: "", profileRequired: false });
    try {
      const current = await textbooksService.current();
      if (!current || !current.textbook) {
        this.setData({ errorMessage: "请先选择一本课本。", state: "error" });
        return;
      }
      const units = current.units || [];
      const unitIndex = units.findIndex((unit) => unit.unit_no === current.current_unit_no);
      this.setData({ textbook: current.textbook, units, unitIndex });
    } catch (error) {
      if (error.code === "PROFILE_REQUIRED") {
        this.setData({ profileRequired: true });
      } else {
        this.setData({ errorMessage: "课本学习暂时不可用，请稍后再试。", state: "error" });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  async changeUnit(event) {
    const index = Number(event.detail.value);
    const unit = this.data.units[index];
    if (!unit || !this.data.textbook) return;
    try {
      await textbooksService.select(this.data.textbook.id, unit.unit_no);
      this.setData({ unitIndex: index, answer: null, errorMessage: "", state: "idle" });
    } catch (error) {
      this.setData({ errorMessage: "单元选择没有保存，请重试。", state: "error" });
    }
  },

  onQuestionInput(event) {
    this.setData({ question: event.detail.value });
  },

  useQuestionChip(event) {
    this.setData({ question: event.currentTarget.dataset.question });
  },

  async askQuestion() {
    const question = this.data.question.trim();
    if (!question || this.data.asking) return;
    this.setData({ asking: true, answer: null, errorMessage: "", state: "asking" });
    try {
      const answer = await textbooksService.ask(question);
      this.setData({ answer, state: answer.found ? "answered" : "not-found" });
    } catch (error) {
      this.setData({ errorMessage: "现在还不能回答，请稍后再试。", state: "error" });
    } finally {
      this.setData({ asking: false });
    }
  },

  chooseAnotherBook() {
    wx.navigateBack();
  },

  goToProfile() {
    wx.navigateTo({ url: "/pages/profile/index" });
  }
});
