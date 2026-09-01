const assert = require("node:assert/strict");
const test = require("node:test");

function clearModule(modulePath) {
  delete require.cache[require.resolve(modulePath)];
}

test("unrelated 404 is not classified as missing Profile", async () => {
  global.wx = {
    getStorageSync() {
      return "test_404_client_000000000001";
    },
    setStorageSync() {},
    request(options) {
      options.success({ statusCode: 404, data: {} });
    }
  };
  clearModule("../services/client-id");
  clearModule("../services/api");
  const api = require("../services/api");

  await assert.rejects(
    api.get("/api/not-profile"),
    (error) => error.code === "API_UNAVAILABLE" && error.statusCode === 404
  );
  await assert.rejects(
    api.get("/api/student/profile"),
    (error) => error.code === "PROFILE_NOT_FOUND"
  );

  global.wx.request = (options) => {
    options.success({ statusCode: 409, data: {} });
  };
  await assert.rejects(
    api.get("/api/not-profile"),
    (error) => error.code === "API_UNAVAILABLE"
  );
});

test("pronunciation service uploads MP3 with reference_text", async () => {
  let uploadOptions;
  global.wx = {
    getStorageSync() {
      return "test_ise_service_00000000001";
    },
    setStorageSync() {},
    uploadFile(options) {
      uploadOptions = options;
      options.success({ statusCode: 200, data: '{"overall_score":88}' });
    }
  };
  for (const path of [
    "../services/client-id",
    "../services/api",
    "../services/pronunciation"
  ]) {
    clearModule(path);
  }
  const pronunciation = require("../services/pronunciation");
  await pronunciation.evaluate("/tmp/reading.mp3", "banana");

  assert.match(uploadOptions.url, /\/api\/pronunciation\/evaluate$/);
  assert.equal(uploadOptions.filePath, "/tmp/reading.mp3");
  assert.deepEqual(uploadOptions.formData, { reference_text: "banana" });
});

test("repeat uses pronunciation mode while normal recording keeps voice turn", async () => {
  let pageDefinition;
  const recorderCallbacks = {};
  let recorderStarts = 0;
  global.wx = {
    createInnerAudioContext() {
      return { destroy() {}, play() {}, stop() {}, set src(_value) {} };
    },
    getRecorderManager() {
      return {
        onError(callback) {
          recorderCallbacks.error = callback;
        },
        onStart(callback) {
          recorderCallbacks.start = callback;
        },
        onStop(callback) {
          recorderCallbacks.stop = callback;
        },
        start(options) {
          recorderStarts += 1;
          assert.equal(options.sampleRate, 16000);
          assert.equal(options.numberOfChannels, 1);
          assert.equal(options.format, "mp3");
          recorderCallbacks.start();
        },
        stop() {}
      };
    },
    getStorageSync() {
      return "test_ise_page_client_00000001";
    },
    setStorageSync() {},
    request(options) {
      options.success({
        statusCode: 200,
        data: { age: 8, grade: 3, english_level: "beginner" }
      });
    }
  };
  global.Page = (definition) => {
    pageDefinition = definition;
  };

  for (const path of [
    "../services/audio-player",
    "../services/recorder",
    "../services/pronunciation",
    "../services/voice",
    "../pages/chat/index"
  ]) {
    clearModule(path);
  }
  require("../pages/chat/index");
  const pronunciation = require("../services/pronunciation");
  const voice = require("../services/voice");
  let pronunciationCalls = 0;
  let voiceCalls = 0;
  pronunciation.evaluate = async (path, target) => {
    pronunciationCalls += 1;
    assert.equal(path, "/tmp/repeat.mp3");
    assert.equal(target, "banana");
    return {
      overall_score: 88,
      accuracy_score: 86,
      fluency_score: 90,
      completeness_score: 100,
      rejected: false,
      words: [{ word: "banana", score: 86 }],
      feedback: "很棒！"
    };
  };
  voice.turn = async () => {
    voiceCalls += 1;
    return {
      transcript: "hello",
      reply: "Hello. Repeat after me: hello",
      repeat_text: "hello",
      audio_url: "/api/voice/media/test",
      suggested_actions: ["listen", "repeat", "explain_zh"]
    };
  };
  voice.resolveAudioUrl = (path) => path;

  const page = {
    ...pageDefinition,
    data: {
      ...pageDefinition.data,
      profileStatus: "ready",
      messages: [...pageDefinition.data.messages]
    },
    setData(update) {
      Object.assign(this.data, update);
    },
    lastRepeatText: "banana"
  };
  page.onLoad();
  page.setData({ profileStatus: "ready" });

  page.onSuggestedAction({ currentTarget: { dataset: { action: "repeat" } } });
  assert.equal(page.recordingMode, "pronunciation");
  assert.equal(page.data.pronunciationTarget, "banana");
  page.lastRepeatText = "a newer target";
  await page.completeRecording({ tempFilePath: "/tmp/repeat.mp3", duration: 900 });
  assert.equal(pronunciationCalls, 1);
  assert.equal(voiceCalls, 0);
  assert.equal(page.data.pronunciationResult.overall_score, 88);
  assert.match(page.data.pronunciationResult.feedback, /很棒/);

  page.startRecording();
  await page.completeRecording({ tempFilePath: "/tmp/voice.mp3", duration: 900 });
  assert.equal(voiceCalls, 1);
  assert.equal(pronunciationCalls, 1);
  assert.equal(recorderStarts, 2);
  page.onUnload();
});

test("Chat response without repeat_text hides repeat action", async () => {
  let pageDefinition;
  global.wx = {
    createInnerAudioContext() {
      return { destroy() {}, play() {}, stop() {} };
    },
    getRecorderManager() {
      return { onError() {}, onStart() {}, onStop() {}, start() {}, stop() {} };
    },
    getStorageSync() {
      return "test_no_repeat_client_00000001";
    },
    setStorageSync() {}
  };
  global.Page = (definition) => {
    pageDefinition = definition;
  };
  for (const path of ["../services/recorder", "../pages/chat/index"]) {
    clearModule(path);
  }
  require("../pages/chat/index");
  const chat = require("../services/chat");
  chat.sendMessage = async () => ({
    reply: "Apple means 苹果。",
    repeat_text: null,
    suggested_actions: ["repeat", "explain_zh"]
  });
  const page = {
    ...pageDefinition,
    data: { ...pageDefinition.data, profileStatus: "ready" },
    setData(update) {
      Object.assign(this.data, update);
    }
  };
  await page.onSend({ detail: { value: "apple" } });

  assert.equal(page.lastRepeatText, "");
  assert.deepEqual(
    page.data.suggestedActions.map((action) => action.id),
    ["explain_zh"]
  );
});
