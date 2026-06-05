const els = {
  chapterFilter: document.querySelector("#chapterFilter"),
  priorityFilter: document.querySelector("#priorityFilter"),
  decisionFilter: document.querySelector("#decisionFilter"),
  sceneFilter: document.querySelector("#sceneFilter"),
  searchInput: document.querySelector("#searchInput"),
  summary: document.querySelector("#summary"),
  itemList: document.querySelector("#itemList"),
  detailTitle: document.querySelector("#detailTitle"),
  detailMeta: document.querySelector("#detailMeta"),
  sourceText: document.querySelector("#sourceText"),
  candidateText: document.querySelector("#candidateText"),
  decisionInput: document.querySelector("#decisionInput"),
  notesInput: document.querySelector("#notesInput"),
  evidenceFacts: document.querySelector("#evidenceFacts"),
  approvalFile: document.querySelector("#approvalFile"),
  validationStatus: document.querySelector("#validationStatus"),
  loadDraft: document.querySelector("#loadDraft"),
  saveDraft: document.querySelector("#saveDraft"),
  copyJson: document.querySelector("#copyJson"),
  downloadJson: document.querySelector("#downloadJson"),
  downloadFilledJson: document.querySelector("#downloadFilledJson"),
  applySuggested: document.querySelector("#applySuggested"),
  clearFiltered: document.querySelector("#clearFiltered")
};

const state = {
  payload: null,
  scenePayload: null,
  items: [],
  filtered: [],
  selectedId: "",
  edits: new Map()
};

const decisionLabels = {
  confirm_candidate_anchor: "确认候选锚点",
  confirm_teaching_summary: "确认教学摘要",
  confirm_boundary_fragment: "确认边界片段",
  split_required: "需要拆分",
  reject_candidate: "拒绝候选",
  manual_anchor_pending: "继续人工查找锚点"
};

const API_BASE = "http://127.0.0.1:8768";

init();

async function init() {
  try {
    const response = await fetch("./source-review-data.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.payload = await response.json();
    state.items = (state.payload.decisions || []).map((item) => ({ ...item }));
    await loadScenePacket();
    applySceneMetadata();
    state.selectedId = itemKey(state.items[0] || {});
    populateFilters();
    bindEvents();
    render();
  } catch (error) {
    els.detailTitle.textContent = "复核数据加载失败";
    els.detailMeta.textContent = error.message;
  }
}

function populateFilters() {
  fillSelect(els.priorityFilter, unique(state.items.map((item) => item.priority_group)));
  fillSelect(els.decisionFilter, unique(state.items.map((item) => item.suggested_decision)), decisionLabels);
  fillSelect(els.sceneFilter, unique(state.items.map((item) => item.scene_title)));
}

function fillSelect(select, values, labels = {}) {
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labels[value] || value;
    select.appendChild(option);
  }
}

function bindEvents() {
  [els.chapterFilter, els.priorityFilter, els.decisionFilter, els.sceneFilter, els.searchInput].forEach((control) => {
    control.addEventListener("input", render);
  });
  els.decisionInput.addEventListener("input", updateCurrentEdit);
  els.notesInput.addEventListener("input", updateCurrentEdit);
  els.approvalFile.addEventListener("change", importApprovalJson);
  els.loadDraft.addEventListener("click", loadDraftFromApi);
  els.saveDraft.addEventListener("click", saveDraftToApi);
  els.copyJson.addEventListener("click", copyApprovalJson);
  els.downloadJson.addEventListener("click", downloadApprovalJson);
  els.downloadFilledJson.addEventListener("click", () => downloadApprovalJson(true));
  els.applySuggested.addEventListener("click", applySuggestedToFiltered);
  els.clearFiltered.addEventListener("click", clearFilteredEdits);
}

