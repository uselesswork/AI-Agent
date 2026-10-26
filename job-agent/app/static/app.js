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
const saveJobUrl = document.querySelector("#save-job-url");
const saveStatus = document.querySelector("#save-status");
const saveNotes = document.querySelector("#save-notes");
const retainSourceText = document.querySelector("#retain-source-text");
const saveApplicationButton = document.querySelector("#save-application-button");
const applicationFilter = document.querySelector("#application-filter");
const applicationSort = document.querySelector("#application-sort");
const applicationCount = document.querySelector("#application-count");
const applicationGrid = document.querySelector("#application-grid");
const refreshApplications = document.querySelector("#refresh-applications");

let currentFile = null;
let currentCandidateProfile = null;
let currentJobProfile = null;
let currentMatchData = null;

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
  currentMatchData = null;
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

function selectedMatchProvider() {
  return document.querySelector('input[name="match-provider"]:checked')?.value ?? "openai";
}

function createMatchProviderPicker() {
  const picker = createElement("fieldset", "provider-picker match-provider-picker");
  picker.append(createElement("legend", "", "选择匹配报告模型"));
  for (const provider of ["openai", "deepseek"]) {
    const label = createElement("label");
    const input = createElement("input");
    input.type = "radio";
    input.name = "match-provider";
    input.value = provider;
    input.checked = provider === selectedProvider();
    const text = createElement("span");
    const displayName = provider === "openai" ? "OpenAI" : "DeepSeek";
    text.append(
      createElement("strong", "", displayName),
      createElement("small", "", `使用 ${provider.toUpperCase()} 配置生成匹配报告`),
    );
    label.append(input, text);
    picker.append(label);
  }
  return picker;
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
  jobPreview.append(createMatchProviderPicker());
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
  currentMatchData = data;
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

const APPLICATION_STATUSES = ["待投递", "已投递", "笔试", "面试", "Offer", "已拒绝"];

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

async function updateApplication(id, changes) {
  const response = await fetch(`/api/applications/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "更新投递记录失败。");
  await loadApplications();
}

function createApplicationCard(item) {
  const card = createElement("article", "application-card");
  const top = createElement("div", "application-card-top");
  const heading = createElement("div");
  heading.append(
    createElement("span", "application-company", item.company || "未填写公司"),
    createElement("h3", "", item.title || "未识别岗位"),
    createElement("small", "", [item.location, `更新于 ${formatDate(item.updated_at)}`].filter(Boolean).join(" · ")),
  );
  const score = createElement("strong", "application-score", item.overall_score);
  score.title = "岗位匹配分";
  top.append(heading, score);
  card.append(top);

  const controls = createElement("div", "application-controls");
  const statusSelect = createElement("select");
  statusSelect.setAttribute("aria-label", `${item.title || "岗位"}的投递状态`);
  for (const status of APPLICATION_STATUSES) {
    const option = createElement("option", "", status);
    option.selected = status === item.status;
    statusSelect.append(option);
  }
  statusSelect.addEventListener("change", async () => {
    try { await updateApplication(item.id, { status: statusSelect.value }); }
    catch (error) { showMessage(error.message); }
  });
  const detailsButton = createElement("button", "text-button", "查看与编辑");
  const draftButton = createElement("button", "text-button", "生成定制材料");
  const deleteButton = createElement("button", "text-button danger-button", "删除");
  controls.append(statusSelect, detailsButton, draftButton, deleteButton);
  card.append(controls);

  const details = createElement("div", "application-details is-hidden");
  const urlInput = createElement("input");
  urlInput.type = "url";
  urlInput.placeholder = "岗位链接";
  urlInput.value = item.job_url || "";
  const notesInput = createElement("textarea");
  notesInput.rows = 3;
  notesInput.placeholder = "投递备注";
  notesInput.value = item.notes || "";
  const saveButton = createElement("button", "copy-button", "保存修改");
  if (item.job_url) {
    const link = createElement("a", "job-link", "打开岗位链接 ↗");
    link.href = item.job_url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    details.append(link);
  }
  details.append(urlInput, notesInput, saveButton);
  detailsButton.addEventListener("click", () => details.classList.toggle("is-hidden"));
  const draftPanel = createElement("div", "draft-panel is-hidden");
  draftButton.addEventListener("click", async () => {
    if (!draftPanel.classList.contains("is-hidden") &&
        !window.confirm("重新生成会丢弃尚未保存的编辑，确定继续吗？")) return;
    draftButton.disabled = true;
    draftButton.textContent = "正在生成…";
    try {
      const response = await fetch(`/api/applications/${item.id}/draft`);
      const draft = await response.json();
      if (!response.ok) throw new Error(draft.detail || "生成定制材料失败。");
      draftPanel.replaceChildren();
      for (const [kind, documentData, label] of [
        ["resume", draft.resume, "简历建议稿"],
        ["letter", draft.cover_letter, "求职信草稿"],
      ]) {
        const block = createElement("section", "draft-document");
        block.append(createElement("h4", "", label));
        for (const section of documentData.sections) {
          block.append(createElement("h5", "", section.heading));
          for (const line of section.lines) block.append(createElement("p", "", line));
        }
        const downloads = createElement("div", "draft-downloads");
        downloads.append(createElement("small", "", "自动建议稿下载（未人工核对）"));
        for (const format of ["docx", "pdf"]) {
          const link = createElement("a", "copy-button", `下载 ${format.toUpperCase()}`);
          link.href = `/api/applications/${item.id}/draft/${kind}.${format}`;
          downloads.append(link);
        }
        block.append(downloads);
        draftPanel.append(block);
      }
      if (draft.suggestions.length) {
        const suggestions = createElement("section", "draft-notices");
        suggestions.append(createElement("h4", "", "修改建议（不会自动写入简历）"));
        for (const suggestion of draft.suggestions) suggestions.append(createElement("p", "", suggestion));
        draftPanel.append(suggestions);
      }
      const warnings = createElement("section", "draft-notices");
      warnings.append(createElement("h4", "", "投递前请核对"));
      for (const warning of draft.warnings) warnings.append(createElement("p", "", warning));
      draftPanel.append(warnings);

      const workspace = createElement("section", "draft-workspace");
      workspace.append(
        createElement("h4", "", "人工编辑与版本保存"),
        createElement("p", "", "编辑后保存为新版本；请对照原始简历和岗位要求逐项核对，再确认并下载该版本。确认只记录人工操作，不代表系统已核验事实。"),
      );
      const editorHost = createElement("div", "draft-editors");
      let resumeEditor;
      let letterEditor;
      function setEditors(resume, letter) {
        resumeEditor = buildDraftEditor(resume, "简历建议稿");
        letterEditor = buildDraftEditor(letter, "求职信草稿");
        editorHost.replaceChildren(resumeEditor.element, letterEditor.element);
      }
      setEditors(draft.resume, draft.cover_letter);
      const saveVersionButton = createElement("button", "copy-button", "保存为新版本");
      const editorStatus = createElement("p", "draft-status", "未保存的修改不会影响已有版本。");
      const versionList = createElement("div", "draft-version-list");
      const evidenceOutput = createElement("div", "draft-evidence-output");
      const compareControls = createElement("div", "draft-compare-controls");
      const diffOutput = createElement("div", "draft-diff-output");
      const sourceResponse = await fetch(`/api/applications/${item.id}/sources/status`);
      const sourceStatus = await sourceResponse.json();
      if (!sourceResponse.ok) throw new Error(apiErrorMessage(sourceStatus, "读取原文留存状态失败。"));
      const sourceNotice = createElement("p", "", sourceStatus.retained
        ? "此投递已授权留存原文，可对保存的版本做字面证据检查。"
        : "此投递未留存原文，历史版本仍可编辑和比较，但不能做原文字面检查。");
      workspace.append(sourceNotice);
      if (sourceStatus.retained) {
        const revokeButton = createElement("button", "text-button danger-button", "删除留存原文");
        revokeButton.addEventListener("click", async () => {
          if (!window.confirm("确定删除这条投递留存的简历和岗位原文吗？此操作不可恢复，版本材料仍会保留。")) return;
          try {
            const response = await fetch(`/api/applications/${item.id}/sources`, { method: "DELETE" });
            if (!response.ok) throw new Error("删除留存原文失败。");
            sourceStatus.retained = false;
            sourceNotice.textContent = "留存原文已删除；历史版本仍可编辑和比较，但不能再做字面检查。";
            revokeButton.remove();
            evidenceOutput.replaceChildren();
            await loadVersionList();
          } catch (error) { showMessage(error.message); }
        });
        workspace.append(revokeButton);
      }

      async function loadVersionList() {
        const response = await fetch(`/api/applications/${item.id}/draft-versions`);
        const versions = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(versions, "读取草稿版本失败。"));
        versionList.replaceChildren();
        if (!versions.length) {
          versionList.append(createElement("p", "", "尚无已保存版本。"));
          return;
        }
        for (const version of versions) {
          const row = createElement("div", "draft-version-row");
          row.append(createElement("strong", "", `版本 ${version.version} · ${version.reviewed_at ? "已核对" : "待核对"}`));
          row.append(createElement("small", "", formatDate(version.created_at)));
          const loadButton = createElement("button", "text-button", "载入编辑");
          loadButton.addEventListener("click", async () => {
            if (!window.confirm("载入历史版本会覆盖编辑框中未保存的修改，确定继续吗？")) return;
            try {
              const detailResponse = await fetch(`/api/applications/${item.id}/draft-versions/${version.version}`);
              const detail = await detailResponse.json();
              if (!detailResponse.ok) throw new Error(apiErrorMessage(detail, "读取版本失败。"));
              setEditors(detail.resume, detail.cover_letter);
              editorStatus.textContent = `已载入版本 ${version.version}；保存修改会创建新版本，不会覆盖旧版。`;
            } catch (error) { showMessage(error.message); }
          });
          row.append(loadButton);
          if (sourceStatus.retained) {
            const evidenceButton = createElement("button", "text-button", "查看字面证据");
            evidenceButton.addEventListener("click", async () => {
              try {
                const evidenceResponse = await fetch(`/api/applications/${item.id}/draft-versions/${version.version}/evidence`);
                const report = await evidenceResponse.json();
                if (!evidenceResponse.ok) throw new Error(apiErrorMessage(report, "证据检查失败。"));
                evidenceOutput.replaceChildren(
                  createElement("h4", "", `版本 ${version.version} · 字面证据检查`),
                  createElement("p", "", report.warning),
                  createElement("p", "", `简历原文命中 ${report.resume_hits} 行；岗位原文命中 ${report.job_hits} 行；未命中 ${report.unmatched} 行。`),
                );
                for (const line of report.lines) {
                  const detail = createElement("details", "draft-evidence-line");
                  const sourceLabel = line.source === "resume" ? "简历原文" : line.source === "job" ? "岗位原文" : "未找到字面片段";
                  detail.append(createElement("summary", "", `${line.document === "resume" ? "简历" : "求职信"} · ${line.section}：${line.text} — ${sourceLabel}`));
                  if (line.source_excerpt) detail.append(createElement("p", "", `原文片段：${line.source_excerpt}`));
                  evidenceOutput.append(detail);
                }
              } catch (error) { showMessage(error.message); }
            });
            row.append(evidenceButton);
          }
          if (!version.reviewed_at) {
            const reviewButton = createElement("button", "text-button", "核对并确认");
            reviewButton.addEventListener("click", async () => {
              if (!window.confirm(`请确认已对照原始简历和岗位描述核对版本 ${version.version} 的全部内容。确认后即可下载该版本。`)) return;
              try {
                const reviewResponse = await fetch(`/api/applications/${item.id}/draft-versions/${version.version}/review`, {
                  method: "PATCH", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ confirmed: true }),
                });
                const result = await reviewResponse.json();
                if (!reviewResponse.ok) throw new Error(apiErrorMessage(result, "确认版本失败。"));
                await loadVersionList();
              } catch (error) { showMessage(error.message); }
            });
            row.append(reviewButton);
          } else {
            for (const kind of ["resume", "letter"]) {
              for (const format of ["docx", "pdf"]) {
                const link = createElement("a", "copy-button", `${kind === "resume" ? "简历" : "求职信"} ${format.toUpperCase()}`);
                link.href = `/api/applications/${item.id}/draft-versions/${version.version}/${kind}.${format}`;
                row.append(link);
              }
            }
          }
          versionList.append(row);
        }
        compareControls.replaceChildren();
        if (versions.length >= 2) {
          const oldSelect = createElement("select");
          const newSelect = createElement("select");
          for (const version of versions) {
            oldSelect.append(createElement("option", "", `版本 ${version.version}`));
            oldSelect.lastChild.value = version.version;
            newSelect.append(createElement("option", "", `版本 ${version.version}`));
            newSelect.lastChild.value = version.version;
          }
          oldSelect.value = versions[versions.length - 1].version;
          newSelect.value = versions[0].version;
          oldSelect.setAttribute("aria-label", "对比起始版本");
          newSelect.setAttribute("aria-label", "对比目标版本");
          const compareButton = createElement("button", "copy-button", "比较两个版本");
          compareButton.addEventListener("click", async () => {
            try {
              const params = new URLSearchParams({ from_version: oldSelect.value, to_version: newSelect.value });
              const response = await fetch(`/api/applications/${item.id}/draft-versions/compare?${params}`);
              const diff = await response.json();
              if (!response.ok) throw new Error(apiErrorMessage(diff, "版本比较失败。"));
              diffOutput.replaceChildren(
                createElement("h4", "", `版本 ${diff.from_version} → ${diff.to_version}`),
                createElement("p", "", "“−”为旧版内容，“+”为新版内容；仅比较文本，不判断事实真伪。"),
                createElement("h5", "", "简历变化"),
                createElement("pre", "", diff.resume_diff.join("\n") || "无变化"),
                createElement("h5", "", "求职信变化"),
                createElement("pre", "", diff.cover_letter_diff.join("\n") || "无变化"),
              );
            } catch (error) { showMessage(error.message); }
          });
          compareControls.append(oldSelect, newSelect, compareButton);
        }
      }
      saveVersionButton.addEventListener("click", async () => {
        saveVersionButton.disabled = true;
        try {
          const response = await fetch(`/api/applications/${item.id}/draft-versions`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resume: resumeEditor.read(), cover_letter: letterEditor.read() }),
          });
          const result = await response.json();
          if (!response.ok) throw new Error(apiErrorMessage(result, "保存版本失败。"));
          editorStatus.textContent = `版本 ${result.version} 已保存，待核对确认。`;
          await loadVersionList();
        } catch (error) { showMessage(error.message); }
        finally { saveVersionButton.disabled = false; }
      });
      workspace.append(editorHost, saveVersionButton, editorStatus,
        createElement("h4", "", "历史版本"), versionList,
        evidenceOutput, compareControls, diffOutput);
      draftPanel.append(workspace);
      await loadVersionList();
      draftPanel.classList.remove("is-hidden");
      card.classList.add("draft-open");
    } catch (error) { showMessage(error instanceof Error ? error.message : "生成定制材料失败。"); }
    finally { draftButton.disabled = false; draftButton.textContent = "重新生成定制材料"; }
  });
  saveButton.addEventListener("click", async () => {
    try {
      await updateApplication(item.id, { job_url: urlInput.value.trim() || null, notes: notesInput.value.trim() || null });
    } catch (error) { showMessage(error.message); }
  });
  deleteButton.addEventListener("click", async () => {
    if (!window.confirm(`确定删除“${item.title || "该岗位"}”的投递记录吗？`)) return;
    try {
      const response = await fetch(`/api/applications/${item.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("删除投递记录失败。");
      await loadApplications();
    } catch (error) { showMessage(error.message); }
  });
  card.append(details, draftPanel);
  return card;
}

