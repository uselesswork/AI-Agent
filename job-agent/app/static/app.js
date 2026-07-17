const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(["pdf", "docx", "txt"]);

const fileInput = document.querySelector("#resume-file");
const dropZone = document.querySelector("#drop-zone");
const selectedFile = document.querySelector("#selected-file");
const fileBadge = document.querySelector("#file-badge");
const fileName = document.querySelector("#file-name");
const fileSize = document.querySelector("#file-size");
const changeFileButton = document.querySelector("#change-file");
const parseButton = document.querySelector("#parse-button");
const message = document.querySelector("#message");
const emptyState = document.querySelector("#empty-state");
const resultContent = document.querySelector("#result-content");
const resultType = document.querySelector("#result-type");
const resultCount = document.querySelector("#result-count");
const resultFilename = document.querySelector("#result-filename");
const resumeText = document.querySelector("#resume-text");
const copyButton = document.querySelector("#copy-button");

let currentFile = null;

function extensionOf(filename) {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function showMessage(text) {
  message.textContent = text;
  message.classList.remove("is-hidden");
}

function clearMessage() {
  message.textContent = "";
  message.classList.add("is-hidden");
}

function clearResult() {
  resultContent.classList.add("is-hidden");
  emptyState.classList.remove("is-hidden");
  resumeText.textContent = "";
}

function validateFile(file) {
  if (!file) return "请选择需要解析的简历文件。";
  const extension = extensionOf(file.name);
  if (!ALLOWED_EXTENSIONS.has(extension)) {
    return "文件格式不受支持，请选择 PDF、DOCX 或 TXT。";
  }
  if (file.size === 0) return "文件为空，请重新选择。";
  if (file.size > MAX_FILE_SIZE) return "文件超过 10 MB，请选择更小的文件。";
  return null;
}

function selectFile(file) {
  clearMessage();
  clearResult();

  const error = validateFile(file);
  if (error) {
    currentFile = null;
    parseButton.disabled = true;
    selectedFile.classList.add("is-hidden");
    showMessage(error);
    return;
  }

  currentFile = file;
  fileBadge.textContent = extensionOf(file.name).toUpperCase();
  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  selectedFile.classList.remove("is-hidden");
  parseButton.disabled = false;
}

fileInput.addEventListener("change", () => selectFile(fileInput.files?.[0]));

changeFileButton.addEventListener("click", () => {
  fileInput.value = "";
  fileInput.click();
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  selectFile(event.dataTransfer?.files?.[0]);
});

parseButton.addEventListener("click", async () => {
  const error = validateFile(currentFile);
  if (error) {
    showMessage(error);
    return;
  }

  clearMessage();
  parseButton.disabled = true;
  parseButton.classList.add("is-loading");
  parseButton.querySelector("span:first-child").textContent = "正在解析";

  const formData = new FormData();
  formData.append("file", currentFile);

  try {
    const response = await fetch("/api/resumes/parse", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `解析失败，服务器返回 ${response.status}。`);
    }

    resultType.textContent = data.file_type.toUpperCase();
    resultCount.textContent = Number(data.character_count).toLocaleString("zh-CN");
    resultFilename.textContent = data.filename;
    resumeText.textContent = data.text;
    emptyState.classList.add("is-hidden");
    resultContent.classList.remove("is-hidden");
    resultContent.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    clearResult();
    showMessage(error instanceof Error ? error.message : "解析失败，请稍后重试。");
  } finally {
    parseButton.disabled = false;
    parseButton.classList.remove("is-loading");
    parseButton.querySelector("span:first-child").textContent = "开始解析";
  }
});

copyButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(resumeText.textContent);
    copyButton.textContent = "已复制";
    window.setTimeout(() => {
      copyButton.textContent = "复制文本";
    }, 1600);
  } catch {
    showMessage("浏览器未允许复制，请手动选择正文复制。 ");
  }
});