function render() {
  const query = els.searchInput.value.trim().toLowerCase();
  state.filtered = state.items.filter((item) => {
    if (els.chapterFilter.value && item.chapter_id !== els.chapterFilter.value) return false;
    if (els.priorityFilter.value && item.priority_group !== els.priorityFilter.value) return false;
    if (els.decisionFilter.value && item.suggested_decision !== els.decisionFilter.value) return false;
    if (els.sceneFilter.value && item.scene_title !== els.sceneFilter.value) return false;
    if (!query) return true;
    return [item.chunk_id, item.source_excerpt, item.candidate_text, item.priority_group, item.review_status, item.scene_title]
      .join("\n")
      .toLowerCase()
      .includes(query);
  });
  if (!state.filtered.some((item) => itemKey(item) === state.selectedId)) {
    state.selectedId = itemKey(state.filtered[0] || {});
  }
  renderSummary();
  renderList();
  renderDetail();
  renderValidation();
}

function renderSummary() {
  const rows = [
    ["总条目", state.items.length],
    ["当前筛选", state.filtered.length],
    ["已填写 decision", Array.from(state.edits.values()).filter((item) => item.decision).length],
    ["P1", state.filtered.filter((item) => String(item.priority_group).startsWith("P1")).length],
    ["P2", state.filtered.filter((item) => String(item.priority_group).startsWith("P2")).length],
    ["P3/P4", state.filtered.filter((item) => /^P[34]/.test(String(item.priority_group))).length],
    ["应用场景", unique(state.filtered.map((item) => item.scene_title)).length]
  ];
  els.summary.innerHTML = rows.map(([label, value]) => `<div class="summary-row"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`).join("");
}

function renderList() {
  if (!state.filtered.length) {
    els.itemList.innerHTML = `<div class="item-card"><strong>没有匹配条目</strong><small>调整筛选条件</small></div>`;
    return;
  }
  els.itemList.innerHTML = state.filtered
    .map((item) => {
      const key = itemKey(item);
      const edit = state.edits.get(key) || {};
      const active = key === state.selectedId ? " active" : "";
      const decision = edit.decision || item.suggested_decision || "";
      return `<button class="item-card${active}" type="button" data-key="${escapeHtml(key)}">
        <strong>${escapeHtml(item.chunk_id)}</strong>
        <small>${escapeHtml(item.priority_group)}</small>
        <span class="badge-row">
          <span class="badge">${escapeHtml(item.review_status)}</span>
          ${item.scene_title ? `<span class="badge scene">${escapeHtml(item.scene_title)}</span>` : ""}
          <span class="badge ${escapeHtml(decision)}">${escapeHtml(decisionLabels[decision] || decision || "待填写")}</span>
        </span>
      </button>`;
    })
    .join("");
  els.itemList.querySelectorAll("[data-key]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedId = button.dataset.key || "";
      render();
    });
  });
}

function renderDetail() {
  const item = selectedItem();
  if (!item) {
    els.detailTitle.textContent = "没有选中条目";
    els.detailMeta.textContent = "";
    els.sourceText.textContent = "";
    els.candidateText.textContent = "";
    els.evidenceFacts.innerHTML = "";
    return;
  }
  const key = itemKey(item);
  const edit = state.edits.get(key) || {};
  els.detailTitle.textContent = `${item.chapter_id} / ${item.chunk_id}`;
  els.detailMeta.textContent = [
    item.priority_group,
    item.review_status,
    item.scene_title,
    `建议：${decisionLabels[item.suggested_decision] || item.suggested_decision}`
  ].filter(Boolean).join(" · ");
  els.sourceText.textContent = item.source_excerpt || "";
  els.candidateText.textContent = item.candidate_text || "";
  els.decisionInput.value = edit.decision ?? item.decision ?? "";
  els.notesInput.value = edit.reviewer_notes ?? item.reviewer_notes ?? "";
  els.evidenceFacts.innerHTML = factsHtml(item);
}

