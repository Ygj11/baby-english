const api = require("./api");

function sendMessage(message) {
  return api.post("/api/tutor/chat", {
    message,
    student: {
      age: 8,
      grade: 3,
      english_level: "beginner"
    },
    context: {
      mode: "chat"
    }
  });
}

function buildChineseExplanationPrompt(lastAssistantReply) {
  const context = String(lastAssistantReply || "").trim().slice(0, 1600);
  if (!context) {
    throw new Error("A previous assistant reply is required.");
  }

  return `请用简短、适合小学生的中文解释你刚才的回答：“${context}”`;
}

function explainInChinese(lastAssistantReply) {
  return sendMessage(buildChineseExplanationPrompt(lastAssistantReply));
}

module.exports = {
  buildChineseExplanationPrompt,
  explainInChinese,
  sendMessage
};
