const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function clearModule(modulePath) {
  delete require.cache[require.resolve(modulePath)];
}

function clearPhotoModules() {
  [
    "../services/client-id",
    "../services/api",
    "../services/audio-player",
    "../services/media",
    "../services/photo",
    "../services/profile",
    "../services/pronunciation",
    "../services/recorder",
    "../pages/photo/index"
  ].forEach(clearModule);
}

test("Home Photo entry preserves five entries and routes to Photo page", () => {
  let definition;
  global.wx = {
    getStorageSync() { return "photo_home_client_000001"; },
    setStorageSync() {},
    request() {}
  };
  global.Page = (value) => { definition = value; };
  clearModule("../pages/home/index");
  require("../pages/home/index");
  const camera = definition.data.entries.find((item) => item.id === "camera");
  assert.equal(camera.url, "/pages/photo/index");
  assert.equal(definition.data.entries.length, 5);
});

test("native media helper selects exactly one compressed image from requested source", async () => {
  const optionsSeen = [];
  global.wx = {
    chooseMedia(options) {
      optionsSeen.push(options);
      options.success({ tempFiles: [{ tempFilePath: "/tmp/chosen.jpg" }] });
    }
  };
  clearModule("../services/media");
  const media = require("../services/media");
  assert.equal(await media.chooseSingleImage("camera"), "/tmp/chosen.jpg");
  assert.deepEqual(
    {
      count: optionsSeen[0].count,
      mediaType: optionsSeen[0].mediaType,
      sizeType: optionsSeen[0].sizeType,
      sourceType: optionsSeen[0].sourceType
    },
    {
      count: 1,
      mediaType: ["image"],
      sizeType: ["compressed"],
      sourceType: ["camera"]
    }
  );
  await media.chooseSingleImage("album");
  assert.deepEqual(optionsSeen[1].sourceType, ["album"]);
});

test("Photo service reuses shared upload, owned listen endpoint and project URL", async () => {
  const requests = [];
  const uploads = [];
  global.wx = {
    getStorageSync() { return "photo_service_client_0001"; },
    setStorageSync() {},
    request(options) {
      requests.push(options);
      options.success({ statusCode: 200, data: { audio_url: "/api/voice/media/test" } });
    },
    uploadFile(options) {
      uploads.push(options);
      options.success({ statusCode: 200, data: '{"status":"ok"}' });
    }
  };
  for (const modulePath of ["../services/client-id", "../services/api", "../services/photo"]) {
    clearModule(modulePath);
  }
  const photo = require("../services/photo");
  await photo.analyze("/tmp/child-preview.jpg");
  const heard = await photo.listen(42);
  assert.match(uploads[0].url, /\/api\/photo\/analyze$/);
  assert.equal(uploads[0].filePath, "/tmp/child-preview.jpg");
  assert.equal(uploads[0].name, "file");
  assert.match(requests[0].url, /\/api\/photo\/records\/42\/listen$/);
  assert.equal(requests[0].method, "POST");
  assert.equal(photo.resolveAudioUrl(heard.audio_url), "http://127.0.0.1:8000/api/voice/media/test");
});

test("Photo page previews, analyzes, listens, repeats, prefills Chat and resets", async () => {
  let definition;
  const recorderCallbacks = {};
  const played = [];
  const navigations = [];
  global.wx = {
    chooseMedia(options) {
      options.success({ tempFiles: [{ tempFilePath: "/tmp/apple.jpg" }] });
    },
    createInnerAudioContext() {
      return {
        destroy() {},
        play() { played.push(this.source); },
        stop() {},
        set src(value) { this.source = value; }
      };
    },
    getRecorderManager() {
      return {
        onError(callback) { recorderCallbacks.error = callback; },
        onStart(callback) { recorderCallbacks.start = callback; },
        onStop(callback) { recorderCallbacks.stop = callback; },
        start() { recorderCallbacks.start(); },
        stop() {},
      };
    },
    getStorageSync() { return "photo_page_client_000001"; },
    setStorageSync() {},
    navigateTo(options) { navigations.push(options.url); }
  };
  global.Page = (value) => { definition = value; };
  clearPhotoModules();
  require("../pages/photo/index");
  const photo = require("../services/photo");
  const profile = require("../services/profile");
  const pronunciation = require("../services/pronunciation");
  profile.getProfile = async () => ({ age: 8, grade: 3, english_level: "beginner" });
  let analyzedPath = "";
  photo.analyze = async (filePath) => {
    analyzedPath = filePath;
    return {
      status: "ok",
      record_id: 42,
      primary_word_en: "apple",
      primary_meaning_zh: "苹果",
      simple_sentence_en: "This is an apple.",
      simple_sentence_zh: "这是一个苹果。",
      practice_phrase: "red apple",
      related_words: [{ word_en: "red", meaning_zh: "红色" }],
      question_en: "What is this?",
      encouragement_zh: "很好！"
    };
  };
  photo.listen = async (recordId) => {
    assert.equal(recordId, 42);
    return { audio_url: "/api/voice/media/photo" };
  };
  photo.resolveAudioUrl = (value) => `http://test${value}`;
  let evaluation;
  pronunciation.evaluate = async (filePath, phrase) => {
    evaluation = { filePath, phrase };
    return { overall_score: 90, accuracy_score: 89, fluency_score: 91, feedback: "很棒！" };
  };

  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update); }
  };
  page.onLoad();
  await Promise.resolve();
  assert.equal(page.data.profileStatus, "ready");
  await page.chooseCamera();
  assert.equal(page.data.previewPath, "/tmp/apple.jpg");
  assert.equal(page.data.state, "selected");
  await page.analyzePhoto();
  assert.equal(analyzedPath, "/tmp/apple.jpg");
  assert.equal(page.data.state, "ok");
  assert.equal(page.data.result.primary_word_en, "apple");

  await page.listen();
  assert.equal(played.at(-1), "http://test/api/voice/media/photo");

  page.startPronunciation();
  assert.equal(page.data.recorderState, "recording");
  await page.completePronunciation({ tempFilePath: "/tmp/repeat.mp3" });
  assert.deepEqual(evaluation, { filePath: "/tmp/repeat.mp3", phrase: "red apple" });
  assert.equal(page.data.pronunciationResult.overall_score, 90);

  page.practiceChat();
  assert.equal(
    navigations.at(-1),
    "/pages/chat/index?draft=Let's%20practice%20the%20word%20%22apple%22."
  );
  page.retake();
  assert.equal(page.data.previewPath, "");
  assert.equal(page.data.result, null);
  assert.equal(page.data.pronunciationResult, null);
  assert.equal(page.data.state, "idle");
  page.onUnload();
});

