function chooseSingleImage(sourceType) {
  const source = sourceType === "album" ? "album" : "camera";
  return new Promise((resolve, reject) => {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sizeType: ["compressed"],
      sourceType: [source],
      success(result) {
        const selected = result.tempFiles && result.tempFiles[0];
        if (!selected || !selected.tempFilePath) {
          reject(new Error("IMAGE_NOT_SELECTED"));
          return;
        }
        resolve(selected.tempFilePath);
      },
      fail(error) {
        reject(error || new Error("IMAGE_NOT_SELECTED"));
      }
    });
  });
}

module.exports = {
  chooseSingleImage
};