function factsHtml(item) {
  const pairs = [
    ["应用场景", item.scene_title || ""],
    ["场景命中词", (item.scene_terms || []).join("; ")],
    ["候选段落", `${item.approved_paragraph_start || ""}-${item.approved_paragraph_end || ""}`],
    ["候选得分", item.candidate_score],
    ["分数差", item.score_margin],
    ["Source role", item.source_excerpt_role],
    ["匹配依据", (item.candidate_reasons || []).join("; ")],
    ["匹配术语", (item.matched_terms || []).join("; ")]
  ];
  return pairs.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value ?? "")}</dd>`).join("");
}

async function loadScenePacket() {
  try {
    const response = await fetch("../output/ch11_application_scene_review_packet_2026-06-05.json");
    if (!response.ok) return;
    state.scenePayload = await response.json();
  } catch (_error) {
    state.scenePayload = null;
  }
}

function applySceneMetadata() {
  const index = new Map();
  for (const group of state.scenePayload?.groups || []) {
    for (const item of group.items || []) {
      index.set(itemKey(item), {
        scene_id: item.scene_id || group.scene_id || "",
        scene_title: item.scene_title || group.scene_title || "",
        scene_terms: item.scene_terms || []
      });
    }
  }
  if (!index.size) return;
  state.items = state.items.map((item) => {
    const scene = index.get(itemKey(item));
    return scene ? { ...item, ...scene } : item;
  });
}

function updateCurrentEdit() {
  const item = selectedItem();
  if (!item) return;
  const key = itemKey(item);
  state.edits.set(key, {
    decision: els.decisionInput.value,
    reviewer_notes: els.notesInput.value
  });
  renderSummary();
  renderList();
  renderValidation();
}

function applySuggestedToFiltered() {
  for (const item of state.filtered) {
    const key = itemKey(item);
    state.edits.set(key, {
      decision: item.suggested_decision || "",
      reviewer_notes: suggestedNote(item)
    });
  }
  render();
}

function clearFilteredEdits() {
  for (const item of state.filtered) {
    state.edits.delete(itemKey(item));
  }
  render();
}

function suggestedNote(item) {
  if (item.suggested_decision === "confirm_candidate_anchor") {
    return "页面建议：Source_Chunk 与候选 Word 段落表达同一概念，可作为概念依据对应；不标记为教材逐字引用，仍需人工复核确认。";
  }
  if (item.suggested_decision === "confirm_teaching_summary") {
    return "页面建议：保留为教学摘要，术语锚点可支撑该 Source_Chunk；不标记为教材逐字引用，仍需人工复核确认。";
  }
  if (item.suggested_decision === "confirm_boundary_fragment") {
    return "页面建议：确认该条为边界/公式/列表片段，仅作证据边界记录；不标记为教材逐字引用，仍需人工复核确认。";
  }
  if (item.suggested_decision === "manual_anchor_pending") {
    return "页面建议：候选段落不稳定，继续人工回看教材原文，决定补锚点、拆分或重写边界。";
  }
  return "页面建议：需人工复核确认。";
}

function selectedItem() {
  return state.items.find((item) => itemKey(item) === state.selectedId) || null;
}

function approvalPayload(filledOnly = false) {
  const decisions = state.items.map((item) => {
    const edit = state.edits.get(itemKey(item)) || {};
    return {
      ...item,
      decision: edit.decision ?? item.decision ?? "",
      reviewer_notes: edit.reviewer_notes ?? item.reviewer_notes ?? ""
    };
  }).filter((item) => !filledOnly || item.decision);
  return {
    generated_at: new Date().toISOString(),
    source_boundary_review: "output/ch10_ch11_source_boundary_review_2026-06-05.json",
    instructions: state.payload.instructions || [],
    decisions
  };
}

async function copyApprovalJson() {
  const text = JSON.stringify(approvalPayload(), null, 2);
  await navigator.clipboard.writeText(text);
  els.copyJson.textContent = "已复制";
  window.setTimeout(() => (els.copyJson.textContent = "复制审批 JSON"), 1200);
}

function downloadApprovalJson(filledOnly = false) {
  const text = JSON.stringify(approvalPayload(filledOnly), null, 2);
  const blob = new Blob([text], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filledOnly ? "ch10_ch11_source_boundary_manual_approvals.filled.json" : "ch10_ch11_source_boundary_manual_approvals.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function importApprovalJson(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const payload = JSON.parse(await file.text());
    const imported = mergeApprovalPayload(payload);
    showStatus(`已导入 ${imported} 条审批记录。`, "ok");
  } catch (error) {
    showStatus(`导入失败：${error.message}`, "error");
  } finally {
    event.target.value = "";
  }
}

async function loadDraftFromApi() {
  try {
    els.loadDraft.disabled = true;
    const response = await fetch(`${API_BASE}/source-review-approvals?target=draft`);
    const result = await response.json();
    if (!response.ok || result.ok === false) {
      throw new Error(result.error || `HTTP ${response.status}`);
    }
    if (!result.exists || !result.payload) {
      showStatus("尚未保存草稿。", "ok");
      return;
    }
    const imported = mergeApprovalPayload(result.payload);
    const warnings = result.validation?.warnings?.length ? `，警告 ${result.validation.warnings.length} 条` : "";
    showStatus(`已加载草稿 ${imported} 条${warnings}。`, "ok");
  } catch (error) {
    showStatus(`加载草稿失败：${error.message}`, "error");
  } finally {
    els.loadDraft.disabled = false;
  }
}

async function saveDraftToApi() {
  try {
    const issues = validatePayload(approvalPayload());
    if (issues.length) {
      showStatus(`草稿未保存，发现 ${issues.length} 个问题：${issues.slice(0, 3).join("；")}`, "error");
      return;
    }
    els.saveDraft.disabled = true;
    const response = await fetch(`${API_BASE}/source-review-approvals?target=draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(approvalPayload(), null, 2)
    });
    const result = await response.json();
    if (!response.ok || result.ok === false) {
      const errors = result.validation?.errors?.slice(0, 3).join("；") || result.error || `HTTP ${response.status}`;
      throw new Error(errors);
    }
    const summary = result.validation?.summary || {};
    const warnings = result.validation?.warnings?.length ? `，警告 ${result.validation.warnings.length} 条` : "";
    showStatus(`草稿已保存：${summary.non_empty_decisions || 0} 条非空 decision${warnings}。`, "ok");
  } catch (error) {
    showStatus(`保存草稿失败：${error.message}`, "error");
  } finally {
    els.saveDraft.disabled = false;
  }
}

