const api = require("./api");

function getProfile() {
  return api.get("/api/student/profile");
}

function saveProfile(profile) {
  return api.put("/api/student/profile", profile);
}

module.exports = {
  getProfile,
  saveProfile
};
