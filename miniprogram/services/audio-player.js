let audioContext = null;
let lastSource = "";

function getAudioContext() {
  if (!audioContext) {
    audioContext = wx.createInnerAudioContext();
  }
  return audioContext;
}

function play(source) {
  const context = getAudioContext();
  context.stop();
  context.src = source;
  lastSource = source;
  context.play();
}

function stop() {
  if (audioContext) {
    audioContext.stop();
  }
}

function replay() {
  if (lastSource) {
    play(lastSource);
  }
}

function cleanup() {
  if (audioContext) {
    audioContext.stop();
    audioContext.destroy();
    audioContext = null;
  }
  lastSource = "";
}

module.exports = {
  play,
  stop,
  replay,
  cleanup
};
