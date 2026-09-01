const api = require("./api");

function transcribe(filePath) {
  return api.upload("/api/voice/transcribe", filePath);
}

function turn(filePath) {
  return api.upload("/api/voice/turn", filePath);
}

function resolveAudioUrl(path) {
  return api.resolveUrl(path);
}

module.exports = {
  transcribe,
  turn,
  resolveAudioUrl
};
