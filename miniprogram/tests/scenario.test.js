const assert = require("node:assert/strict");
const test = require("node:test");

function clearModule(path) {
  delete require.cache[require.resolve(path)];
}

test("Home scenario entry navigates to the backend catalogue page", () => {
  let definition;
  global.wx = {
    getStorageSync() { return "scenario_home_client_000001"; },
    setStorageSync() {},
    request() {}
  };
  global.Page = (value) => { definition = value; };
  clearModule("../pages/home/index");
  require("../pages/home/index");
  const entry = definition.data.entries.find((item) => item.id === "scenario");
  assert.equal(entry.url, "/pages/scenarios/index");
  assert.equal(definition.data.entries.length, 5);
});

test("scenario service uses session-owned text, voice and completion endpoints", async () => {
  const requests = [];
  const uploads = [];
  global.wx = {
    getStorageSync() { return "scenario_service_client_0001"; },
    setStorageSync() {},
    request(options) {
      requests.push(options);
      options.success({ statusCode: 200, data: {} });
    },
    uploadFile(options) {
      uploads.push(options);
      options.success({ statusCode: 200, data: "{}" });
    }
  };
  for (const path of ["../services/client-id", "../services/api", "../services/scenarios"]) clearModule(path);
  const scenarios = require("../services/scenarios");
  await scenarios.list();
  await scenarios.start("restaurant");
  await scenarios.turn(12, "A sandwich, please.");
  await scenarios.voiceTurn(12, "/tmp/scene.mp3");
  await scenarios.complete(12);
  assert.deepEqual(requests.map((item) => item.url.replace("http://127.0.0.1:8000", "")), [
    "/api/scenarios",
    "/api/scenarios/restaurant/sessions",
    "/api/scenarios/sessions/12/turn",
    "/api/scenarios/sessions/12/complete"
  ]);
  assert.deepEqual(requests[2].data, { message: "A sandwich, please." });
  assert.match(uploads[0].url, /\/api\/scenarios\/sessions\/12\/voice-turn$/);
});

test("catalogue renders only scenes returned by backend", async () => {
  let definition;
  global.wx = {};
  global.Page = (value) => { definition = value; };
  clearModule("../services/scenarios");
  clearModule("../pages/scenarios/index");
  const scenarios = require("../services/scenarios");
  scenarios.list = async () => [{ id: "server-only", title_zh: "服务端场景" }];
  require("../pages/scenarios/index");
  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update); }
  };
  await page.onLoad();
  assert.deepEqual(page.data.scenes, [{ id: "server-only", title_zh: "服务端场景" }]);
});

test("scenario page renders opener and routes text, voice, goal pronunciation and completion", async () => {
  let definition;
  const recorderCallbacks = {};
  global.wx = {
    createInnerAudioContext() {
      return { destroy() {}, play() {}, stop() {}, set src(value) { this.source = value; } };
    },
    getRecorderManager() {
      return {
        onError(callback) { recorderCallbacks.error = callback; },
        onStart(callback) { recorderCallbacks.start = callback; },
        onStop(callback) { recorderCallbacks.stop = callback; },
        start() { recorderCallbacks.start(); },
        stop() {}
      };
    },
    getStorageSync() { return "scenario_page_client_000001"; },
    setStorageSync() {}
  };
  global.Page = (value) => { definition = value; };
  for (const path of [
    "../services/audio-player", "../services/recorder", "../services/scenarios",
    "../services/pronunciation", "../pages/scenario/index"
  ]) clearModule(path);
  const scenarios = require("../services/scenarios");
  const pronunciation = require("../services/pronunciation");
  const scene = {
    id: "restaurant", icon: "🍽️", title: "At the Restaurant", title_zh: "餐厅点餐",
    partner_role: "a friendly waiter",
    goals: [{ id: "order_food", title_zh: "点餐", practice_phrase: "Can I have a sandwich, please?", hint_zh: "试试" }],
    progress: { completed_goal_ids: [], missing_goal_ids: ["order_food"], completed_count: 0, total_count: 1 }
  };
  const calls = { text: 0, voice: 0, pronunciation: 0, complete: 0 };
  scenarios.start = async () => ({ session_id: 9, scene, opening_message: "Hello! What would you like?", progress: scene.progress });
  scenarios.turn = async (id, text) => { calls.text += 1; assert.equal(id, 9); assert.equal(text, "A sandwich, please."); return { reply: "Great choice!" }; };
  scenarios.voiceTurn = async (id, path) => { calls.voice += 1; assert.equal(path, "/tmp/voice.mp3"); return { transcript: "Water, please.", reply: "Here you are.", audio_url: "/api/voice/media/scene" }; };
  scenarios.resolveAudioUrl = (path) => path;
  scenarios.complete = async () => { calls.complete += 1; return { summary: "完成点餐目标！", tip: "再练饮料。", progress: { completed_goal_ids: ["order_food"], missing_goal_ids: [], completed_count: 1, total_count: 1 } }; };
  pronunciation.evaluate = async (path, phrase) => { calls.pronunciation += 1; assert.equal(path, "/tmp/practice.mp3"); assert.equal(phrase, scene.goals[0].practice_phrase); return { overall_score: 88, accuracy_score: 86, fluency_score: 90, feedback: "很棒！" }; };
  require("../pages/scenario/index");
  const page = {
    ...definition,
    data: { ...definition.data, messages: [] },
    setData(update) { Object.assign(this.data, update); }
  };
  await page.onLoad({ scene_id: "restaurant" });
  assert.equal(page.data.messages[0].content[0].data, "Hello! What would you like?");
  await page.onSend({ detail: { value: "A sandwich, please." } });
  assert.equal(calls.text, 1);

  page.startVoice();
  await page.completeRecording({ tempFilePath: "/tmp/voice.mp3", duration: 900 });
  assert.equal(calls.voice, 1);

  page.practiceGoal({ currentTarget: { dataset: { phrase: scene.goals[0].practice_phrase } } });
  await page.completeRecording({ tempFilePath: "/tmp/practice.mp3", duration: 900 });
  assert.equal(calls.pronunciation, 1);
  assert.equal(page.data.pronunciationResult.overall_score, 88);

  await page.completeSession();
  assert.equal(calls.complete, 1);
  assert.equal(page.data.completed, true);
  assert.equal(page.data.completion.summary, "完成点餐目标！");
  assert.equal(page.data.scene.goals[0].completed, true);
  page.onUnload();
});
