// vidsync Web UI 前端逻辑

const API = {
  platforms: "/api/platforms",
  scan: "/api/cookies/scan",
  publish: "/api/publish",
  status: (id) => `/api/status/${id}`,
  logs: (id) => `/api/logs/${id}`,
};

// ---- 平台状态加载 ----

async function loadPlatforms() {
  const resp = await fetch(API.platforms);
  const data = await resp.json();
  renderPlatforms(data.platforms);
  renderCheckboxes(data.platforms);
  document.getElementById("cookies-hint").textContent =
    `cookies 目录：${data.cookies_dir}`;
}

function renderPlatforms(platforms) {
  const grid = document.getElementById("platforms-grid");
  grid.innerHTML = "";
  for (const p of platforms) {
    const card = document.createElement("div");
    card.className = `platform-card ${p.ready ? "ready" : "not-ready"}`;
    card.innerHTML = `
      <div class="name">${p.name}</div>
      <div class="status">
        cookies: ${p.cookie_valid}/${p.cookie_total} 有效
      </div>
      ${p.ready
        ? '<span class="badge ready">✓ 就绪</span>'
        : '<span class="badge not-ready">✗ 缺 cookie</span>'}
      ${p.supported_in_v01
        ? '<span class="badge v01">v0.1</span>'
        : '<span class="badge" style="background:#8e8e93;color:white;">v0.2+</span>'}
    `;
    grid.appendChild(card);
  }
}

function renderCheckboxes(platforms) {
  const box = document.getElementById("platform-checkboxes");
  box.innerHTML = "";
  for (const p of platforms) {
    const label = document.createElement("label");
    if (!p.supported_in_v01) label.classList.add("disabled");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = p.id;
    cb.disabled = !p.supported_in_v01;
    if (p.supported_in_v01 && p.ready) cb.checked = true;
    label.appendChild(cb);
    label.appendChild(document.createTextNode(` ${p.name}`));
    box.appendChild(label);
  }
}

// ---- 重新扫描 ----

document.getElementById("rescan-btn").addEventListener("click", async () => {
  const btn = document.getElementById("rescan-btn");
  btn.disabled = true;
  btn.textContent = "扫描中...";
  try {
    const resp = await fetch(API.scan, { method: "POST" });
    const data = await resp.json();
    if (data.ok) {
      alert(`扫描完成：发现 ${Object.keys(data.mapped).length} 个平台的 cookies`);
      await loadPlatforms();
    } else {
      alert(`扫描失败：${data.error}`);
    }
  } catch (e) {
    alert(`扫描出错：${e}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "🔄 重新扫描 cookies";
  }
});

// ---- 表单提交 ----

document.getElementById("publish-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "处理中...";

  const form = e.target;
  const fd = new FormData();
  fd.append("video", document.getElementById("video").files[0]);
  fd.append("vertical_cover", document.getElementById("vertical_cover").files[0]);
  fd.append("horizontal_cover", document.getElementById("horizontal_cover").files[0]);
  fd.append("short_title", document.getElementById("short_title").value);
  fd.append("long_title", document.getElementById("long_title").value);
  fd.append("keywords", document.getElementById("keywords").value);
  fd.append("description", document.getElementById("description").value);

  // 选中的平台
  const checked = Array.from(document.querySelectorAll("#platform-checkboxes input:checked"))
    .map(cb => cb.value);
  fd.append("platforms", checked.join(","));

  if (checked.length === 0) {
    alert("请至少选择一个平台");
    submitBtn.disabled = false;
    submitBtn.textContent = "🚀 开始保存草稿";
    return;
  }

  // 显示进度区
  document.getElementById("progress-section").style.display = "block";
  document.getElementById("result-section").style.display = "none";
  document.getElementById("progress-log").innerHTML = "";

  appendLog(`启动发布任务，目标平台：${checked.join(", ")}`);

  try {
    const resp = await fetch(API.publish, { method: "POST", body: fd });
    const data = await resp.json();
    if (data.task_id) {
      appendLog(`任务已创建：${data.task_id}`);
      pollProgress(data.task_id);
    } else {
      appendLog(`❌ 任务创建失败：${JSON.stringify(data)}`, "failed");
    }
  } catch (e) {
    appendLog(`❌ 请求出错：${e}`, "failed");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "🚀 开始保存草稿";
  }
});

// ---- 进度查询（轮询 + WebSocket fallback）----

function appendLog(msg, cls = "") {
  const log = document.getElementById("progress-log");
  const line = document.createElement("div");
  line.className = `log-line ${cls}`;
  const ts = new Date().toLocaleTimeString("zh-CN");
  line.textContent = `[${ts}] ${msg}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

async function pollProgress(taskId) {
  // 简单轮询（v0.1 不用 WebSocket，避免兼容问题）
  let done = false;
  while (!done) {
    try {
      const resp = await fetch(API.status(taskId));
      const data = await resp.json();

      // 显示每个平台的状态
      for (const [pid, info] of Object.entries(data.platforms || {})) {
        const cls = info.status === "success" ? "success"
                  : info.status === "failed" ? "failed"
                  : "pending";
        appendLog(`[${pid}] ${info.status}: ${info.draft_url || info.error || ""}`, cls);
      }

      if (data.status === "completed" || data.status === "failed") {
        done = true;
        appendLog(`任务结束：${data.status}`,
                  data.status === "completed" ? "success" : "failed");
        showResult(data, taskId);
        break;
      }
    } catch (e) {
      appendLog(`查询状态出错：${e}`, "failed");
    }
    await new Promise(r => setTimeout(r, 2000));
  }
}

function showResult(taskData, taskId) {
  const section = document.getElementById("result-section");
  section.style.display = "block";
  const tableDiv = document.getElementById("result-table");

  let html = `<table>
    <thead><tr>
      <th>平台</th><th>状态</th><th>草稿链接</th><th>过期时间</th><th>备注</th>
    </tr></thead><tbody>`;
  for (const [pid, info] of Object.entries(taskData.platforms || {})) {
    const link = info.draft_url ? `<a href="${info.draft_url}" target="_blank">${info.draft_url}</a>` : "-";
    const expires = info.expires_at ? info.expires_at.replace("T", " ").substring(0, 19) : "-";
    const note = info.extra?.note || info.error || "";
    const statusColor = info.status === "success" ? "green"
                      : info.status === "failed" ? "red"
                      : "gray";
    html += `<tr>
      <td>${pid}</td>
      <td style="color:${statusColor}">${info.status}</td>
      <td>${link}</td>
      <td>${expires}</td>
      <td>${note}</td>
    </tr>`;
  }
  html += "</tbody></table>";
  tableDiv.innerHTML = html;

  // 显示日志目录
  if (taskData.run_dir) {
    document.getElementById("log-dir").textContent = taskData.run_dir;
  }
}

// ---- 初始化 ----

loadPlatforms();
