const assert = require("node:assert/strict");
const test = require("node:test");

function clearModule(modulePath) {
  delete require.cache[require.resolve(modulePath)];
}

test("explainInChinese sends the last AI reply through the Tutor API", async () => {
  let requestOptions;
  global.wx = {
    getStorageSync() {
      return "test_miniprogram_client_000001";
    },
    setStorageSync() {},
    request(options) {
      requestOptions = options;
      options.success({
        statusCode: 200,
        data: {
          reply: "Apple 是苹果。",
          suggested_actions: ["repeat", "explain_zh"]
        }
      });
    }
  };

  clearModule("../services/api");
  clearModule("../services/chat");
  const chatService = require("../services/chat");

  await chatService.explainInChinese("Apple means 苹果.");

  assert.equal(requestOptions.method, "POST");
  assert.equal(requestOptions.url, "http://127.0.0.1:8000/api/tutor/chat");
  assert.match(requestOptions.data.message, /简短.*中文解释/);
  assert.match(requestOptions.data.message, /Apple means 苹果/);
  assert.equal(requestOptions.data.context.mode, "chat");
});

test("text and explain replies clear stale voice audio state", async () => {
  let pageDefinition;
  let destroyedAudioContexts = 0;
  const playedSources = [];
  const recorderCallbacks = {};

  global.wx = {
    createInnerAudioContext() {
      return {
        destroy() {
          destroyedAudioContexts += 1;
        },
        play() {
          playedSources.push(this.source);
        },
        set src(value) {
          this.source = value;
        },
        stop() {}
      };
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
        start() {},
        stop() {}
      };
    },
    getStorageSync() {
      return "test_miniprogram_client_000001";
    },
    setStorageSync() {},
    request(options) {
      options.success({ statusCode: 200, data: { age: 8, grade: 3, english_level: "beginner" } });
    }
  };
  global.Page = (definition) => {
    pageDefinition = definition;
  };

  clearModule("../services/audio-player");
  clearModule("../services/recorder");
  clearModule("../pages/chat/index");
  require("../pages/chat/index");

  const chatService = require("../services/chat");
  const audioPlayer = require("../services/audio-player");
  const voiceService = require("../services/voice");
  chatService.sendMessage = async () => ({
    reply: "A fresh text reply.",
    repeat_text: "A fresh text reply",
    suggested_actions: ["repeat", "explain_zh"]
  });
  let explainedReply = "";
  chatService.explainInChinese = async (reply) => {
    explainedReply = reply;
    return {
      reply: "这是简短中文解释。",
      repeat_text: "Try again",
      suggested_actions: ["repeat", "explain_zh"]
    };
  };
  voiceService.resolveAudioUrl = (path) => `http://127.0.0.1:8000${path}`;
  voiceService.turn = async () => ({
    transcript: "apple 怎么说",
    reply: "Apple.",
    repeat_text: "apple",
    audio_url: "/api/voice/media/current",
    suggested_actions: ["listen", "repeat", "explain_zh"]
  });

  const page = {
    ...pageDefinition,
    data: {
      ...pageDefinition.data,
      profileStatus: "ready",
      messages: [...pageDefinition.data.messages],
      suggestedActions: [
        { id: "listen", label: "再听" },
        { id: "explain_zh", label: "中文讲讲" }
      ]
    },
    setData(update) {
      Object.assign(this.data, update);
    },
    voiceAudioUrl: "http://127.0.0.1:8000/api/voice/media/old"
  };
  audioPlayer.play(page.voiceAudioUrl);

  await page.onSend({ detail: { value: "hello" } });

  assert.equal(page.voiceAudioUrl, "");
  assert.equal(destroyedAudioContexts, 1);
  assert.deepEqual(
    page.data.suggestedActions.map((action) => action.id),
    ["repeat", "explain_zh"]
  );

  page.voiceAudioUrl = "http://127.0.0.1:8000/api/voice/media/current";
  audioPlayer.play(page.voiceAudioUrl);
  await page.onSuggestedAction({
    currentTarget: { dataset: { action: "explain_zh" } }
  });

  assert.equal(explainedReply, "A fresh text reply.");
  assert.equal(page.voiceAudioUrl, "");
  assert.equal(destroyedAudioContexts, 2);
  assert.equal(page.data.actionLoading, false);
  assert.equal(
    page.data.suggestedActions.some((action) => action.id === "listen"),
    false
  );

  await page.completeVoiceTurn({
    duration: 1000,
    tempFilePath: "/tmp/current.mp3"
  });

  assert.equal(
    page.voiceAudioUrl,
    "http://127.0.0.1:8000/api/voice/media/current"
  );
  assert.equal(playedSources.at(-1), page.voiceAudioUrl);
  assert.equal(
    page.data.suggestedActions.some((action) => action.id === "listen"),
    true
  );

  page.onLoad();
  page.onUnload();
  page.setData({ recorderMessage: "page unloaded" });
  recorderCallbacks.start();

  assert.equal(page.data.recorderMessage, "page unloaded");
  assert.equal(destroyedAudioContexts, 3);
});
