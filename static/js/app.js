// HackRadar Frontend Application Logic

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initTheme();
  loadStats();
  loadRecentEvents();
  loadSources();
  initEventListeners();
});

function initTabs() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const targetBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetBtn && targetPane) {
    targetBtn.classList.add("active");
    targetPane.classList.add("active");
  }

  if (tabId === "events") loadAllEvents();
  if (tabId === "sources") loadFullSources();
  if (tabId === "logs") loadLogsAndRuns();
}

function initTheme() {
  const toggleBtn = document.getElementById("btn-theme-toggle");
  const savedTheme = localStorage.getItem("hr_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  toggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("hr_theme", next);
  });
}

function initEventListeners() {
  // Manual monitor trigger
  const runBtn = document.getElementById("btn-trigger-monitor");
  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    runBtn.innerText = "⏳ Running...";
    try {
      const resp = await fetch("/api/monitor/trigger", { method: "POST" });
      const data = await resp.json();
      alert(`Monitoring Cycle Completed!\nNew events: ${data.results.new_events_found}\nTotal found: ${data.results.total_events_found}`);
      loadStats();
      loadRecentEvents();
    } catch (e) {
      alert("Error triggering monitor: " + e);
    } finally {
      runBtn.disabled = false;
      runBtn.innerText = "⚡ Run Monitor";
    }
  });

  // Test Telegram button
  const testNotifBtn = document.getElementById("btn-test-notif");
  testNotifBtn.addEventListener("click", async () => {
    testNotifBtn.disabled = true;
    testNotifBtn.innerText = "⏳ Sending...";
    try {
      const resp = await fetch("/api/notifications/test", { method: "POST" });
      const data = await resp.json();
      if (resp.ok) {
        alert("✅ Telegram test message dispatched successfully!");
      } else {
        alert("⚠️ Telegram test failed: " + (data.detail || JSON.stringify(data)));
      }
    } catch (e) {
      alert("Error: " + e);
    } finally {
      testNotifBtn.disabled = false;
      testNotifBtn.innerText = "💬 Test Telegram";
    }
  });

  // Event search & filter
  const searchInput = document.getElementById("event-search-input");
  const sourceFilter = document.getElementById("event-source-filter");
  const modeFilter = document.getElementById("event-mode-filter");

  let timeoutId;
  const onFilterChange = () => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => loadAllEvents(), 300);
  };

  searchInput.addEventListener("input", onFilterChange);
  sourceFilter.addEventListener("change", onFilterChange);
  modeFilter.addEventListener("change", onFilterChange);
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    document.getElementById("stat-total-events").innerText = data.total_events || 0;
    document.getElementById("stat-new-today").innerText = data.new_today || 0;
    document.getElementById("stat-active-sources").innerText = data.active_sources || 0;
    document.getElementById("stat-failed-sources").innerText = `${data.failed_sources || 0} failed`;
    document.getElementById("stat-total-users").innerText = data.total_users || 0;
    document.getElementById("stat-total-notifs").innerText = data.total_notifications || 0;
  } catch (e) {
    console.error("Error loading stats:", e);
  }
}

