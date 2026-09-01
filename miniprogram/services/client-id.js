const STORAGE_KEY = "babyEnglishClientId";
const CLIENT_ID_PATTERN = /^[A-Za-z0-9_-]{16,64}$/;

function createClientId() {
  const randomHex = () =>
    Math.floor(Math.random() * 0xffffffff)
      .toString(16)
      .padStart(8, "0");
  return `be_${randomHex()}${randomHex()}${randomHex()}${randomHex()}`;
}

function getClientId() {
  const stored = String(wx.getStorageSync(STORAGE_KEY) || "").trim();
  if (CLIENT_ID_PATTERN.test(stored)) {
    return stored;
  }

  const clientId = createClientId();
  wx.setStorageSync(STORAGE_KEY, clientId);
  return clientId;
}

module.exports = {
  STORAGE_KEY,
  createClientId,
  getClientId
};