test("unclear and unsuitable Photo outcomes render a clean retake state", async () => {
  let definition;
  global.wx = {
    createInnerAudioContext() { return { destroy() {}, play() {}, stop() {} }; },
    getRecorderManager() { return { onError() {}, onStart() {}, onStop() {}, start() {}, stop() {} }; },
    getStorageSync() { return "photo_outcome_client_0001"; },
    setStorageSync() {}
  };
  global.Page = (value) => { definition = value; };
  clearPhotoModules();
  require("../pages/photo/index");
  const photo = require("../services/photo");
  const page = {
    ...definition,
    data: { ...definition.data, previewPath: "/tmp/photo.jpg", profileStatus: "ready" },
    setData(update) { Object.assign(this.data, update); }
  };
  for (const status of ["unclear", "unsuitable"]) {
    photo.analyze = async () => ({ status, record_id: null, message_zh: "换一张照片吧。" });
    page.setData({ state: "selected" });
    await page.analyzePhoto();
    assert.equal(page.data.state, status);
    assert.equal(page.data.result.record_id, null);
    page.retake();
    assert.equal(page.data.result, null);
    page.setData({ previewPath: "/tmp/photo.jpg", profileStatus: "ready" });
  }
});

test("Chat accepts a bounded optional prefill without auto-sending", () => {
  let definition;
  let tutorRequests = 0;
  global.wx = {
    createInnerAudioContext() { return { destroy() {}, play() {}, stop() {} }; },
    getRecorderManager() { return { onError() {}, onStart() {}, onStop() {}, start() {}, stop() {} }; },
    getStorageSync() { return "photo_chat_client_000001"; },
    setStorageSync() {},
    request(options) {
      if (options.url.endsWith("/api/tutor/chat")) tutorRequests += 1;
      options.success({ statusCode: 200, data: { age: 8, grade: 3, english_level: "beginner" } });
    }
  };
  global.Page = (value) => { definition = value; };
  for (const modulePath of ["../services/audio-player", "../services/recorder", "../pages/chat/index"]) {
    clearModule(modulePath);
  }
  require("../pages/chat/index");
  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update); }
  };
  page.onLoad({ draft: encodeURIComponent('Let\'s practice the word "apple".') });
  assert.equal(page.data.draft, 'Let\'s practice the word "apple".');
  assert.equal(tutorRequests, 0);
  page.onUnload();

  const another = {
    ...definition,
    data: { ...definition.data, draft: "" },
    setData(update) { Object.assign(this.data, update); }
  };
  another.onLoad({ draft: "x".repeat(241) });
  assert.equal(another.data.draft, "");
  another.onUnload();
});

test("Photo preview remains page-local and no sample/save-storage path exists", () => {
  const pageSource = fs.readFileSync(
    path.join(__dirname, "../pages/photo/index.js"),
    "utf8"
  );
  const template = fs.readFileSync(
    path.join(__dirname, "../pages/photo/index.wxml"),
    "utf8"
  );
  assert.match(template, /<image[^>]+src="\{\{previewPath\}\}"/);
  assert.doesNotMatch(pageSource, /saveFile|setStorage|sample|base64/i);
});
