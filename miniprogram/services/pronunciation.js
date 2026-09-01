const api = require("./api");

function evaluate(filePath, referenceText) {
  return api.upload("/api/pronunciation/evaluate", filePath, {
    reference_text: referenceText
  });
}

module.exports = {
  evaluate
};
