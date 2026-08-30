const recorderManager = wx.getRecorderManager();

const listeners = {
  error: [],
  start: [],
  stop: []
};

let cancelRequested = false;

function emit(event, payload) {
  listeners[event].forEach((listener) => listener(payload));
}

function subscribe(event, listener) {
  listeners[event].push(listener);
  return () => {
    const index = listeners[event].indexOf(listener);
    if (index >= 0) {
      listeners[event].splice(index, 1);
    }
  };
}

recorderManager.onStart(() => {
  emit("start");
});

recorderManager.onStop((result) => {
  const wasCancelled = cancelRequested;
  cancelRequested = false;

  if (!wasCancelled) {
    emit("stop", {
      tempFilePath: result.tempFilePath,
      duration: result.duration
    });
  }
});

recorderManager.onError(() => {
  cancelRequested = false;
  emit("error");
});

function start() {
  cancelRequested = false;
  recorderManager.start({
    duration: 60000,
    sampleRate: 16000,
    numberOfChannels: 1,
    encodeBitRate: 48000,
    format: "mp3"
  });
}

function stop() {
  recorderManager.stop();
}

function cancel() {
  cancelRequested = true;
  recorderManager.stop();
}

function onStart(listener) {
  return subscribe("start", listener);
}

function onStop(listener) {
  return subscribe("stop", listener);
}

function onError(listener) {
  return subscribe("error", listener);
}

module.exports = {
  start,
  stop,
  cancel,
  onStart,
  onStop,
  onError
};