function mergeApprovalPayload(payload) {
  const decisions = Array.isArray(payload.decisions) ? payload.decisions : [];
  let imported = 0;
  for (const item of decisions) {
    const key = itemKey(item);
    if (!state.items.some((source) => itemKey(source) === key)) continue;
    state.edits.set(key, {
      decision: item.decision || "",
      reviewer_notes: item.reviewer_notes || ""
    });
    imported += 1;
  }
  render();
  return imported;
}

function showStatus(message, type = "ok") {
  els.validationStatus.textContent = message;
  els.validationStatus.className = `validation-status ${type}`;
}

function renderValidation() {
  const payload = approvalPayload();
  const issues = validatePayload(payload);
  const filled = payload.decisions.filter((item) => item.decision).length;
  if (!issues.length) {
    els.validationStatus.textContent = filled ? `已填写 ${filled} 条，页面内校验通过。导出后仍建议运行脚本复核。` : "尚未填写审批决策。";
    els.validationStatus.className = "validation-status ok";
    return;
  }
  els.validationStatus.textContent = `发现 ${issues.length} 个问题：${issues.slice(0, 3).join("；")}`;
  els.validationStatus.className = "validation-status error";
}

function validatePayload(payload) {
  const allowed = new Set(["", "confirm_candidate_anchor", "confirm_teaching_summary", "confirm_boundary_fragment", "split_required", "reject_candidate", "manual_anchor_pending"]);
  const issues = [];
  const seen = new Set();
  for (const item of payload.decisions) {
    const key = itemKey(item);
    if (seen.has(key)) issues.push(`${key} 重复`);
    seen.add(key);
    if (!allowed.has(item.decision || "")) issues.push(`${key} decision 不合法`);
    if (item.decision && item.decision.startsWith("confirm_")) {
      if (!Number(item.approved_paragraph_start) || !Number(item.approved_paragraph_end)) {
        issues.push(`${key} 缺少段落范围`);
      }
      if (!String(item.reviewer_notes || "").trim()) {
        issues.push(`${key} 确认项缺少 reviewer_notes`);
      }
    }
  }
  return issues;
}

function itemKey(item) {
  return `${item.chapter_id || ""}/${item.chunk_id || ""}`;
}

function unique(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
