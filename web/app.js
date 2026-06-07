const examples = [
  "数字孪生为什么强调虚实闭环？",
  "CAD图元和BIM构件有什么本质区别？",
  "BIM+GIS叠加分析能帮选线解决什么问题？",
  "道路工程数字化设计经历了哪些主要阶段？",
  "以模型为核心的设计流程包括哪些环节？",
  "数据驱动的设计控制体现在哪些方面？",
  "这个时间轴脚本应该怎么看？",
  "图1-1说明了什么？"
];

const chapters = {
  ch01: {
    label: "第 1 章",
    title: "数字化设计概述",
    examples: [
      "数字孪生为什么强调虚实闭环？",
      "CAD图元和BIM构件有什么本质区别？",
      "图1-1说明了什么？"
    ]
  },
  ch02: {
    label: "第 2 章",
    title: "图形原理与三维表达",
    examples: [
      "图形表达在道路建模中的作用是什么？",
      "WCS和UCS有什么区别？",
      "我想看2.1互动脚本。"
    ]
  },
  ch03: {
    label: "第 3 章",
    title: "道路CAD系统设计原理",
    examples: [
      "CAD系统由哪些模块组成？",
      "道路CAD系统设计流程是什么？",
      "我想看3.1互动脚本。"
    ]
  },
  ch04: {
    label: "第 4 章",
    title: "道路BIM正向设计",
    examples: [
      "BIM的定义和三大核心要素是什么？",
      "道路BIM正向设计流程包括哪五个环节？",
      "我想看道路BIM与建筑BIM。"
    ]
  },
  ch05: {
    label: "第 5 章",
    title: "GIS理论与空间分析",
    examples: [
      "什么是GIS的定义？",
      "什么是缓冲区分析？",
      "我想看空间数据模型、拓扑结构与BIM模型差异。"
    ]
  },
  ch06: {
    label: "第 6 章",
    title: "AutoCAD平台功能与使用方法",
    examples: [
      "AutoCAD如何设置AutoCAD绘图环境？",
      "设置AutoCAD绘图环境失败或结果不对怎么办？",
      "我想看第六章AutoCAD互动脚本。"
    ]
  },
  ch07: {
    label: "第 7 章",
    title: "道路CAD软件的使用",
    examples: [
      "纬地如何新建纬地项目？",
      "新建纬地项目失败或结果不对怎么办？",
      "我想看道路CAD软件使用流程。"
    ]
  },
  ch08: {
    label: "第 8 章",
    title: "道路BIM软件的使用",
    examples: [
      "ORD参数化架构是什么？",
      "创建或检查ORD项目工作环境怎么操作？",
      "我想看ORD软件功能总览与道路设计流程。"
    ]
  },
  ch09: {
    label: "第 9 章",
    title: "BIM_GIS集成方法",
    examples: [
      "数据驱动的BIM+GIS道路设计范式是什么？",
      "创建TIN曲面怎么操作？",
      "我想看BIM+GIS协同设计流程。"
    ]
  },
  ch10: {
    label: "第 10 章",
    title: "AI驱动的道路设计方法",
    examples: [
      "AI驱动的道路设计包含哪三大范式？",
      "知识驱动、算法驱动和数据驱动有什么区别？",
      "我想看AI驱动道路设计范式。"
    ]
  },
  ch11: {
    label: "第 11 章",
    title: "道路数字孪生的概念与方法体系",
    examples: [
      "道路数字孪生是什么？",
      "从CAD到数字孪生的技术演进是什么？",
      "我想看道路数字孪生内涵与系统框架。"
    ]
  }
};

const storage = {
  history: "road-kb-question-history",
  feedback: "road-kb-learning-feedback"
};

const state = {
  currentAnswer: null,
  chapterId: "ch01",
  chapterResources: [],
  operationTasks: [],
  operationTaskDetail: null,
  resourceFilter: "all",
  questionBank: null,
  questionFilter: "all",
  questionSearch: "",
  questionBankExpanded: false,
  selectedFeedback: "useful"
};

const els = {
  apiBase: document.querySelector("#apiBase"),
  chapterButtons: document.querySelectorAll("[data-chapter]"),
  serviceStatus: document.querySelector("#serviceStatus"),
  statAnswers: document.querySelector("#statAnswers"),
  statQa: document.querySelector("#statQa"),
  statResources: document.querySelector("#statResources"),
  questionInput: document.querySelector("#questionInput"),
  askButton: document.querySelector("#askButton"),
  examples: document.querySelector("#examples"),
  questionBankPanel: document.querySelector("#questionBankPanel"),
  questionBankToggle: document.querySelector("#questionBankToggle"),
  questionBankTools: document.querySelector("#questionBankTools"),
  questionTabs: document.querySelector("#questionTabs"),
  questionSearch: document.querySelector("#questionSearch"),
  questionBank: document.querySelector("#questionBank"),
  questionBankCount: document.querySelector("#questionBankCount"),
  historyList: document.querySelector("#historyList"),
  clearHistory: document.querySelector("#clearHistory"),
  answerId: document.querySelector("#answerId"),
  answerTitle: document.querySelector("#answerTitle"),
  confidence: document.querySelector("#confidence"),
  answerPanel: document.querySelector("#answerPanel"),
  answerBody: document.querySelector("#answerBody"),
  learningSupport: document.querySelector("#learningSupport"),
  resources: document.querySelector("#resources"),
  resourceCount: document.querySelector("#resourceCount"),
  resourceTabs: document.querySelector("#resourceTabs"),
  chapterResources: document.querySelector("#chapterResources"),
  refreshChapterResources: document.querySelector("#refreshChapterResources"),
  operationTaskCount: document.querySelector("#operationTaskCount"),
  operationTasks: document.querySelector("#operationTasks"),
  operationTaskDetail: document.querySelector("#operationTaskDetail"),
  refreshOperationTasks: document.querySelector("#refreshOperationTasks"),
  hits: document.querySelector("#hits"),
  hitCount: document.querySelector("#hitCount"),
  detailId: document.querySelector("#detailId"),
  cardDetail: document.querySelector("#cardDetail"),
  evalRuns: document.querySelector("#evalRuns"),
  failureList: document.querySelector("#failureList"),
  refreshEval: document.querySelector("#refreshEval"),
  feedbackStatus: document.querySelector("#feedbackStatus"),
  feedbackNote: document.querySelector("#feedbackNote"),
  saveFeedback: document.querySelector("#saveFeedback"),
  exportFeedback: document.querySelector("#exportFeedback"),
  traceBox: document.querySelector("#traceBox"),
  retrieverName: document.querySelector("#retrieverName")
};

