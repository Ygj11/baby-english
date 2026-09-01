const api = require("./api");

function analyze(filePath) {
  return api.upload("/api/photo/analyze", filePath);
}

function listen(recordId) {
  return api.post(`/api/photo/records/${recordId}/listen`, {});
}

function resolveAudioUrl(path) {
  return api.resolveUrl(path);
}

module.exports = {
  analyze,
  listen,
  resolveAudioUrl
};
