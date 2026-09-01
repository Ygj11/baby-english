const profileService = require("../../services/profile");

const AGES = [6, 7, 8, 9, 10, 11, 12];
const GRADES = [1, 2, 3, 4, 5, 6];
const LEVELS = [
  { value: "starter", label: "启蒙 Starter" },
  { value: "beginner", label: "入门 Beginner" },
  { value: "elementary", label: "基础 Elementary" }
];

Page({
  data: {
    ages: AGES,
    grades: GRADES,
    levels: LEVELS,
    ageIndex: 2,
    gradeIndex: 2,
    levelIndex: 1,
    loading: true,
    saving: false,
    statusMessage: ""
  },

  async onLoad() {
    try {
      const profile = await profileService.getProfile();
      this.fillProfile(profile);
    } catch (error) {
      if (error.code !== "PROFILE_NOT_FOUND") {
        this.setData({ statusMessage: "学习设置暂时无法读取，请稍后再试。" });
      }
    } finally {
      this.setData({ loading: false });
    }
  },

  fillProfile(profile) {
    this.setData({
      ageIndex: Math.max(0, AGES.indexOf(profile.age)),
      gradeIndex: Math.max(0, GRADES.indexOf(profile.grade)),
      levelIndex: Math.max(
        0,
        LEVELS.findIndex((level) => level.value === profile.english_level)
      )
    });
  },

  onAgeChange(event) {
    this.setData({ ageIndex: Number(event.detail.value), statusMessage: "" });
  },

  onGradeChange(event) {
    this.setData({ gradeIndex: Number(event.detail.value), statusMessage: "" });
  },

  onLevelChange(event) {
    this.setData({ levelIndex: Number(event.detail.value), statusMessage: "" });
  },

  async save() {
    if (this.data.saving || this.data.loading) {
      return;
    }
    this.setData({ saving: true, statusMessage: "" });
    try {
      await profileService.saveProfile({
        age: AGES[this.data.ageIndex],
        grade: GRADES[this.data.gradeIndex],
        english_level: LEVELS[this.data.levelIndex].value
      });
      this.setData({ statusMessage: "保存成功，可以开始学习啦！" });
    } catch (error) {
      this.setData({ statusMessage: "没有保存成功，请再试一次。" });
    } finally {
      this.setData({ saving: false });
    }
  }
});
