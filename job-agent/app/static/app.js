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
const analyzeButton = document.querySelector("#analyze-button");
const profilePanel = document.querySelector("#profile-panel");
const profileProvider = document.querySelector("#profile-provider");
const profileModel = document.querySelector("#profile-model");
const profileBasic = document.querySelector("#profile-basic");
const profileTargetBlock = document.querySelector("#profile-target-block");
const profileTargets = document.querySelector("#profile-targets");
const profileSections = document.querySelector("#profile-sections");
const profileWarnings = document.querySelector("#profile-warnings");
const profileWarningList = document.querySelector("#profile-warning-list");
const jobMatchPanel = document.querySelector("#job-match-panel");
const jobDescription = document.querySelector("#job-description");
const jobCharacterCount = document.querySelector("#job-character-count");
const parseJobButton = document.querySelector("#parse-job-button");
const jobPreview = document.querySelector("#job-preview");
const matchPanel = document.querySelector("#match-panel");
const matchProvider = document.querySelector("#match-provider");
const matchModel = document.querySelector("#match-model");
const matchScore = document.querySelector("#match-score");
const matchRecommendation = document.querySelector("#match-recommendation");
const matchSummary = document.querySelector("#match-summary");
const matchDimensions = document.querySelector("#match-dimensions");
const matchStrengths = document.querySelector("#match-strengths");
const matchGaps = document.querySelector("#match-gaps");
const matchSuggestions = document.querySelector("#match-suggestions");
const matchAssessments = document.querySelector("#match-assessments");

let currentFile = null;
let currentCandidateProfile = null;
let currentJobProfile = null;

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
  profilePanel.classList.add("is-hidden");
  jobMatchPanel.classList.add("is-hidden");
  matchPanel.classList.add("is-hidden");
  currentCandidateProfile = null;
  currentJobProfile = null;
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined && text !== null) element.textContent = text;
  return element;
}

function displayValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(" · ") : "未提供";
  return value || "未提供";
}

function addSummaryItem(label, value) {
  const item = createElement("div", "profile-summary-item");
  item.append(createElement("span", "", label), createElement("strong", "", displayValue(value)));
  profileBasic.append(item);
}

function addEvidence(container, evidence) {
  if (!evidence?.length) return;
  const details = createElement("details", "evidence-list");
  details.append(createElement("summary", "", `查看原文证据（${evidence.length}）`));
  for (const item of evidence) {
    const quote = createElement("blockquote", "", item.quote);
    if (item.source_section) quote.title = `来源章节：${item.source_section}`;
    details.append(quote);
  }
  container.append(details);
}

function addList(container, values) {
  if (!values?.length) return;
  const list = createElement("ul");
  for (const value of values) list.append(createElement("li", "", value));
  container.append(list);
}

function addProfileSection(title, items, renderer) {
  if (!items?.length) return;
  const section = createElement("section", "profile-section");
  section.append(createElement("h3", "", title));
  for (const item of items) section.append(renderer(item));
  profileSections.append(section);
}

function createCard(title, meta, description, bullets, evidence) {
  const card = createElement("article", "profile-card");
  card.append(createElement("h4", "", title || "未命名"));
  if (meta) card.append(createElement("p", "profile-card-meta", meta));
  if (description) card.append(createElement("p", "", description));
  addList(card, bullets);
  addEvidence(card, evidence);
  return card;
}

