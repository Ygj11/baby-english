const assert = require("node:assert/strict");
const test = require("node:test");

function clearModule(modulePath) {
  delete require.cache[require.resolve(modulePath)];
}

test("client id is generated once, stored, and reused", () => {
  let stored = "";
  let writes = 0;
  global.wx = {
    getStorageSync() {
      return stored;
    },
    setStorageSync(key, value) {
      assert.equal(key, "babyEnglishClientId");
      stored = value;
      writes += 1;
    }
  };

  clearModule("../services/client-id");
  const clientId = require("../services/client-id");
  const first = clientId.getClientId();
  const second = clientId.getClientId();

  assert.match(first, /^[A-Za-z0-9_-]{16,64}$/);
  assert.equal(second, first);
  assert.equal(writes, 1);
});

test("request and upload inject the same client id", async () => {
  const calls = [];
  const stableId = "test_api_client_00000000000001";
  global.wx = {
    getStorageSync() {
      return stableId;
    },
    setStorageSync() {},
    request(options) {
      calls.push(options);
      options.success({ statusCode: 200, data: { status: "ok" } });
    },
    uploadFile(options) {
      calls.push(options);
      options.success({ statusCode: 200, data: '{"text":"ok"}' });
    }
  };

  clearModule("../services/client-id");
  clearModule("../services/api");
  const api = require("../services/api");
  await api.get("/api/health");
  await api.upload("/api/voice/transcribe", "/tmp/audio.mp3");

  assert.equal(calls[0].header["X-Client-Id"], stableId);
  assert.equal(calls[1].header["X-Client-Id"], stableId);
});

test("chat and voice no longer send hardcoded profile fields", async () => {
  const requests = [];
  global.wx = {
    getStorageSync() {
      return "test_services_client_000000001";
    },
    setStorageSync() {},
    request(options) {
      requests.push(options);
      options.success({ statusCode: 200, data: { reply: "ok" } });
    },
    uploadFile(options) {
      requests.push(options);
      options.success({ statusCode: 200, data: '{"reply":"ok"}' });
    }
  };

  for (const path of [
    "../services/client-id",
    "../services/api",
    "../services/chat",
    "../services/voice"
  ]) {
    clearModule(path);
  }
  const chat = require("../services/chat");
  const voice = require("../services/voice");
  await chat.sendMessage("hello");
  await voice.turn("/tmp/audio.mp3");

  assert.deepEqual(requests[0].data, {
    message: "hello",
    context: { mode: "chat" }
  });
  assert.equal("student" in requests[0].data, false);
  assert.deepEqual(requests[1].formData, {});
});

test("profile service uses GET and idempotent PUT contracts", async () => {
  const requests = [];
  global.wx = {
    getStorageSync() {
      return "test_profile_service_00000001";
    },
    setStorageSync() {},
    request(options) {
      requests.push(options);
      options.success({
        statusCode: 200,
        data: { age: 9, grade: 4, english_level: "beginner" }
      });
    }
  };

  for (const path of ["../services/client-id", "../services/api", "../services/profile"]) {
    clearModule(path);
  }
  const profile = require("../services/profile");
  await profile.getProfile();
  await profile.saveProfile({ age: 9, grade: 4, english_level: "beginner" });

  assert.equal(requests[0].method, "GET");
  assert.match(requests[0].url, /\/api\/student\/profile$/);
  assert.equal(requests[1].method, "PUT");
  assert.deepEqual(requests[1].data, {
    age: 9,
    grade: 4,
    english_level: "beginner"
  });
});

test("profile page loads stored values and saves current selection", async () => {
  let pageDefinition;
  const requestCalls = [];
  global.wx = {
    getStorageSync() {
      return "test_profile_page_0000000001";
    },
    setStorageSync() {},
    request(options) {
      requestCalls.push(options);
      options.success({
        statusCode: 200,
        data: { age: 11, grade: 5, english_level: "elementary" }
      });
    }
  };
  global.Page = (definition) => {
    pageDefinition = definition;
  };

  for (const path of [
    "../services/client-id",
    "../services/api",
    "../services/profile",
    "../pages/profile/index"
  ]) {
    clearModule(path);
  }
  require("../pages/profile/index");
  const page = {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(update) {
      Object.assign(this.data, update);
    }
  };

  await page.onLoad();
  assert.equal(page.data.ageIndex, 5);
  assert.equal(page.data.gradeIndex, 4);
  assert.equal(page.data.levelIndex, 2);
  page.onAgeChange({ detail: { value: "1" } });
  await page.save();

  assert.equal(requestCalls.at(-1).method, "PUT");
  assert.deepEqual(requestCalls.at(-1).data, {
    age: 7,
    grade: 5,
    english_level: "elementary"
  });
  assert.match(page.data.statusMessage, /保存成功/);
});

test("chat page guides to settings when profile is missing", async () => {
  let pageDefinition;
  let navigatedTo = "";
  global.wx = {
    createInnerAudioContext() {
      return { destroy() {}, play() {}, stop() {} };
    },
    getRecorderManager() {
      return {
        onError() {},
        onStart() {},
        onStop() {},
        start() {},
        stop() {}
      };
    },
    getStorageSync() {
      return "test_chat_missing_profile_00001";
    },
    setStorageSync() {},
    request(options) {
      options.success({ statusCode: 404, data: { detail: "missing" } });
    },
    navigateTo(options) {
      navigatedTo = options.url;
    }
  };
  global.Page = (definition) => {
    pageDefinition = definition;
  };

  for (const path of [
    "../services/client-id",
    "../services/api",
    "../services/profile",
    "../pages/chat/index"
  ]) {
    clearModule(path);
  }
  require("../pages/chat/index");
  const page = {
    ...pageDefinition,
    data: { ...pageDefinition.data },
    setData(update) {
      Object.assign(this.data, update);
    }
  };

  await page.checkProfile();
  assert.equal(page.data.profileRequired, true);
  assert.equal(page.data.profileStatus, "missing");
  page.goToProfile();
  assert.equal(navigatedTo, "/pages/profile/index");
});