async function loadRecentEvents() {
  try {
    const res = await fetch("/api/events?limit=8");
    const data = await res.json();
    const tbody = document.getElementById("recent-events-table");
    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem;">No hackathons discovered yet. Click 'Run Monitor' above!</td></tr>`;
      return;
    }

    tbody.innerHTML = data.items.map(ev => {
      const mode = ev.online ? "Online" : (ev.location || "Offline");
      const prize = ev.prize_pool || "—";
      const deadline = ev.registration_deadline ? new Date(ev.registration_deadline).toLocaleDateString() : "Open";
      return `
        <tr>
          <td>
            <strong>${escapeHtml(ev.title)}</strong>
            ${ev.is_demo ? '<span class="badge badge-warning" style="margin-left: 4px;">DEMO</span>' : ''}
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(ev.organizer || '')}</div>
          </td>
          <td><span class="badge badge-source">${escapeHtml(ev.source)}</span></td>
          <td>${escapeHtml(mode)}</td>
          <td><strong style="color: var(--accent);">${escapeHtml(prize)}</strong></td>
          <td>${deadline}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="showEventDetails(${ev.id})">Details</button>
            <a href="${ev.registration_url || ev.url}" target="_blank" class="btn btn-sm" style="text-decoration:none;">View &rarr;</a>
          </td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    console.error("Error loading recent events:", e);
  }
}

async function loadAllEvents() {
  const search = document.getElementById("event-search-input").value;
  const source = document.getElementById("event-source-filter").value;
  const mode = document.getElementById("event-mode-filter").value;

  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (source) params.append("source", source);
  if (mode) params.append("mode", mode);
  params.append("limit", "100");

  try {
    const res = await fetch(`/api/events?${params.toString()}`);
    const data = await res.json();
    const tbody = document.getElementById("all-events-table");
    document.getElementById("events-count-label").innerText = `Showing ${data.items.length} of ${data.total} events`;

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">No matching events found.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.items.map(ev => {
      const locMode = ev.online ? "🌐 Online" : `📍 ${ev.location || 'In-Person'}`;
      const dates = ev.start_datetime ? new Date(ev.start_datetime).toLocaleDateString() : 'TBD';
      return `
        <tr>
          <td>
            <strong>${escapeHtml(ev.title)}</strong>
            ${ev.is_demo ? '<span class="badge badge-warning">DEMO</span>' : ''}
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(ev.organizer || '')}</div>
          </td>
          <td><span class="badge badge-source">${escapeHtml(ev.source)}</span></td>
          <td>${escapeHtml(locMode)}</td>
          <td>${dates}</td>
          <td>${escapeHtml(ev.prize_pool || '—')}</td>
          <td><span class="badge badge-success">${ev.status}</span></td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="showEventDetails(${ev.id})">Details</button>
            <a href="${ev.registration_url || ev.url}" target="_blank" class="btn btn-sm" style="text-decoration:none;">Register</a>
          </td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    console.error("Error loading all events:", e);
  }
}

