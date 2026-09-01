const { API_BASE_URL } = require("../config/api");
const clientIdService = require("./client-id");

function buildUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL.replace(/\/$/, "")}${normalizedPath}`;
}

function isSuccessful(statusCode) {
  return statusCode >= 200 && statusCode < 300;
}

function createUnavailableError(statusCode, path = "") {
  const isProfilePath = path === "/api/student/profile";
  const requiresProfile = path.startsWith("/api/scenarios") ||
    path.startsWith("/api/photo") || path.startsWith("/api/textbooks") || [
    "/api/tutor/chat",
    "/api/voice/turn",
    "/api/pronunciation/evaluate"
  ].includes(path);
  const code =
    statusCode === 404 && isProfilePath
      ? "PROFILE_NOT_FOUND"
      : statusCode === 409 && requiresProfile
        ? "PROFILE_REQUIRED"
        : statusCode === 400 || statusCode === 422
          ? "API_VALIDATION"
          : "API_UNAVAILABLE";
  const error = new Error(code);
  error.code = code;
  error.statusCode = statusCode;
  return error;
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl(path),
      method,
      data,
      header: {
        "content-type": "application/json",
        "X-Client-Id": clientIdService.getClientId()
      },
      success(response) {
        if (isSuccessful(response.statusCode)) {
          resolve(response.data);
          return;
        }

        reject(createUnavailableError(response.statusCode, path));
      },
      fail() {
        reject(createUnavailableError(undefined, path));
      }
    });
  });
}

function get(path) {
  return request("GET", path);
}

function post(path, body) {
  return request("POST", path, body);
}

function put(path, body) {
  return request("PUT", path, body);
}

function upload(path, file, formData = {}) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: buildUrl(path),
      filePath: file,
      formData,
      header: {
        "X-Client-Id": clientIdService.getClientId()
      },
      name: "file",
      success(response) {
        if (!isSuccessful(response.statusCode)) {
          reject(createUnavailableError(response.statusCode, path));
          return;
        }

        try {
          resolve(JSON.parse(response.data));
        } catch (error) {
          resolve(response.data);
        }
      },
      fail() {
        reject(createUnavailableError(undefined, path));
      }
    });
  });
}

module.exports = {
  get,
  post,
  put,
  upload,
  resolveUrl: buildUrl
};
