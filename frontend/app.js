const $ = (sel) => document.querySelector(sel);

const els = {
  left: $("#left"),
  right: $("#right"),
  format: $("#format"),
  title: $("#title"),
  ignore: $("#ignore"),
  compare: $("#compare"),
  summary: $("#summary"),
  diffWrap: $("#diff-wrap"),
  diffBody: $("#diff-body"),
  error: $("#error"),
  exportGroup: $("#export-group"),
  exportHtml: $("#export-html"),
  exportPdf: $("#export-pdf"),
  historyList: $("#history-list"),
  refreshHistory: $("#refresh-history"),
  loadLeft: $("#load-left"),
  loadRight: $("#load-right"),
  clearLeft: $("#clear-left"),
  clearRight: $("#clear-right"),
  toast: $("#toast"),
};

let current = null;

/* ---------------- helpers ---------------- */

function toast(msg, kind = "") {
  els.toast.textContent = msg;
  els.toast.className = "toast" + (kind ? " " + kind : "");
  els.toast.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (els.toast.hidden = true), 2800);
}

function parseIgnore(raw) {
  return (raw || "")
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function showError(msg) {
  els.error.textContent = msg;
  els.error.hidden = false;
  els.diffWrap.hidden = true;
  els.exportGroup.hidden = true;
  els.summary.innerHTML = '<span class="muted">Error — see below.</span>';
}

function hideError() {
  els.error.hidden = true;
  els.error.textContent = "";
}

function renderSummary(s) {
  if (s.identical) {
    els.summary.innerHTML =
      '<span class="pill identical">Identical</span> ' +
      `<span class="muted">${s.equal} lines compared</span>`;
    return;
  }
  els.summary.innerHTML = `
    <span class="pill equal">${s.equal} equal</span>
    <span class="pill added">${s.added} added</span>
    <span class="pill removed">${s.removed} removed</span>
    <span class="pill changed">${s.changed} changed</span>
  `;
}

function renderDiff(rows) {
  const frag = document.createDocumentFragment();
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.className = r.tag;
    tr.innerHTML = `
      <td class="ln">${r.left_no ?? ""}</td>
      <td class="code left"></td>
      <td class="ln">${r.right_no ?? ""}</td>
      <td class="code right"></td>
    `;
    tr.children[1].textContent = r.left || "\u00a0";
    tr.children[3].textContent = r.right || "\u00a0";
    frag.appendChild(tr);
  }
  els.diffBody.replaceChildren(frag);
  els.diffWrap.hidden = false;
  els.exportGroup.hidden = false;
}

/* ---------------- API calls ---------------- */

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.error || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

async function runCompare() {
  hideError();
  const body = {
    left: els.left.value,
    right: els.right.value,
    format: els.format.value,
    ignore: parseIgnore(els.ignore.value),
    title: els.title.value.trim() || "Untitled comparison",
    save: true,
  };
  if (!body.left && !body.right) {
    showError("Both sides are empty.");
    return;
  }
  els.compare.disabled = true;
  els.compare.textContent = "Comparing…";
  try {
    const data = await api("/api/compare", {
      method: "POST",
      body: JSON.stringify(body),
    });
    current = data;
    renderSummary(data.summary);
    renderDiff(data.rows);
    await loadHistory();
    toast("Comparison saved to history", "ok");
  } catch (e) {
    showError(e.message);
  } finally {
    els.compare.disabled = false;
    els.compare.textContent = "Compare";
  }
}

async function downloadExport(kind) {
  if (!current) return;
  const body = current.id
    ? { id: current.id }
    : {
        rows: current.rows,
        summary: current.summary,
        format: current.format,
        ignore: current.ignore,
        title: current.title,
        created_at: current.created_at,
      };
  const res = await fetch(`/api/export/${kind}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = j.error || msg;
    } catch {}
    toast(msg, "error");
    return;
  }
  const disp = res.headers.get("Content-Disposition") || "";
  const m = disp.match(/filename="([^"]+)"/);
  const fname = m ? m[1] : `diff.${kind}`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  toast(`Exported ${fname}`, "ok");
}

async function loadHistory() {
  try {
    const list = await api("/api/history");
    renderHistory(list);
  } catch (e) {
    console.error(e);
  }
}

function renderHistory(list) {
  els.historyList.innerHTML = "";
  if (!list.length) {
    els.historyList.innerHTML =
      '<li style="padding:14px;color:var(--muted);font-size:12px;">No comparisons yet.</li>';
    return;
  }
  for (const e of list) {
    const li = document.createElement("li");
    li.className = "history-item";
    li.dataset.id = e.id;
    const when = new Date(e.created_at).toLocaleString();
    const s = e.summary || {};
    const chips = s.identical
      ? '<span class="chip equal">identical</span>'
      : `<span class="chip added">+${s.added || 0}</span>` +
        `<span class="chip removed">−${s.removed || 0}</span>` +
        `<span class="chip changed">~${s.changed || 0}</span>`;
    li.innerHTML = `
      <button class="hi-del" title="Delete">&times;</button>
      <div class="hi-title">${escapeHtml(e.title || "Untitled")}</div>
      <div class="hi-meta"><span>${escapeHtml(e.format)}</span><span>${when}</span></div>
      <div class="hi-chips">${chips}</div>
    `;
    li.addEventListener("click", (ev) => {
      if (ev.target.classList.contains("hi-del")) return;
      loadHistoryEntry(e.id);
    });
    li.querySelector(".hi-del").addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await fetch(`/api/history/${e.id}`, { method: "DELETE" });
      if (current && current.id === e.id) current = null;
      await loadHistory();
    });
    els.historyList.appendChild(li);
  }
}

async function loadHistoryEntry(id) {
  try {
    const rec = await api(`/api/history/${id}`);
    current = rec;
    els.left.value = rec.left_raw ?? "";
    els.right.value = rec.right_raw ?? "";
    els.format.value = rec.format || "text";
    els.title.value = rec.title || "";
    els.ignore.value = (rec.ignore || []).join(", ");
    renderSummary(rec.summary);
    renderDiff(rec.rows);
    hideError();
  } catch (e) {
    toast(e.message, "error");
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

/* ---------------- file loading ---------------- */

function wireFile(input, target) {
  input.addEventListener("change", async () => {
    const file = input.files[0];
    if (!file) return;
    target.value = await file.text();
    const name = file.name.toLowerCase();
    if (name.endsWith(".json")) els.format.value = "json";
    else if (name.endsWith(".xml")) els.format.value = "xml";
    input.value = "";
  });
}

/* ---------------- keyboard ---------------- */

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    runCompare();
  }
});

/* ---------------- wire up ---------------- */

els.compare.addEventListener("click", runCompare);
els.refreshHistory.addEventListener("click", loadHistory);
els.exportHtml.addEventListener("click", () => downloadExport("html"));
els.exportPdf.addEventListener("click", () => downloadExport("pdf"));
els.clearLeft.addEventListener("click", () => (els.left.value = ""));
els.clearRight.addEventListener("click", () => (els.right.value = ""));
wireFile(els.loadLeft, els.left);
wireFile(els.loadRight, els.right);

loadHistory();