function apiErrorMessage(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map((entry) => entry.msg).join("；");
  return fallback;
}

function buildDraftEditor(documentData, label) {
  const element = createElement("section", "draft-editor");
  element.append(createElement("h5", "", label));
  const titleInput = createElement("input");
  titleInput.setAttribute("aria-label", `${label}标题`);
  titleInput.value = documentData.title;
  element.append(titleInput);
  const sectionsHost = createElement("div", "draft-editor-sections");
  const sectionEditors = [];
  function addSection(heading = "", lines = []) {
    const section = createElement("div", "draft-editor-section");
    const headingInput = createElement("input");
    headingInput.setAttribute("aria-label", `${label}章节标题`);
    headingInput.placeholder = "章节标题";
    headingInput.value = heading;
    const linesInput = createElement("textarea");
    linesInput.setAttribute("aria-label", `${label}章节内容，每行一条`);
    linesInput.rows = Math.max(3, Math.min(lines.length + 1, 10));
    linesInput.placeholder = "每行一条内容";
    linesInput.value = lines.join("\n");
    const removeButton = createElement("button", "text-button danger-button", "删除章节");
    removeButton.type = "button";
    removeButton.addEventListener("click", () => section.remove());
    section.append(headingInput, linesInput, removeButton);
    sectionsHost.append(section);
    sectionEditors.push({ section, headingInput, linesInput });
  }
  for (const section of documentData.sections) addSection(section.heading, section.lines);
  const addButton = createElement("button", "text-button", "添加章节");
  addButton.type = "button";
  addButton.addEventListener("click", () => addSection());
  element.append(sectionsHost, addButton);
  return {
    element,
    read: () => ({
      title: titleInput.value.trim(),
      sections: sectionEditors.filter((editor) => editor.section.parentNode === sectionsHost)
        .map((editor) => ({
          heading: editor.headingInput.value.trim(),
          lines: editor.linesInput.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
        })),
    }),
  };
}

