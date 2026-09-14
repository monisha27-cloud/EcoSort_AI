// =========================================================================
// EcoSort AI — frontend application logic
// Talks to the Flask backend (API_BASE) and runs a pretrained MobileNet
// model client-side (TensorFlow.js) for the computer-vision scan feature.
// =========================================================================

// ------------------------------------------------------------- navigation
const navButtons = document.querySelectorAll(".nav button");
const views = document.querySelectorAll(".view");

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    navButtons.forEach((b) => b.classList.remove("active"));
    views.forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("active");
    if (btn.dataset.view === "catalog") loadCatalog();
    if (btn.dataset.view === "dashboard") loadDashboard();
  });
});

// ------------------------------------------------------------- backend health
async function checkHealth() {
  const pulse = document.getElementById("apiPulse");
  const label = document.getElementById("apiStatus");
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error();
    pulse.classList.remove("off");
    label.textContent = "Backend connected";
  } catch {
    pulse.classList.add("off");
    label.textContent = "Backend offline — run backend/app.py";
  }
}
checkHealth();
setInterval(checkHealth, 8000);

// ------------------------------------------------------------- helpers
function streamClassFor(item) {
  if (item.hazard_level === "High") return "stream-hazard";
  if (item.e_waste === "Yes") return "stream-ewaste";
  if (item.recyclable === "Yes") return "stream-recycle";
  if (item.reuse_possible === "Yes" || item.reuse_possible === "Depends") return "stream-reuse";
  return "stream-general";
}

function streamLabelFor(item) {
  if (item.hazard_level === "High") return "High hazard";
  if (item.e_waste === "Yes") return "E-waste";
  if (item.recyclable === "Yes") return "Recyclable";
  if (item.reuse_possible === "Yes" || item.reuse_possible === "Depends") return "Reusable";
  return "General waste";
}

// =========================================================================
// SCAN VIEW — camera + MobileNet + backend lookup
// =========================================================================
const video = document.getElementById("video");
const previewImg = document.getElementById("previewImg");
const cameraPlaceholder = document.getElementById("cameraPlaceholder");
const btnStartCam = document.getElementById("btnStartCam");
const btnStopCam = document.getElementById("btnStopCam");
const btnCapture = document.getElementById("btnCapture");
const fileInput = document.getElementById("fileInput");
const modelStatus = document.getElementById("modelStatus");
const modelStatusFooter = document.getElementById("modelStatusFooter");
const resultPanel = document.getElementById("resultPanel");

let mobilenetModel = null;
let stream = null;

async function loadModel() {
  try {
    mobilenetModel = await mobilenet.load({ version: 2, alpha: 1.0 });
    modelStatus.textContent = "Vision model ready (MobileNet v2, runs locally in your browser).";
    modelStatusFooter.textContent = "Vision model: ready";
  } catch (err) {
    modelStatus.textContent = "Couldn't load the vision model — check your internet connection.";
    modelStatusFooter.textContent = "Vision model: failed to load";
    console.error(err);
  }
}
loadModel();

btnStartCam.addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    video.srcObject = stream;
    video.style.display = "block";
    previewImg.style.display = "none";
    cameraPlaceholder.style.display = "none";
    btnCapture.disabled = false;
    btnStopCam.disabled = false;
    btnStartCam.disabled = true;
  } catch (err) {
    alert("Couldn't access the camera. You can still upload a photo instead.");
    console.error(err);
  }
});

btnStopCam.addEventListener("click", () => {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  video.style.display = "none";
  cameraPlaceholder.style.display = "flex";
  btnCapture.disabled = true;
  btnStopCam.disabled = true;
  btnStartCam.disabled = false;
});

btnCapture.addEventListener("click", async () => {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  await classifyElement(canvas, "camera");
});

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  previewImg.style.display = "block";
  video.style.display = "none";
  cameraPlaceholder.style.display = "none";
  previewImg.onload = () => classifyElement(previewImg, "upload");
});

