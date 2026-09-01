const api = require("./api");

function list() {
  return api.get("/api/textbooks");
}

function units(textbookId) {
  return api.get(`/api/textbooks/${textbookId}/units`);
}

function current() {
  return api.get("/api/textbooks/current");
}

function select(textbookId, currentUnitNo = null) {
  return api.put("/api/textbooks/current", {
    textbook_id: textbookId,
    current_unit_no: currentUnitNo
  });
}

function ask(question) {
  return api.post("/api/textbooks/ask", { question });
}

module.exports = { list, units, current, select, ask };