async function loadApplications() {
  const params = new URLSearchParams({ sort: applicationSort.value });
  if (applicationFilter.value) params.set("status", applicationFilter.value);
  applicationCount.textContent = "正在读取投递记录…";
  try {
    const response = await fetch(`/api/applications?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "读取投递记录失败。");
    applicationGrid.replaceChildren();
    applicationCount.textContent = `共 ${data.length} 个岗位`;
    if (!data.length) {
      applicationGrid.append(createElement("p", "board-empty", "暂无符合条件的投递记录。生成匹配报告后，可以把岗位保存到这里。"));
      return;
    }
    for (const item of data) applicationGrid.append(createApplicationCard(item));
  } catch (error) {
    applicationCount.textContent = "投递记录读取失败";
    showMessage(error instanceof Error ? error.message : "读取投递记录失败。");
  }
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
        provider: selectedMatchProvider(),
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

saveApplicationButton.addEventListener("click", async () => {
  if (!currentCandidateProfile || !currentJobProfile || !currentMatchData) {
    showMessage("请先完成简历、岗位和匹配报告分析。");
    return;
  }
  if (retainSourceText.checked && !resumeText.textContent.trim()) {
    showMessage("如需保存原文，请先点击“开始解析”获得简历正文，或取消原文留存勾选。");
    return;
  }
  if (retainSourceText.checked && !jobDescription.value.trim()) {
    showMessage("如需保存原文，请先填写岗位描述，或取消原文留存勾选。");
    return;
  }
  saveApplicationButton.disabled = true;
  saveApplicationButton.querySelector("span:first-child").textContent = "正在保存…";
  try {
    const response = await fetch("/api/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resume_filename: currentFile?.name || "未知简历",
        candidate_profile: currentCandidateProfile,
        job_profile: currentJobProfile,
        match_result: currentMatchData.result,
        provider: currentMatchData.provider,
        model: currentMatchData.model,
        status: saveStatus.value,
        job_url: saveJobUrl.value.trim() || null,
        notes: saveNotes.value.trim() || null,
        retain_source_text: retainSourceText.checked,
        ...(retainSourceText.checked ? {
          resume_text: resumeText.textContent,
          job_description: jobDescription.value.trim(),
        } : {}),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(apiErrorMessage(data, "保存投递记录失败。"));
    saveApplicationButton.querySelector("span:first-child").textContent = "保存成功";
    retainSourceText.checked = false;
    await loadApplications();
    document.querySelector("#applications-panel").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    showMessage(error instanceof Error ? error.message : "保存投递记录失败。");
  } finally {
    window.setTimeout(() => {
      saveApplicationButton.disabled = false;
      saveApplicationButton.querySelector("span:first-child").textContent = "保存岗位与匹配报告";
    }, 900);
  }
});

applicationFilter.addEventListener("change", loadApplications);
applicationSort.addEventListener("change", loadApplications);
refreshApplications.addEventListener("click", loadApplications);
loadApplications();

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