function renderProfile(data) {
  const profile = data.profile;
  profileBasic.replaceChildren();
  profileTargets.replaceChildren();
  profileSections.replaceChildren();
  profileWarningList.replaceChildren();

  profileProvider.textContent = data.provider;
  profileModel.textContent = data.model;
  addSummaryItem("姓名", profile.basic_info.name);
  addSummaryItem("邮箱", profile.basic_info.email);
  addSummaryItem("电话", profile.basic_info.phone);
  addSummaryItem("所在地", profile.basic_info.location);

  if (profile.job_targets.length) {
    for (const target of profile.job_targets) {
      profileTargets.append(createElement("span", "tag", target));
    }
    profileTargetBlock.classList.remove("is-hidden");
  } else {
    profileTargetBlock.classList.add("is-hidden");
  }

  if (profile.summary) {
    addProfileSection("个人概述", [profile.summary], (summary) =>
      createCard("简历概述", "", summary, [], []),
    );
  }
  addProfileSection("教育经历", profile.education, (item) =>
    createCard(
      item.institution,
      [item.degree, item.major, item.start_date, item.end_date, item.gpa]
        .filter(Boolean)
        .join(" · "),
      "",
      item.courses,
      item.evidence,
    ),
  );
  addProfileSection("专业技能", profile.skills, (item) =>
    createCard(
      item.name,
      [item.category, item.level].filter(Boolean).join(" · "),
      "",
      [],
      item.evidence,
    ),
  );
  addProfileSection("项目经历", profile.projects, (item) =>
    createCard(
      item.name,
      [item.role, item.start_date, item.end_date].filter(Boolean).join(" · "),
      item.description,
      [...item.technologies.map((value) => `技术：${value}`), ...item.highlights],
      item.evidence,
    ),
  );
  addProfileSection("实践经历", profile.experiences, (item) =>
    createCard(
      item.organization,
      [item.role, item.start_date, item.end_date].filter(Boolean).join(" · "),
      "",
      item.highlights,
      item.evidence,
    ),
  );
  addProfileSection("证书与荣誉", profile.certificates, (item) =>
    createCard(item.name, item.date || "", "", [], item.evidence),
  );

  if (profile.warnings.length) {
    for (const warning of profile.warnings) {
      profileWarningList.append(createElement("li", "", warning));
    }
    profileWarnings.classList.remove("is-hidden");
  } else {
    profileWarnings.classList.add("is-hidden");
  }

  profilePanel.classList.remove("is-hidden");
  currentCandidateProfile = profile;
  jobMatchPanel.classList.remove("is-hidden");
  profilePanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function selectedProvider() {
  return document.querySelector('input[name="provider"]:checked')?.value ?? "openai";
}

function renderJob(profile) {
  jobPreview.replaceChildren();
  const title = createElement("h3", "job-preview-title", profile.title || "未识别岗位名称");
  const meta = [profile.company, profile.location, profile.education].filter(Boolean).join(" · ");
  jobPreview.append(title, createElement("p", "job-preview-meta", meta || "未提供公司、地点或学历信息"));
  const groups = [
    ["必备技能", profile.required_skills],
    ["加分技能", profile.preferred_skills],
    ["岗位职责", profile.responsibilities],
  ];
  for (const [label, values] of groups) {
    if (!values?.length) continue;
    const section = createElement("section", "job-preview-section");
    section.append(createElement("h4", "", label));
    addList(section, values);
    jobPreview.append(section);
  }
  const button = createElement("button", "analysis-button match-button");
  button.type = "button";
  button.id = "analyze-match-button";
  button.innerHTML = "<span><strong>生成匹配报告</strong><small>基于候选人画像与岗位要求评分</small></span><span>AI →</span>";
  button.addEventListener("click", analyzeMatch);
  jobPreview.append(button);
}

function fillList(element, values, emptyText) {
  element.replaceChildren();
  for (const value of values?.length ? values : [emptyText]) element.append(createElement("li", "", value));
}

function renderMatch(data) {
  const result = data.result;
  matchProvider.textContent = data.provider;
  matchModel.textContent = data.model;
  matchScore.textContent = result.overall_score;
  matchRecommendation.textContent = result.recommendation;
  matchSummary.textContent = result.summary;
  matchDimensions.replaceChildren();
  for (const item of result.dimensions) {
    const card = createElement("article", "dimension-card");
    card.append(createElement("span", "", `${item.name} · 权重 ${item.weight}%`));
    card.append(createElement("strong", "", item.score));
    const bar = createElement("div", "score-bar");
    const fill = createElement("i");
    fill.style.width = `${item.score}%`;
    bar.append(fill);
    card.append(bar, createElement("p", "", item.reason));
    matchDimensions.append(card);
  }
  fillList(matchStrengths, result.strengths, "暂无明确优势");
  fillList(matchGaps, result.gaps, "暂无明确差距");
  fillList(matchSuggestions, result.resume_suggestions, "暂无优化建议");
  matchAssessments.replaceChildren();
  for (const item of result.assessments) {
    const card = createElement("article", "assessment-card");
    card.append(createElement("span", `assessment-status status-${item.status}`, item.status));
    card.append(createElement("h4", "", item.requirement));
    card.append(createElement("p", "", item.reason));
    addEvidence(card, item.resume_evidence.map((quote) => ({ quote })));
    matchAssessments.append(card);
  }
  matchPanel.classList.remove("is-hidden");
  matchPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function analyzeMatch(event) {
  const button = event?.currentTarget;
  if (!currentCandidateProfile || !currentJobProfile || !button) return;
  clearMessage();
  button.disabled = true;
  const original = button.querySelector("strong").textContent;
  button.querySelector("strong").textContent = "正在计算匹配度...";
  try {
    const response = await fetch("/api/matches/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_profile: currentCandidateProfile,
        job_profile: currentJobProfile,
        provider: selectedProvider(),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `匹配分析失败，服务器返回 ${response.status}。`);
    renderMatch(data);
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "匹配分析失败，请稍后重试。");
  } finally {
    button.disabled = false;
    button.querySelector("strong").textContent = original;
  }
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

analyzeButton.addEventListener("click", async () => {
  const error = validateFile(currentFile);
  if (error) {
    showMessage(error);
    return;
  }

  clearMessage();
  profilePanel.classList.add("is-hidden");
  analyzeButton.disabled = true;
  const originalText = analyzeButton.querySelector("strong").textContent;
  analyzeButton.querySelector("strong").textContent = "正在生成画像...";

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("provider", selectedProvider());

  try {
    const response = await fetch("/api/resumes/analyze", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `画像生成失败，服务器返回 ${response.status}。`);
    }
    renderProfile(data);
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "画像生成失败，请稍后重试。");
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.querySelector("strong").textContent = originalText;
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

jobDescription.addEventListener("input", () => {
  jobCharacterCount.textContent = jobDescription.value.length.toLocaleString("zh-CN");
});

parseJobButton.addEventListener("click", async () => {
  const description = jobDescription.value.trim();
  if (description.length < 20) {
    showMessage("岗位描述至少需要 20 个字符，请粘贴更完整的内容。");
    return;
  }
  clearMessage();
  matchPanel.classList.add("is-hidden");
  parseJobButton.disabled = true;
  parseJobButton.querySelector("span:first-child").textContent = "正在解析岗位...";
  try {
    const response = await fetch("/api/jobs/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description, provider: selectedProvider() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `岗位解析失败，服务器返回 ${response.status}。`);
    currentJobProfile = data.profile;
    renderJob(data.profile);
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "岗位解析失败，请稍后重试。");
  } finally {
    parseJobButton.disabled = false;
    parseJobButton.querySelector("span:first-child").textContent = "解析岗位要求";
  }
});