async function classifyElement(el, source) {
  if (!mobilenetModel) {
    resultPanel.innerHTML = `<div class="empty-state">Vision model is still loading — try again in a moment.</div>`;
    return;
  }
  resultPanel.innerHTML = `<div class="empty-state">Analysing image…</div>`;
  try {
    const predictions = await mobilenetModel.classify(el, 5);
    await lookupAndRender(predictions, source);
  } catch (err) {
    console.error(err);
    resultPanel.innerHTML = `<div class="empty-state">Something went wrong analysing the image.</div>`;
  }
}

async function lookupAndRender(predictions, source) {
  try {
    const res = await fetch(`${API_BASE}/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Send the top few guesses, not just the first - the backend checks
      // each in turn against the catalog, since the right answer is often
      // in 2nd or 3rd place rather than 1st.
      body: JSON.stringify({
        labels: predictions.map((p) => ({ className: p.className, probability: p.probability })),
        source,
      }),
    });
    const data = await res.json();
    renderResult(data);
  } catch (err) {
    resultPanel.innerHTML = `<div class="empty-state">Couldn't reach the backend. Is <span class="mono">app.py</span> running on port 5000?</div>`;
    console.error(err);
  }
}

function renderResult(data) {
  if (!data.matched) {
    resultPanel.innerHTML = `
      <h3>No confident match</h3>
      <div class="raw-label">CV guess: ${escapeHtml(data.raw_label)}</div>
      <div class="empty-state" style="padding: 30px 0;">${escapeHtml(data.message)}</div>
    `;
    return;
  }
  const item = data.item;
  const streamClass = streamClassFor(item);
  const streamLabel = streamLabelFor(item);

  resultPanel.innerHTML = `
    <h3>${escapeHtml(item.item)}</h3>
    <div class="raw-label">CV guess: "${escapeHtml(data.raw_label)}" → matched to catalog</div>
    <span class="pill ${streamClass}">${streamLabel}</span>
    <div style="margin-top:16px;">
      <div class="detail-row"><span class="k">Category</span><span class="v">${escapeHtml(item.category)}</span></div>
      <div class="detail-row"><span class="k">E-waste</span><span class="v">${escapeHtml(item.e_waste)}</span></div>
      <div class="detail-row"><span class="k">Hazard level</span><span class="v">${escapeHtml(item.hazard_level)}</span></div>
      <div class="detail-row"><span class="k">Recyclable</span><span class="v">${escapeHtml(item.recyclable)}</span></div>
      <div class="detail-row"><span class="k">Disposal method</span><span class="v">${escapeHtml(item.disposal_method)}</span></div>
      <div class="detail-row"><span class="k">Nearest bin</span><span class="v">${escapeHtml(item.campus_location)}</span></div>
      <div class="detail-row"><span class="k">Instruction</span><span class="v">${escapeHtml(item.instruction)}</span></div>
      <div class="detail-row"><span class="k">Reuse possible</span><span class="v">${escapeHtml(item.reuse_possible)}</span></div>
      <div class="detail-row"><span class="k">Reuse method</span><span class="v">${escapeHtml(item.reuse_method)}</span></div>
    </div>
  `;
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// =========================================================================
// CATALOG VIEW
// =========================================================================
const catalogBody = document.getElementById("catalogBody");
const searchInput = document.getElementById("searchInput");
const filterCategory = document.getElementById("filterCategory");
const filterHazard = document.getElementById("filterHazard");
const filterRecyclable = document.getElementById("filterRecyclable");

let categoriesLoaded = false;

async function loadCategoriesOnce() {
  if (categoriesLoaded) return;
  try {
    const res = await fetch(`${API_BASE}/categories`);
    const cats = await res.json();
    cats.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      filterCategory.appendChild(opt);
    });
    categoriesLoaded = true;
  } catch (err) {
    console.error(err);
  }
}

