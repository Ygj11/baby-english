const { API_BASE_URL } = require("../config/api");

function buildUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL.replace(/\/$/, "")}${normalizedPath}`;
}

function isSuccessful(statusCode) {
  return statusCode >= 200 && statusCode < 300;
}

function createUnavailableError(statusCode) {
  const error = new Error("Service unavailable");
  error.code = "API_UNAVAILABLE";
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
        "content-type": "application/json"
      },
      success(response) {
        if (isSuccessful(response.statusCode)) {
          resolve(response.data);
          return;
        }

        reject(createUnavailableError(response.statusCode));
      },
      fail() {
        reject(createUnavailableError());
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

function upload(path, file, formData = {}) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: buildUrl(path),
      filePath: file,
      formData,
      name: "file",
      success(response) {
        if (!isSuccessful(response.statusCode)) {
          reject(createUnavailableError(response.statusCode));
          return;
        }

        try {
          resolve(JSON.parse(response.data));
        } catch (error) {
          resolve(response.data);
        }
      },
      fail() {
        reject(createUnavailableError());
      }
    });
  });
}

module.exports = {
  get,
  post,
  upload,
  resolveUrl: buildUrl
};
