const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function clearModule(modulePath) {
  delete require.cache[require.resolve(modulePath)];
}

test("Home textbook entry preserves five entries and opens backend catalogue", () => {
  let definition;
  global.wx = {
    getStorageSync() { return "textbook_home_client_0001"; },
    setStorageSync() {},
    request() {}
  };
  global.Page = (value) => { definition = value; };
  clearModule("../pages/home/index");
  require("../pages/home/index");
  const entry = definition.data.entries.find((item) => item.id === "textbook");
  assert.equal(entry.url, "/pages/textbooks/index");
  assert.equal(definition.data.entries.length, 5);
});

test("textbook service reuses shared client for catalogue, selection, units, and ask", async () => {
  const requests = [];
  global.wx = {
    getStorageSync() { return "textbook_service_client_0001"; },
    setStorageSync() {},
    request(options) {
      requests.push(options);
      options.success({ statusCode: 200, data: {} });
    }
  };
  for (const modulePath of ["../services/client-id", "../services/api", "../services/textbooks"]) {
    clearModule(modulePath);
  }
  const textbooks = require("../services/textbooks");
  await textbooks.list();
  await textbooks.current();
  await textbooks.units(9);
  await textbooks.select(9, 2);
  await textbooks.ask("What is Milo?");
  assert.deepEqual(
    requests.map((item) => item.url.replace("http://127.0.0.1:8000", "")),
    [
      "/api/textbooks",
      "/api/textbooks/current",
      "/api/textbooks/9/units",
      "/api/textbooks/current",
      "/api/textbooks/ask"
    ]
  );
  assert.deepEqual(requests[3].data, { textbook_id: 9, current_unit_no: 2 });
  assert.deepEqual(requests[4].data, { question: "What is Milo?" });
  assert.equal(requests[4].header["X-Client-Id"], "textbook_service_client_0001");
});

test("catalogue renders backend books, persists selection, and has safe empty state", async () => {
  let definition;
  const navigations = [];
  global.wx = { navigateTo(options) { navigations.push(options.url); } };
  global.Page = (value) => { definition = value; };
  clearModule("../services/textbooks");
  clearModule("../pages/textbooks/index");
  const textbooks = require("../services/textbooks");
  const serverBook = { id: 4, title: "Server Synthetic Book", publisher: "Server", selected: false };
  textbooks.list = async () => [serverBook];
  let selected;
  textbooks.select = async (id, unitNo) => { selected = { id, unitNo }; return {}; };
  require("../pages/textbooks/index");
  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update); }
  };
  await page.onLoad();
  assert.deepEqual(page.data.books, [serverBook]);
  await page.chooseBook({ currentTarget: { dataset: { textbookId: 4 } } });
  assert.deepEqual(selected, { id: 4, unitNo: null });
  assert.equal(navigations.at(-1), "/pages/textbook/index");
  const wxml = fs.readFileSync(path.join(__dirname, "../pages/textbooks/index.wxml"), "utf8");
  assert.match(wxml, /暂时还没有可用课本/);
});

test("learning page persists unit, prevents duplicate ask, and renders source state", async () => {
  let definition;
  global.wx = {};
  global.Page = (value) => { definition = value; };
  clearModule("../services/textbooks");
  clearModule("../pages/textbook/index");
  const textbooks = require("../services/textbooks");
  textbooks.current = async () => ({
    textbook: { id: 4, title: "Server Synthetic Book" },
    current_unit_no: 1,
    units: [{ unit_no: 1, title: "Toy Friends" }, { unit_no: 2, title: "Bird Songs" }]
  });
  let selected;
  textbooks.select = async (id, unitNo) => { selected = { id, unitNo }; };
  let resolveAsk;
  let askCalls = 0;
  textbooks.ask = async () => {
    askCalls += 1;
    return new Promise((resolve) => { resolveAsk = resolve; });
  };
  require("../pages/textbook/index");
  const page = {
    ...definition,
    data: { ...definition.data },
    setData(update) { Object.assign(this.data, update); }
  };
  await page.onLoad();
  assert.equal(page.data.unitIndex, 0);
  await page.changeUnit({ detail: { value: "1" } });
  assert.deepEqual(selected, { id: 4, unitNo: 2 });
  page.setData({ question: "What is Pip?" });
  const pending = page.askQuestion();
  await page.askQuestion();
  assert.equal(askCalls, 1);
  resolveAsk({
    answer: "Pip is a yellow bird.",
    found: true,
    sources: [{ unit_no: 2, unit_title: "Bird Songs", lesson: "Lesson 1", page: 12 }]
  });
  await pending;
  assert.equal(page.data.state, "answered");
  assert.equal(page.data.answer.sources[0].page, 12);

  textbooks.ask = async () => ({ answer: "没有找到。", found: false, sources: [] });
  await page.askQuestion();
  assert.equal(page.data.state, "not-found");
  const wxml = fs.readFileSync(path.join(__dirname, "../pages/textbook/index.wxml"), "utf8");
  assert.match(wxml, /answer\.sources/);
  assert.doesNotMatch(
    fs.readFileSync(path.join(__dirname, "../pages/textbook/index.js"), "utf8"),
    /Milo is|Pip is|人民教育|PEP/
  );
});