function apiBase() {
  return els.apiBase.value.replace(/\/$/, "");
}

function selectedMode() {
  return document.querySelector("input[name='mode']:checked")?.value || "db";
}

function askOptions() {
  const mode = selectedMode();
  return {
    use_vectors: mode === "vectors",
    use_db: mode === "db"
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i += 1;
      continue;
    }
    if (line.startsWith("|") && i + 1 < lines.length && lines[i + 1].includes("---")) {
      const rows = [line];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(lines[i].trim());
        i += 1;
      }
      blocks.push(renderTable(rows));
      continue;
    }
    if (line.startsWith("- ")) {
      const items = [];
      while (i < lines.length && lines[i].trim().startsWith("- ")) {
        items.push(`<li>${inlineMarkdown(lines[i].trim().slice(2))}</li>`);
        i += 1;
      }
      blocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }
    blocks.push(`<p>${inlineMarkdown(line)}</p>`);
    i += 1;
  }
  return blocks.join("");
}

function studentAnswerText(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  return lines
    .filter((line) => {
      const text = line.trim();
      if (text.startsWith("教材依据：")) return false;
      if (text.includes("Source_Chunks作为依据")) return false;
      return true;
    })
    .join("\n")
    .trim();
}

function renderTable(rows) {
  const parsed = rows.map((row) =>
    row
      .split("|")
      .slice(1, -1)
      .map((cell) => inlineMarkdown(cell.trim()))
  );
  const [head, ...body] = parsed;
  const th = head.map((cell) => `<th>${cell}</th>`).join("");
  const tr = body.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
}

function inlineMarkdown(text) {
  return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/`(.*?)`/g, "<code>$1</code>");
}

function compactPreview(value, maxLength = 90) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

function getJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || "") || fallback;
  } catch {
    return fallback;
  }
}

function setJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function setStatus(kind, label) {
  els.serviceStatus.className = `status-row ${kind}`;
  els.serviceStatus.querySelector("strong").textContent = label;
}

