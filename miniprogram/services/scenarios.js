const api = require("./api");

function list() {
  return api.get("/api/scenarios");
}

function start(sceneId) {
  return api.post(`/api/scenarios/${sceneId}/sessions`, {});
}

function turn(sessionId, message) {
  return api.post(`/api/scenarios/sessions/${sessionId}/turn`, { message });
}

function voiceTurn(sessionId, filePath) {
  return api.upload(`/api/scenarios/sessions/${sessionId}/voice-turn`, filePath);
}

function complete(sessionId) {
  return api.post(`/api/scenarios/sessions/${sessionId}/complete`, {});
}

function resolveAudioUrl(path) {
  return api.resolveUrl(path);
}

module.exports = { list, start, turn, voiceTurn, complete, resolveAudioUrl };