async function loadCatalog() {
  await loadCategoriesOnce();
  const params = new URLSearchParams();
  if (searchInput.value) params.set("search", searchInput.value);
  if (filterCategory.value) params.set("category", filterCategory.value);
  if (filterHazard.value) params.set("hazard_level", filterHazard.value);
  if (filterRecyclable.value) params.set("recyclable", filterRecyclable.value);

  catalogBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-dim); padding: 20px;">Loading…</td></tr>`;
  try {
    const res = await fetch(`${API_BASE}/items?${params.toString()}`);
    const data = await res.json();
    if (data.items.length === 0) {
      catalogBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-dim); padding: 20px;">No items match those filters.</td></tr>`;
      return;
    }
    catalogBody.innerHTML = data.items
      .map(
        (item) => `
      <tr>
        <td class="id-cell">#${item.record_id}</td>
        <td>${escapeHtml(item.item)}</td>
        <td>${escapeHtml(item.category)}</td>
        <td>${escapeHtml(item.hazard_level)}</td>
        <td>${escapeHtml(item.recyclable)}</td>
        <td>${escapeHtml(item.disposal_method)}</td>
        <td>${escapeHtml(item.campus_location)}</td>
        <td>${escapeHtml(item.instruction)}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    catalogBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-dim); padding: 20px;">Couldn't reach the backend on port 5000.</td></tr>`;
    console.error(err);
  }
}

let searchDebounce;
searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadCatalog, 250);
});
[filterCategory, filterHazard, filterRecyclable].forEach((el) =>
  el.addEventListener("change", loadCatalog)
);

// =========================================================================
// DASHBOARD VIEW
// =========================================================================
const barColors = {
  "IT Equipment": "var(--stream-ewaste)",
  "Peripheral": "var(--stream-ewaste)",
  "Small Electronics": "var(--stream-ewaste)",
  "Networking": "var(--stream-ewaste)",
  "Battery": "var(--stream-hazard)",
  "Lighting": "var(--stream-hazard)",
  "Plastic": "var(--stream-recycle)",
  "Glass": "var(--stream-recycle)",
  "Metal": "var(--stream-recycle)",
  "Paper": "var(--stream-recycle)",
  "General Waste": "var(--stream-general)",
  "Unknown": "var(--stream-general)",
  "Low": "var(--stream-recycle)",
  "Moderate": "var(--stream-ewaste)",
  "High": "var(--stream-hazard)",
};

function renderBarList(container, dataObj) {
  const entries = Object.entries(dataObj).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map((e) => e[1]), 1);
  container.innerHTML = entries
    .map(
      ([key, count]) => `
    <div class="bar-row">
      <div>${escapeHtml(key)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(count / max) * 100}%; background:${barColors[key] || "var(--stream-general)"};"></div></div>
      <div class="count">${count}</div>
    </div>`
    )
    .join("");
}

async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const stats = await res.json();

    document.getElementById("statTotalItems").textContent = stats.total_items;
    document.getElementById("statTotalScans").textContent = stats.total_scans;
    document.getElementById("statEwaste").textContent = stats.by_e_waste["Yes"] || 0;
    document.getElementById("statRecyclable").textContent = stats.by_recyclable["Yes"] || 0;

    renderBarList(document.getElementById("barCategory"), stats.by_category);
    renderBarList(document.getElementById("barHazard"), stats.by_hazard_level);
  } catch (err) {
    console.error(err);
  }

  try {
    const res2 = await fetch(`${API_BASE}/scan-logs?limit=15`);
    const logs = await res2.json();
    const logList = document.getElementById("logList");
    if (logs.length === 0) {
      logList.innerHTML = `<div class="empty-state">No scans yet — try the Scan tab.</div>`;
      return;
    }
    logList.innerHTML = logs
      .map(
        (log) => `
      <div class="log-row">
        <div>${escapeHtml(log.matched_item || log.predicted_label)} <span class="mono" style="color:var(--text-dim); font-size:11.5px;">(${escapeHtml(log.source)})</span></div>
        <div class="time">${escapeHtml(log.timestamp)}</div>
      </div>`
      )
      .join("");
  } catch (err) {
    console.error(err);
  }
}