async function checkHealth() {
  try {
    const response = await fetch(`${apiBase()}/health?chapter_id=${encodeURIComponent(state.chapterId)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    setStatus("ok", "已连接");
    els.statAnswers.textContent = data.answer_cards ?? "-";
    els.statQa.textContent = data.qa_cases ?? "-";
    els.statResources.textContent = data.resources ?? "-";
  } catch {
    setStatus("error", "未连接");
    els.statAnswers.textContent = "-";
    els.statQa.textContent = "-";
    els.statResources.textContent = "-";
  }
}

async function ask(question) {
  const options = askOptions();
  els.askButton.disabled = true;
  els.askButton.textContent = "检索中";
  els.answerId.textContent = "检索中";
  els.answerTitle.textContent = question;
  els.confidence.textContent = "-";
  els.answerBody.classList.remove("empty");
  els.answerBody.innerHTML = "<p>正在调用本地知识库 API...</p>";
  revealAnswerPanel();

  try {
    const response = await fetch(`${apiBase()}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        chapter_id: state.chapterId,
        auto_chapter: true,
        top_k: 5,
        use_vectors: options.use_vectors,
        use_db: options.use_db
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderAnswer(data);
    rememberQuestion(data);
    loadAnswerCard(data.answer_id);
  } catch (error) {
    els.answerId.textContent = "请求失败";
    els.answerTitle.textContent = "无法连接知识库 API";
    els.confidence.textContent = "-";
    els.answerBody.innerHTML = `<p>${escapeHtml(error.message)}</p><p>请确认 API 服务已启动，并检查高级设置中的 API 地址。</p>`;
    els.resources.textContent = "暂无推荐资源";
    els.hits.textContent = "暂无召回结果";
    els.traceBox.textContent = String(error.stack || error.message);
  } finally {
    els.askButton.disabled = false;
    els.askButton.textContent = "提问";
  }
}

function revealAnswerPanel() {
  if (!els.answerPanel) return;
  els.answerPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderAnswer(data) {
  syncResolvedChapter(data.chapter_id);
  state.currentAnswer = data;
  els.answerId.textContent = data.answer_id || "未命中";
  els.answerTitle.textContent = data.question || "检索结果";
  els.confidence.textContent = data.confidence || "-";
  els.answerBody.innerHTML = renderMarkdown(studentAnswerText(data.answer) || "教材知识库未找到直接答案。");
  renderResources(data.recommended_resources || []);
  renderHits(data.top_hits || []);
  renderTrace(data.trace || {});
  updateFeedbackStatus();
}

function renderResources(resources) {
  els.resourceCount.textContent = resources.length;
  if (!resources.length) {
    els.resources.className = "resource-list empty";
    els.resources.textContent = "暂无推荐资源";
    return;
  }
  els.resources.className = "resource-list";
  els.resources.innerHTML = resources.map((item) => resourceCardHtml(item, true)).join("");
}

function resourceCardHtml(item, includeMatch = false) {
  const path = item.file_path || "";
  const href = item.url_path || (path ? `/${path}` : "#");
  const status = resourceStatus(item);
  const title = item.title || item.resource_id;
  const script = item.interactive_script || {};
  const steps = Array.isArray(script.operation_steps) ? script.operation_steps.slice(0, 3) : [];
  const thumbnail = item.resource_type === "image" && href !== "#"
    ? `<a class="resource-thumb" href="${escapeHtml(href)}" target="_blank" rel="noreferrer">
        <img src="${escapeHtml(href)}" alt="${escapeHtml(title)}">
      </a>`
    : "";
  const formula = formulaBoxHtml(item);
  const table = tableBoxHtml(item);
  const match = "";
  const themeText = script.interaction_theme || "";
  const stepList = steps.length
    ? `<ol class="resource-steps">${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>`
    : "";
  const theme = themeText && normalizedText(themeText) !== normalizedText(title)
    ? `<p class="resource-theme">${escapeHtml(themeText)}</p>`
    : "";
  const pathLine = "";
  const action = href !== "#" && item.resource_type !== "formula"
    ? `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">打开资源</a>`
    : "";
  return `<article class="resource-card">
    <div class="card-row">
      <h3>${escapeHtml(title)}</h3>
      <div class="resource-badges">${match}</div>
    </div>
    ${thumbnail}
    ${formula}
    ${table}
    ${theme}
    ${pathLine}
    ${stepList}
    ${action}
  </article>`;
}

function normalizedText(value) {
  return String(value || "").replace(/\s+/g, "").trim();
}

function resourceStatus(item) {
  const available = item.resource_type === "formula"
    ? item.available !== false && !!item.formula_detail?.expression
    : item.resource_type === "table"
      ? item.available !== false && Array.isArray(item.table_detail?.rows) && item.table_detail.rows.length > 0
    : item.exists !== false;
  if (!available) return { className: "missing", label: "文件缺失" };
  if (item.resource_type === "formula") return { className: "ok", label: item.status || "structured" };
  if (item.resource_type === "table") return { className: "ok", label: item.status || "structured" };
  return { className: "ok", label: item.status || "bound" };
}

function formulaBoxHtml(item) {
  if (item.resource_type !== "formula") return "";
  const detail = item.formula_detail || {};
  const expression = displayFormulaExpression(detail.expression || "");
  const context = detail.context_before || detail.context_after || item.description || "";
  const variables = Array.isArray(detail.variables) ? detail.variables.slice(0, 3) : [];
  if (!expression && !context && !variables.length) return "";
  const variableList = variables.length
    ? `<ul class="formula-vars">${variables.map((line) => `<li>${escapeHtml(compactPreview(line, 80))}</li>`).join("")}</ul>`
    : "";
  const contextLine = context ? `<p class="formula-context">${escapeHtml(compactPreview(context, 120))}</p>` : "";
  const expressionLine = expression ? `<p class="formula-expression">${escapeHtml(expression)}</p>` : "";
  return `<div class="formula-box">
    ${expressionLine}
    ${contextLine}
    ${variableList}
  </div>`;
}

function displayFormulaExpression(expression) {
  const text = String(expression || "");
  const formatted = text
    .replace(/\s*&\s*/g, "\n")
    .replace(/\n{2,}/g, "\n")
    .trim();
  return formatted || text;
}

function tableBoxHtml(item) {
  if (item.resource_type !== "table") return "";
  const detail = item.table_detail || {};
  const columns = Array.isArray(detail.columns) ? detail.columns.slice(0, 4) : [];
  const rows = Array.isArray(detail.rows) ? detail.rows.slice(0, 3) : [];
  const context = detail.context_before || item.description || "";
  if (!columns.length || !rows.length) return "";
  const header = columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const body = rows.map((row) => {
    const cells = columns.map((column) => `<td>${escapeHtml(compactPreview(row[column] || "", 70))}</td>`).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
  const contextLine = context ? `<p class="table-context">${escapeHtml(compactPreview(context, 120))}</p>` : "";
  return `<div class="table-box">
    ${contextLine}
    <table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>
  </div>`;
}

async function loadChapterResources() {
  if (!els.chapterResources) return;
  els.chapterResources.className = "resource-list empty";
  els.chapterResources.textContent = "正在加载资源...";
  try {
    const response = await fetch(`${apiBase()}/resources?chapter_id=${encodeURIComponent(state.chapterId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    state.chapterResources = data.resources || [];
    renderChapterResources();
  } catch (error) {
    els.chapterResources.className = "resource-list empty";
    els.chapterResources.textContent = error.message;
  }
}

function renderChapterResources() {
  if (!els.chapterResources) return;
  const items = state.chapterResources.filter((item) => {
    if (state.resourceFilter === "all") return true;
    return item.resource_type === state.resourceFilter;
  });
  if (!items.length) {
    els.chapterResources.className = "resource-list empty";
    els.chapterResources.textContent = "暂无资源";
    return;
  }
  els.chapterResources.className = "resource-list";
  els.chapterResources.innerHTML = items.map((item) => chapterResourceCardHtml(item)).join("");
}

function chapterResourceCardHtml(item) {
  return resourceCardHtml(item, false);
}

async function loadOperationTasks() {
  if (!els.operationTasks) return;
  els.operationTasks.className = "operation-list empty";
  els.operationTasks.textContent = "正在加载操作任务...";
  if (els.operationTaskDetail) {
    els.operationTaskDetail.className = "operation-detail empty";
    els.operationTaskDetail.textContent = "选择任务后查看步骤";
  }
  try {
    const response = await fetch(`${apiBase()}/operation-tasks?chapter_id=${encodeURIComponent(state.chapterId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    state.operationTasks = data.tasks || [];
    renderOperationTasks(data);
  } catch (error) {
    els.operationTasks.className = "operation-list empty";
    els.operationTasks.textContent = error.message;
    if (els.operationTaskCount) els.operationTaskCount.textContent = "0";
  }
}

function renderOperationTasks(data = {}) {
  if (!els.operationTasks) return;
  const items = state.operationTasks || [];
  if (els.operationTaskCount) {
    els.operationTaskCount.textContent = `${items.length}`;
  }
  if (!items.length) {
    els.operationTasks.className = "operation-list empty";
    els.operationTasks.textContent = "本章暂无操作任务";
    return;
  }
  els.operationTasks.className = "operation-list";
  els.operationTasks.innerHTML = items.slice(0, 18).map((task) => operationTaskCardHtml(task)).join("");
}

function operationTaskCardHtml(task) {
  const resource = task.primary_resource ? `<span>资源 ${escapeHtml(task.primary_resource.resource_type || "")}</span>` : "";
  return `<button class="operation-card" type="button" data-operation-task="${escapeHtml(task.task_id)}">
    <strong>${escapeHtml(task.task_name || task.task_id)}</strong>
    <small>${escapeHtml(compactPreview(task.task_goal || "", 92))}</small>
    <span class="operation-meta">
      <span>${escapeHtml(task.step_count ?? 0)} 步</span>
      <span>${escapeHtml(task.error_count ?? 0)} 错误</span>
      ${resource}
    </span>
  </button>`;
}

async function loadOperationTaskDetail(taskId) {
  if (!els.operationTaskDetail || !taskId) return;
  els.operationTaskDetail.className = "operation-detail";
  els.operationTaskDetail.innerHTML = "<p>正在加载任务步骤...</p>";
  try {
    const response = await fetch(`${apiBase()}/operation-task?chapter_id=${encodeURIComponent(state.chapterId)}&id=${encodeURIComponent(taskId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    state.operationTaskDetail = data;
    renderOperationTaskDetail(data);
  } catch (error) {
    els.operationTaskDetail.className = "operation-detail empty";
    els.operationTaskDetail.textContent = error.message;
  }
}

function renderOperationTaskDetail(data) {
  const task = data.task || {};
  const steps = data.steps || [];
  const errors = data.errors || [];
  const answers = data.answer_cards || [];
  const resources = data.recommended_resources || [];
  els.operationTaskDetail.className = "operation-detail";
  els.operationTaskDetail.innerHTML = `<article class="operation-detail-card">
    <h3>${escapeHtml(task.task_name || task.task_id)}</h3>
    <p>${escapeHtml(task.task_goal || "")}</p>
    <dl class="operation-facts">
      <div><dt>前置条件</dt><dd>${escapeHtml(task.prerequisite || "未注明")}</dd></div>
      <div><dt>预期成果</dt><dd>${escapeHtml(task.output_result || "未注明")}</dd></div>
    </dl>
    <h4>操作步骤</h4>
    ${operationStepsHtml(steps)}
    <h4>常见错误</h4>
    ${operationErrorsHtml(errors)}
    <h4>相关问答</h4>
    ${operationAnswersHtml(answers)}
    <h4>推荐资源</h4>
    ${resources.length ? resources.map((item) => resourceCardHtml(item, false)).join("") : "<p class=\"muted-text\">暂无可用资源</p>"}
  </article>`;
}

function operationStepsHtml(steps) {
  if (!steps.length) return "<p class=\"muted-text\">暂无步骤</p>";
  return `<ol class="operation-steps">${steps.map((step, index) => `<li>
    <strong>${escapeHtml(step.step_title || `步骤 ${index + 1}`)}</strong>
    <span>${escapeHtml(step.command || step.action || "")}</span>
    <small>${escapeHtml(step.expected_result || "")}</small>
    ${operationMediaHtml(step)}
  </li>`).join("")}</ol>`;
}

function operationMediaHtml(step) {
  const items = [];
  if (step.video_segment) {
    const video = step.video_segment;
    const label = video.available ? "视频可用" : "视频待补充";
    const text = `${label}${video.start_time ? ` · ${video.start_time}-${video.end_time || ""}` : ""}`;
    items.push(video.available && video.url_path
      ? `<a class="media-chip ok" href="${escapeHtml(video.url_path)}" target="_blank" rel="noreferrer">${escapeHtml(text)}</a>`
      : `<span class="media-chip pending">${escapeHtml(text)}</span>`);
  }
  if (step.screenshot) {
    const shot = step.screenshot;
    const label = shot.available ? "截图可用" : "截图待补充";
    items.push(shot.available && shot.url_path
      ? `<a class="media-chip ok" href="${escapeHtml(shot.url_path)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`
      : `<span class="media-chip pending">${escapeHtml(label)}</span>`);
  }
  return items.length ? `<div class="operation-media">${items.join("")}</div>` : "";
}

function operationErrorsHtml(errors) {
  if (!errors.length) return "<p class=\"muted-text\">暂无错误记录</p>";
  return `<ul class="operation-errors">${errors.slice(0, 5).map((item) => `<li>
    <strong>${escapeHtml(item.phenomenon || item.error_id)}</strong>
    <span>${escapeHtml(compactPreview(item.cause || item.solution || "", 120))}</span>
  </li>`).join("")}</ul>`;
}

function operationAnswersHtml(answers) {
  if (!answers.length) return "<p class=\"muted-text\">暂无关联答案卡</p>";
  return `<div class="operation-answer-links">${answers.slice(0, 5).map((item) => `<button type="button" data-detail="${escapeHtml(item.answer_id)}">
    ${escapeHtml(item.canonical_question || item.answer_id)}
  </button>`).join("")}</div>`;
}

function renderHits(hits) {
  els.hitCount.textContent = hits.length;
  if (!hits.length) {
    els.hits.className = "hit-list empty";
    els.hits.textContent = "暂无召回结果";
    return;
  }
  els.hits.className = "hit-list";
  els.hits.innerHTML = hits
    .map(
      (hit, index) => `<article class="hit-card">
        <div class="card-row">
          <h3>${index + 1}. ${escapeHtml(hit.answer_id)}</h3>
          <button type="button" data-detail="${escapeHtml(hit.answer_id)}">详情</button>
        </div>
        <p>${escapeHtml(hit.canonical_question || "")}</p>
        <div class="hit-meta">
          <span>score ${escapeHtml(hit.score)}</span>
          <span>${escapeHtml(hit.confidence)}</span>
          <span>${escapeHtml(hit.answer_mode)}</span>
        </div>
      </article>`
    )
    .join("");
}

function renderTrace(trace) {
  els.retrieverName.textContent = trace.retriever || "-";
  els.traceBox.textContent = JSON.stringify(trace, null, 2);
}

async function loadAnswerCard(answerId) {
  if (!answerId || String(answerId).startsWith("resource:")) {
    renderLearningSupport(null);
    els.detailId.textContent = answerId || "-";
    els.cardDetail.className = "detail-box empty";
    els.cardDetail.textContent = "资源型回答暂无答案卡详情，可直接打开推荐资源查看。";
    return;
  }
  els.detailId.textContent = answerId;
  els.cardDetail.className = "detail-box";
  els.cardDetail.innerHTML = "<p>正在加载答案卡详情...</p>";
  try {
    const response = await fetch(`${apiBase()}/answer-card?id=${encodeURIComponent(answerId)}&chapter_id=${encodeURIComponent(state.chapterId)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderLearningSupport(data.learning_support);
    renderAnswerCardDetail(data);
  } catch (error) {
    renderLearningSupport(null);
    els.cardDetail.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
}

function renderLearningSupport(data) {
  if (!els.learningSupport) return;
  if (!data) {
    els.learningSupport.hidden = true;
    els.learningSupport.innerHTML = "";
    return;
  }

  const path = data.study_path || [];
  const checks = data.self_check || [];
  const next = data.next_learning || [];
  const navigation = data.navigation || null;
  const scenarios = data.scenarios || [];
  const stage = [data.card_type, data.learning_stage].filter(Boolean).join(" · ");

  els.learningSupport.hidden = false;
  els.learningSupport.innerHTML = `
    <div class="learning-support-head">
      <div>
        <span>继续学习</span>
        <h3>${escapeHtml(data.learning_objective || "巩固本题并完成一次自我检查")}</h3>
      </div>
      ${stage ? `<small>${escapeHtml(stage)}</small>` : ""}
    </div>
    ${data.one_sentence_takeaway ? `<p class="learning-takeaway">${escapeHtml(data.one_sentence_takeaway)}</p>` : ""}
    <div class="learning-columns">
      ${learningList("学习路径", path)}
      ${selfCheckHtml(checks)}
      ${learningList("下一步", next)}
    </div>
    ${navigation ? navigationHtml(navigation) : ""}
    ${scenarios.length ? scenarioHtml(scenarios[0]) : ""}
    ${data.misconception ? `<p class="learning-warning"><strong>注意：</strong>${escapeHtml(String(data.misconception).replace(/^注意[:：]\s*/, ""))}</p>` : ""}
  `;
}

function learningList(title, items) {
  if (!items.length) return "";
  return `<section class="learning-block">
    <h4>${escapeHtml(title)}</h4>
    <ol>${items.slice(0, 4).map((item) => `<li>${escapeHtml(typeof item === "string" ? item : item.instruction || "")}</li>`).join("")}</ol>
  </section>`;
}

function selfCheckHtml(items) {
  if (!items.length) return "";
  return `<section class="learning-block">
    <h4>自我检查</h4>
    ${items.slice(0, 3).map((item) => {
      const question = typeof item === "string" ? item : item.question || "";
      const answer = typeof item === "string" ? "" : item.answer_hint || item.answer || item.reference_answer || "";
      return `<details class="self-check-item">
        <summary>${escapeHtml(question)}</summary>
        ${answer ? `<p>${escapeHtml(answer)}</p>` : ""}
      </details>`;
    }).join("")}
  </section>`;
}

function navigationHtml(item) {
  const sequence = item.learning_sequence || [];
  if (!sequence.length) return "";
  return `<section class="learning-flow">
    <h4>${escapeHtml(item.title || "本章学习路线")}</h4>
    <div>${sequence.map((step, index) => `<span><b>${index + 1}</b>${escapeHtml(step)}</span>`).join("")}</div>
  </section>`;
}

function scenarioHtml(item) {
  return `<details class="learning-scenario">
    <summary>情境练习：${escapeHtml(item.scenario_description || item.scenario_title || "")}</summary>
    <p>${escapeHtml(item.student_task || "")}</p>
    ${learningList("完成步骤", item.task_steps || [])}
  </details>`;
}

function renderAnswerCardDetail(data) {
  const card = data.answer_card || {};
  const kps = data.knowledge_points || [];
  const chunks = data.source_chunks || [];
  const qa = data.qa_cases || [];
  els.detailId.textContent = card.answer_id || "-";
  els.cardDetail.innerHTML = `<div class="detail-section">
      <h3>${escapeHtml(card.canonical_question || "")}</h3>
      <dl class="detail-grid">
        <div><dt>答案模式</dt><dd>${escapeHtml(card.answer_mode)}</dd></div>
        <div><dt>状态</dt><dd>${escapeHtml(card.status)}</dd></div>
        <div><dt>章节位置</dt><dd>${escapeHtml(card.section_id)}</dd></div>
        <div><dt>测试题</dt><dd>${qa.length}</dd></div>
      </dl>
    </div>
    <div class="detail-section">
      <h4>必须覆盖</h4>
      ${renderSmallList(card.must_include || [])}
    </div>
    <div class="detail-section">
      <h4>关联知识点</h4>
      ${renderSmallList(kps.map((kp) => `${kp.kp_id} · ${kp.title}`))}
    </div>
    <div class="detail-section">
      <h4>证据片段</h4>
      ${chunks.length ? chunks.map((chunk) => `<p class="excerpt">${escapeHtml(chunk.source_excerpt || "").slice(0, 220)}...</p>`).join("") : "<p class=\"muted-text\">暂无证据片段</p>"}
    </div>`;
}

function renderSmallList(items) {
  if (!items.length) return "<p class=\"muted-text\">暂无</p>";
  return `<ul class="small-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function rememberQuestion(data) {
  if (!data?.question) return;
  const history = getJson(storage.history, []);
  const entry = {
    question: data.question,
    answer_id: data.answer_id,
    chapter_id: data.chapter_id || state.chapterId,
    confidence: data.confidence,
    mode: selectedMode(),
    time: new Date().toLocaleString()
  };
  const next = [entry, ...history.filter((item) => item.question !== entry.question)].slice(0, 12);
  setJson(storage.history, next);
  renderHistory();
}

function renderHistory() {
  const history = getJson(storage.history, []);
  if (!history.length) {
    els.historyList.className = "history-list empty";
    els.historyList.textContent = "暂无历史";
    return;
  }
  els.historyList.className = "history-list";
  els.historyList.innerHTML = history
    .map(
      (item) => `<button type="button" data-history="${escapeHtml(item.question)}">
        <strong>${escapeHtml(item.question)}</strong>
        <span>${escapeHtml(chapters[item.chapter_id]?.label || "本章")} · ${escapeHtml(item.time)}</span>
      </button>`
    )
    .join("");
}

async function loadEvalRuns() {
  els.evalRuns.className = "eval-list";
  els.evalRuns.textContent = "正在加载评测记录...";
  els.failureList.className = "failure-list empty";
  els.failureList.textContent = "暂无失败样例";
  try {
    const response = await fetch(`${apiBase()}/eval-runs?limit=5`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderEvalRuns(data.runs || []);
  } catch (error) {
    els.evalRuns.className = "eval-list empty";
    els.evalRuns.textContent = error.message;
  }
}

function renderEvalRuns(runs) {
  if (!runs.length) {
    els.evalRuns.className = "eval-list empty";
    els.evalRuns.textContent = "暂无评测记录";
    return;
  }
  els.evalRuns.className = "eval-list";
  els.evalRuns.innerHTML = runs
    .map((run, index) => {
      const metrics = run.metrics || {};
      const total = metrics.total ?? "-";
      const passed = metrics.passed ?? "-";
      const rate = typeof metrics.pass_rate === "number" ? `${(metrics.pass_rate * 100).toFixed(2)}%` : "-";
      const statusText = metrics.status && total === "-" ? metrics.status : `${passed}/${total} · ${rate}`;
      return `<button type="button" class="${index === 0 ? "active" : ""}" data-run-id="${escapeHtml(run.run_id)}">
        <strong>${escapeHtml(metrics.retriever || run.run_id)}</strong>
        <span>${escapeHtml(statusText)}</span>
      </button>`;
    })
    .join("");
  loadFailures(runs[0].run_id);
}

async function loadFailures(runId) {
  if (!runId) return;
  els.failureList.className = "failure-list";
  els.failureList.textContent = "正在加载失败样例...";
  try {
    const response = await fetch(`${apiBase()}/eval-failures?run_id=${encodeURIComponent(runId)}&limit=8`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderFailures(data.failures || []);
  } catch (error) {
    els.failureList.className = "failure-list empty";
    els.failureList.textContent = error.message;
  }
}

function renderFailures(failures) {
  if (!failures.length) {
    els.failureList.className = "failure-list empty";
    els.failureList.textContent = "本次评测无失败样例";
    return;
  }
  els.failureList.className = "failure-list";
  els.failureList.innerHTML = failures
    .map(
      (item) => `<article>
        <strong>${escapeHtml(item.test_id)}</strong>
        <p>${escapeHtml(item.question)}</p>
        <span>${escapeHtml(item.expected_answer_card)} -> ${escapeHtml(item.actual_answer_card)}</span>
      </article>`
    )
    .join("");
}

function updateFeedbackStatus() {
  const feedback = getJson(storage.feedback, []);
  const key = state.currentAnswer?.question;
  const existing = feedback.find((item) => item.question === key);
  els.feedbackStatus.textContent = existing ? "已保存" : "未保存";
  els.feedbackNote.value = existing?.note || "";
}

function saveFeedback() {
  if (!state.currentAnswer?.question) {
    els.feedbackStatus.textContent = "请先提问";
    return;
  }
  const feedback = getJson(storage.feedback, []);
  const entry = {
    question: state.currentAnswer.question,
    answer_id: state.currentAnswer.answer_id,
    retriever: state.currentAnswer.trace?.retriever,
    rating: state.selectedFeedback,
    note: els.feedbackNote.value.trim(),
    time: new Date().toLocaleString()
  };
  const next = [entry, ...feedback.filter((item) => item.question !== entry.question)].slice(0, 100);
  setJson(storage.feedback, next);
  els.feedbackStatus.textContent = "已保存";
}

function exportFeedback() {
  const feedback = getJson(storage.feedback, []);
  const blob = new Blob([JSON.stringify(feedback, null, 2)], { type: "application/json;charset=utf-8" });
  const link = document.createElement("a");
  const stamp = new Date().toISOString().slice(0, 19).replaceAll(":", "");
  link.href = URL.createObjectURL(blob);
  link.download = `road-kb-feedback-${stamp}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

function currentExamples() {
  return chapters[state.chapterId]?.examples || examples;
}

function initExamples() {
  els.examples.innerHTML = currentExamples()
    .map((question) => `<button type="button" data-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`)
    .join("");
}

async function loadQuestionBank() {
  if (!els.questionBank) return;
  try {
    const response = await fetch("./question-bank.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.questionBank = await response.json();
  } catch {
    state.questionBank = { chapters: {} };
  }
  renderQuestionBank();
}

function currentQuestionBank() {
  const chapter = state.questionBank?.chapters?.[state.chapterId];
  return Array.isArray(chapter?.questions) ? chapter.questions : [];
}

function renderQuestionBank() {
  if (!els.questionBank) return;
  const search = state.questionSearch.trim().toLowerCase();
  const allItems = currentQuestionBank();
  const filtered = allItems.filter((item) => {
    const categoryOk = state.questionFilter === "all" || item.category === state.questionFilter;
    const searchText = `${item.question || ""} ${item.category || ""} ${item.target_id || ""}`.toLowerCase();
    return categoryOk && (!search || searchText.includes(search));
  });
  const isFocusedView = state.questionBankExpanded || state.questionFilter !== "all" || !!search;
  const featured = allItems.filter((item) => item.pinned).concat(allItems.filter((item) => !item.pinned)).slice(0, 6);
  const items = isFocusedView ? filtered : featured;

  els.questionBankPanel.classList.toggle("expanded", isFocusedView);
  els.questionBankPanel.classList.toggle("compact", !isFocusedView);
  els.questionBankTools.hidden = !state.questionBankExpanded;
  els.questionBankToggle.textContent = state.questionBankExpanded ? "收起" : "展开";
  els.questionBankCount.textContent = isFocusedView ? `${items.length}/${allItems.length}` : `${items.length} 精选`;

  if (!items.length) {
    els.questionBank.className = "question-bank empty";
    els.questionBank.textContent = "暂无匹配问题";
    return;
  }
  els.questionBank.className = `question-bank ${isFocusedView ? "expanded" : "compact"}`;
  els.questionBank.innerHTML = items
    .map((item) => questionBankItemHtml(item))
    .join("");
}

function questionBankItemHtml(item) {
  const target = state.questionBankExpanded && item.target_id ? `<span>${escapeHtml(item.target_id)}</span>` : "";
  const pinned = item.pinned ? `<span>优选</span>` : "";
  return `<button class="question-card" type="button" data-bank-question="${escapeHtml(item.question)}">
    <strong>${escapeHtml(item.question)}</strong>
    <small>
      <span>${escapeHtml(item.category || "题库")}</span>
      ${target}
      ${pinned}
    </small>
  </button>`;
}

function initChapters() {
  const panel = document.querySelector("[data-chapter]")?.closest(".panel");
  if (panel) {
    Object.entries(chapters).forEach(([chapterId, chapter]) => {
      if (panel.querySelector(`[data-chapter="${chapterId}"]`)) return;
      const button = document.createElement("button");
      button.className = "chapter";
      button.type = "button";
      button.dataset.chapter = chapterId;
      button.innerHTML = `<span>${escapeHtml(chapter.label)}</span><strong>${escapeHtml(chapter.title)}</strong>`;
      panel.appendChild(button);
    });
    els.chapterButtons = document.querySelectorAll("[data-chapter]");
  }
  els.chapterButtons.forEach((button) => {
    const chapter = chapters[button.dataset.chapter];
    if (!chapter) return;
    button.querySelector("span").textContent = chapter.label;
    button.querySelector("strong").textContent = chapter.title;
  });
}

function syncResolvedChapter(chapterId) {
  if (!chapterId || !chapters[chapterId] || chapterId === state.chapterId) return;
  state.chapterId = chapterId;
  state.questionBankExpanded = false;
  state.questionFilter = "all";
  state.questionSearch = "";
  if (els.questionSearch) els.questionSearch.value = "";
  els.questionTabs.querySelectorAll("[data-question-filter]").forEach((item) => {
    item.classList.toggle("active", item.dataset.questionFilter === "all");
  });
  els.chapterButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.chapter === chapterId);
  });
  initExamples();
  renderQuestionBank();
  checkHealth();
  loadEvalRuns();
  loadChapterResources();
  loadOperationTasks();
}

function selectChapter(chapterId, askFirstExample = false) {
  if (!chapters[chapterId]) return;
  state.chapterId = chapterId;
  state.questionBankExpanded = false;
  state.questionFilter = "all";
  state.questionSearch = "";
  if (els.questionSearch) els.questionSearch.value = "";
  els.questionTabs.querySelectorAll("[data-question-filter]").forEach((item) => {
    item.classList.toggle("active", item.dataset.questionFilter === "all");
  });
  els.chapterButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.chapter === chapterId);
  });
  initExamples();
  renderQuestionBank();
  const first = currentExamples()[0] || "";
  if (first) els.questionInput.value = first;
  checkHealth();
  loadEvalRuns();
  loadChapterResources();
  loadOperationTasks();
  if (askFirstExample && first) ask(first);
}

function applyUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const chapter = params.get("chapter") || params.get("chapter_id");
  if (chapter && chapters[chapter]) {
    selectChapter(chapter);
  }
  const mode = params.get("mode");
  if (["keyword", "vectors", "db"].includes(mode)) {
    const input = document.querySelector(`input[name='mode'][value='${mode}']`);
    if (input) input.checked = true;
  }
  const api = params.get("api");
  if (api) els.apiBase.value = api;
  const question = params.get("q");
  if (question) {
    els.questionInput.value = question;
    ask(question);
  }
}

els.askButton.addEventListener("click", () => {
  const question = els.questionInput.value.trim();
  if (question) ask(question);
});

els.questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    const question = els.questionInput.value.trim();
    if (question) ask(question);
  }
});

els.examples.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button) return;
  els.questionInput.value = button.dataset.question;
  ask(button.dataset.question);
});

els.questionBank.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-bank-question]");
  if (!button) return;
  els.questionInput.value = button.dataset.bankQuestion;
  ask(button.dataset.bankQuestion);
});

els.questionBankToggle.addEventListener("click", () => {
  state.questionBankExpanded = !state.questionBankExpanded;
  if (!state.questionBankExpanded) {
    state.questionFilter = "all";
    state.questionSearch = "";
    els.questionSearch.value = "";
    els.questionTabs.querySelectorAll("[data-question-filter]").forEach((item) => {
      item.classList.toggle("active", item.dataset.questionFilter === "all");
    });
  }
  renderQuestionBank();
});

els.questionTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-question-filter]");
  if (!button) return;
  state.questionFilter = button.dataset.questionFilter;
  els.questionTabs.querySelectorAll("[data-question-filter]").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  renderQuestionBank();
});

els.questionSearch.addEventListener("input", () => {
  state.questionSearch = els.questionSearch.value;
  renderQuestionBank();
});

els.historyList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-history]");
  if (!button) return;
  const item = getJson(storage.history, []).find((entry) => entry.question === button.dataset.history);
  if (item?.chapter_id) selectChapter(item.chapter_id);
  els.questionInput.value = button.dataset.history;
  ask(button.dataset.history);
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-chapter]");
  if (!button) return;
  selectChapter(button.dataset.chapter, true);
});

els.clearHistory.addEventListener("click", () => {
  localStorage.removeItem(storage.history);
  renderHistory();
});

els.hits.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-detail]");
  if (button) loadAnswerCard(button.dataset.detail);
});

els.evalRuns.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-run-id]");
  if (!button) return;
  els.evalRuns.querySelectorAll("button").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  loadFailures(button.dataset.runId);
});

els.refreshEval.addEventListener("click", loadEvalRuns);
els.refreshChapterResources.addEventListener("click", loadChapterResources);
if (els.refreshOperationTasks) {
  els.refreshOperationTasks.addEventListener("click", loadOperationTasks);
}
els.saveFeedback.addEventListener("click", saveFeedback);
els.exportFeedback.addEventListener("click", exportFeedback);

if (els.operationTasks) {
  els.operationTasks.addEventListener("click", (event) => {
    const button = event.target.closest("[data-operation-task]");
    if (!button) return;
    els.operationTasks.querySelectorAll("[data-operation-task]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    loadOperationTaskDetail(button.dataset.operationTask);
  });
}

if (els.operationTaskDetail) {
  els.operationTaskDetail.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-detail]");
    if (button) loadAnswerCard(button.dataset.detail);
  });
}

els.resourceTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-resource-filter]");
  if (!button) return;
  state.resourceFilter = button.dataset.resourceFilter;
  els.resourceTabs.querySelectorAll("[data-resource-filter]").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  renderChapterResources();
});

document.querySelectorAll("[data-feedback]").forEach((button) => {
  button.addEventListener("click", () => {
    state.selectedFeedback = button.dataset.feedback;
    document.querySelectorAll("[data-feedback]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  });
});

els.apiBase.addEventListener("change", () => {
  checkHealth();
  loadEvalRuns();
  loadChapterResources();
  loadOperationTasks();
});

document.querySelectorAll("input[name='mode']").forEach((input) => {
  input.addEventListener("change", () => {
    const question = els.questionInput.value.trim();
    if (question) ask(question);
  });
});

document.querySelector("[data-feedback='useful']").classList.add("active");
initChapters();
initExamples();
renderHistory();
checkHealth();
loadQuestionBank();
loadEvalRuns();
loadChapterResources();
loadOperationTasks();
applyUrlParams();