async function loadSources() {
  try {
    const res = await fetch("/api/sources");
    const sources = await res.json();
    const tbody = document.getElementById("dashboard-sources-table");
    tbody.innerHTML = sources.map(s => {
      const statusBadge = s.enabled ?
        (s.last_error ? `<span class="badge badge-warning">Issue</span>` : `<span class="badge badge-success">Active</span>`) :
        `<span class="badge badge-danger">Disabled</span>`;

      return `
        <tr>
          <td><strong>${escapeHtml(s.display_name)}</strong></td>
          <td><code>${s.source_type}</code></td>
          <td>${statusBadge}</td>
          <td>${s.events_discovered}</td>
          <td>${s.last_checked_at ? new Date(s.last_checked_at).toLocaleTimeString() : 'Never'}</td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    console.error("Error loading sources:", e);
  }
}

async function loadFullSources() {
  try {
    const res = await fetch("/api/sources");
    const sources = await res.json();
    const tbody = document.getElementById("full-sources-table");
    tbody.innerHTML = sources.map(s => {
      const statusBadge = s.enabled ?
        (s.last_error ? `<span class="badge badge-warning">Degraded</span>` : `<span class="badge badge-success">Healthy</span>`) :
        `<span class="badge badge-danger">Disabled</span>`;

      return `
        <tr>
          <td>
            <strong>${escapeHtml(s.display_name)}</strong>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(s.name)}</div>
          </td>
          <td><code style="font-size: 0.75rem;">${escapeHtml(s.base_url || '—')}</code></td>
          <td><code>${s.source_type}</code></td>
          <td>${statusBadge} ${s.last_error ? `<div style="font-size: 0.7rem; color: var(--danger);">${escapeHtml(s.last_error.slice(0, 60))}</div>` : ''}</td>
          <td>${s.events_discovered}</td>
          <td>${s.last_success_at ? new Date(s.last_success_at).toLocaleString() : 'Never'}</td>
          <td>
            <button class="btn btn-sm ${s.enabled ? 'btn-secondary' : 'btn'}" onclick="toggleSource(${s.id}, ${!s.enabled})">
              ${s.enabled ? 'Disable' : 'Enable'}
            </button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    console.error("Error loading full sources:", e);
  }
}

async function toggleSource(id, enable) {
  try {
    const res = await fetch(`/api/sources/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: enable })
    });
    if (res.ok) {
      loadFullSources();
      loadSources();
      loadStats();
    }
  } catch (e) {
    alert("Error toggling source: " + e);
  }
}

async function loadLogsAndRuns() {
  try {
    // 1. Runs
    const runsRes = await fetch("/api/monitor/runs");
    const runs = await runsRes.json();
    const runsTable = document.getElementById("monitor-runs-table");
    if (runs.length === 0) {
      runsTable.innerHTML = `<tr><td colspan="6" style="text-align:center;">No monitoring runs recorded yet.</td></tr>`;
    } else {
      runsTable.innerHTML = runs.map(r => `
        <tr>
          <td>${new Date(r.started_at).toLocaleString()}</td>
          <td><span class="badge ${r.status === 'success' ? 'badge-success' : 'badge-warning'}">${r.status}</span></td>
          <td>${r.sources_succeeded}/${r.sources_checked}</td>
          <td>${r.total_events_found}</td>
          <td><strong style="color: var(--accent);">${r.new_events_found}</strong></td>
          <td>${r.notifications_sent}</td>
        </tr>
      `).join("");
    }

    // 2. Error logs
    const logsRes = await fetch("/api/logs");
    const logs = await logsRes.json();
    const logsTable = document.getElementById("error-logs-table");
    if (logs.length === 0) {
      logsTable.innerHTML = `<tr><td colspan="5" style="text-align:center;">No errors logged! 🎉</td></tr>`;
    } else {
      logsTable.innerHTML = logs.map(l => `
        <tr>
          <td>${new Date(l.created_at).toLocaleTimeString()}</td>
          <td><span class="badge badge-source">${escapeHtml(l.source || 'system')}</span></td>
          <td>${escapeHtml(l.component)}</td>
          <td><code>${escapeHtml(l.error_type)}</code></td>
          <td style="color: var(--danger); font-size: 0.75rem;">${escapeHtml(l.message)}</td>
        </tr>
      `).join("");
    }
  } catch (e) {
    console.error("Error loading logs and runs:", e);
  }
}

async function showEventDetails(id) {
  try {
    const res = await fetch(`/api/events/${id}`);
    const ev = await res.json();

    document.getElementById("modal-title").innerText = ev.title;
    const body = document.getElementById("modal-body");
    body.innerHTML = `
      <p><strong>Organizer:</strong> ${escapeHtml(ev.organizer || 'Unknown')}</p>
      <p><strong>Source:</strong> ${escapeHtml(ev.source)} (ID: ${escapeHtml(ev.source_event_id)})</p>
      <p><strong>Location:</strong> ${escapeHtml(ev.location || 'Online')} (Online: ${ev.online ? 'Yes' : 'No'})</p>
      <p><strong>Prize Pool:</strong> ${escapeHtml(ev.prize_pool || 'N/A')}</p>
      <p><strong>Registration Deadline:</strong> ${ev.registration_deadline ? new Date(ev.registration_deadline).toLocaleString() : 'Open'}</p>
      <p><strong>Categories:</strong> ${ev.categories.join(', ') || 'General'}</p>
      <p style="margin-top: 0.75rem;"><strong>Description:</strong><br>${escapeHtml(ev.description || 'No description provided.')}</p>
      <div style="margin-top: 1.25rem;">
        <a href="${ev.registration_url || ev.url}" target="_blank" class="btn btn-sm">Open Official Registration &rarr;</a>
      </div>
    `;

    document.getElementById("event-modal").classList.add("active");
  } catch (e) {
    alert("Error fetching event details: " + e);
  }
}

function closeModal() {
  document.getElementById("event-modal").classList.remove("active");
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
