/**
 * Beyond Identity — Interactive Frontend Logic
 * Connects to FastAPI endpoints: /auth, /listings, /incidents, /awareness, /health-assistant
 */

const API_BASE = ""; // Relative to current host
let currentAuthToken = localStorage.getItem("bi_token") || "";
let currentUser = JSON.parse(localStorage.getItem("bi_user") || "null");

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupAuthUI();
  loadStats();
  loadListings();
  setupIncidentForm();
  setupAwarenessUI();
  setupHealthAssistantUI();
});

// ==========================================
// Tabs Navigation
// ==========================================
function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add("active");

      // Trigger refreshes if necessary
      if (targetId === "tab-cases") loadIncidents();
    });
  });
}

// ==========================================
// Authentication & Demo User Switcher
// ==========================================
function setupAuthUI() {
  const userProfileEl = document.getElementById("user-profile-display");
  const loginModal = document.getElementById("login-modal");
  const openLoginBtn = document.getElementById("open-login-btn");
  const closeLoginBtn = document.getElementById("close-login-btn");

  if (openLoginBtn) openLoginBtn.addEventListener("click", () => loginModal.classList.add("active"));
  if (closeLoginBtn) closeLoginBtn.addEventListener("click", () => loginModal.classList.remove("active"));

  renderUserStatus();

  // Quick Demo Logins
  document.querySelectorAll(".demo-login-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const email = btn.getAttribute("data-email");
      const password = btn.getAttribute("data-password");
      await executeLogin(email, password);
      loginModal.classList.remove("active");
    });
  });

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      currentAuthToken = "";
      currentUser = null;
      localStorage.removeItem("bi_token");
      localStorage.removeItem("bi_user");
      renderUserStatus();
      loadListings();
    });
  }
}

async function executeLogin(email, password) {
  try {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!res.ok) throw new Error("Authentication failed");
    const data = await res.json();
    currentAuthToken = data.access_token;
    localStorage.setItem("bi_token", currentAuthToken);

    // Fetch user details
    const meRes = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${currentAuthToken}` },
    });
    if (meRes.ok) {
      currentUser = await meRes.json();
      localStorage.setItem("bi_user", JSON.stringify(currentUser));
    }

    renderUserStatus();
    alert(`Logged in successfully as ${currentUser?.name} (${currentUser?.role})`);
    loadIncidents();
  } catch (err) {
    alert("Login error: " + err.message);
  }
}

function renderUserStatus() {
  const container = document.getElementById("auth-actions-container");
  if (!container) return;

  if (currentUser && currentAuthToken) {
    container.innerHTML = `
      <div class="user-badge">
        <span>👤 <strong>${currentUser.name}</strong> (${currentUser.role})</span>
      </div>
      <button class="btn btn-outline-danger" id="logout-btn">Log out</button>
    `;
    document.getElementById("logout-btn").addEventListener("click", () => {
      currentAuthToken = "";
      currentUser = null;
      localStorage.removeItem("bi_token");
      localStorage.removeItem("bi_user");
      renderUserStatus();
    });

    // Show Verifier tab if verifier/admin
    const verifierTab = document.getElementById("tab-btn-cases");
    if (verifierTab) {
      verifierTab.style.display = "flex";
    }
  } else {
    container.innerHTML = `
      <button class="btn btn-primary" id="open-login-btn">Demo Login</button>
    `;
    document.getElementById("open-login-btn").addEventListener("click", () => {
      document.getElementById("login-modal").classList.add("active");
    });
  }
}

// ==========================================
// Stats Loader
// ==========================================
async function loadStats() {
  try {
    const resListings = await fetch(`${API_BASE}/listings/`);
    if (resListings.ok) {
      const data = await resListings.json();
      const countEl = document.getElementById("stat-listings-count");
      if (countEl) countEl.innerText = data.length + "+";
    }
  } catch (e) {
    console.error(e);
  }
}

// ==========================================
// Listings Directory
// ==========================================
async function loadListings(categoryFilter = "") {
  const container = document.getElementById("listings-container");
  if (!container) return;

  container.innerHTML = `<div style="text-align:center; padding: 40px; color: var(--text-muted);">Loading verified opportunities...</div>`;

  try {
    let url = `${API_BASE}/listings/`;
    if (categoryFilter) url += `?category=${encodeURIComponent(categoryFilter)}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load listings");
    const listings = await res.json();

    if (listings.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding: 40px; color: var(--text-muted);">No verified listings found in this category.</div>`;
      return;
    }

    container.innerHTML = listings
      .map((item) => {
        const badgeClass =
          item.status === "verified"
            ? "badge-verified"
            : item.status === "pending"
            ? "badge-pending"
            : "badge-delisted";

        return `
        <div class="listing-card">
          <div>
            <div class="card-top">
              <span class="category-tag">📂 ${item.category.toUpperCase()}</span>
              <span class="badge ${badgeClass}">${item.status}</span>
            </div>
            <h3 class="card-title">${escapeHtml(item.title)}</h3>
            <div class="card-org">🏛️ ${escapeHtml(item.organization_name || "Community Partner")}</div>
            <p class="card-desc">${escapeHtml(item.description || "No description provided.")}</p>
          </div>
          <div>
            <div class="card-footer">
              <span>📍 ${escapeHtml(item.location || "Pan-India")}</span>
              <span>📞 ${escapeHtml(item.contact_info || "Relay via Beyond Identity")}</span>
            </div>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-rose); padding:20px;">Error loading listings: ${err.message}</div>`;
  }
}

// Filter listeners
document.addEventListener("click", (e) => {
  if (e.target.matches(".filter-pill")) {
    document.querySelectorAll(".filter-pill").forEach((p) => p.classList.remove("active"));
    e.target.classList.add("active");
    const cat = e.target.getAttribute("data-cat");
    loadListings(cat);
  }
});

// ==========================================
// Discrimination Reporting
// ==========================================
function setupIncidentForm() {
  const form = document.getElementById("incident-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    submitBtn.innerText = "Submitting & Matching Schemes...";

    const payload = {
      incident_type: document.getElementById("inc-type").value,
      title: document.getElementById("inc-title").value,
      description: document.getElementById("inc-desc").value,
      incident_date: document.getElementById("inc-date").value || null,
      location_city: document.getElementById("inc-city").value,
      location_state: document.getElementById("inc-state").value,
      perpetrator_details: document.getElementById("inc-perpetrator").value || null,
      urgency_level: document.getElementById("inc-urgency").value,
      is_anonymous: document.getElementById("inc-anon").checked,
      contact_email: document.getElementById("inc-email").value || null,
    };

    try {
      const headers = { "Content-Type": "application/json" };
      if (currentAuthToken && !payload.is_anonymous) {
        headers["Authorization"] = `Bearer ${currentAuthToken}`;
      }

      const res = await fetch(`${API_BASE}/incidents/`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to submit report");
      const incident = await res.json();

      renderIncidentResultModal(incident);
      form.reset();
    } catch (err) {
      alert("Submission error: " + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = "Submit Incident Report";
    }
  });
}

function renderIncidentResultModal(incident) {
  const modal = document.getElementById("incident-result-modal");
  const content = document.getElementById("incident-result-content");
  if (!modal || !content) return;

  let schemesHtml = incident.matched_schemes
    .map(
      (s) => `
    <div style="background:rgba(255,255,255,0.04); padding:16px; border-radius:10px; margin-bottom:12px; border-left:3px solid var(--accent-cyan);">
      <h4 style="color:#fff; margin-bottom:4px;">${escapeHtml(s.name)}</h4>
      <div style="font-size:12px; color:var(--text-muted); margin-bottom:8px;">${escapeHtml(s.ministry_or_dept)}</div>
      <p style="font-size:13px; margin-bottom:8px;">${escapeHtml(s.benefits)}</p>
      ${s.helpline ? `<div style="font-size:12px; color:var(--accent-emerald);"><strong>Helpline:</strong> ${escapeHtml(s.helpline)}</div>` : ""}
      ${s.application_link ? `<a href="${s.application_link}" target="_blank" style="color:var(--accent-cyan); font-size:12px; text-decoration:underline;">Official Application Portal →</a>` : ""}
    </div>
  `
    )
    .join("");

  let ngosHtml = incident.matched_ngos
    .map(
      (n) => `
    <div style="background:rgba(255,255,255,0.04); padding:16px; border-radius:10px; margin-bottom:12px; border-left:3px solid var(--accent-pink);">
      <h4 style="color:#fff; margin-bottom:4px;">${escapeHtml(n.name)}</h4>
      <div style="font-size:12px; color:var(--accent-violet); margin-bottom:6px;">📍 ${escapeHtml(n.location)} | ${escapeHtml(n.focus_area)}</div>
      ${n.contact_phone ? `<div style="font-size:13px; color:#fff;">📞 <strong>${escapeHtml(n.contact_phone)}</strong></div>` : ""}
      ${n.contact_email ? `<div style="font-size:12px; color:var(--text-muted);">✉️ ${escapeHtml(n.contact_email)}</div>` : ""}
    </div>
  `
    )
    .join("");

  content.innerHTML = `
    <div style="text-align:center; margin-bottom:24px;">
      <div style="font-size:40px; margin-bottom:8px;">✅</div>
      <h3 style="font-size:22px; color:#fff;">Incident Logged Successfully</h3>
      <div style="color:var(--text-muted); font-size:13px;">Reference ID: #${incident.id} | Status: <span class="badge badge-pending">${incident.status}</span></div>
    </div>

    <h4 style="color:var(--accent-cyan); margin-bottom:12px; font-size:16px;">🏛️ Matched Indian Government Schemes (${incident.matched_schemes.length})</h4>
    ${schemesHtml || "<p style='color:var(--text-muted); font-size:13px;'>No specific scheme matched.</p>"}

    <h4 style="color:var(--accent-pink); margin:20px 0 12px; font-size:16px;">🤝 Verified NGO Crisis Partners (${incident.matched_ngos.length})</h4>
    ${ngosHtml || "<p style='color:var(--text-muted); font-size:13px;'>No specific NGO matched.</p>"}
  `;

  modal.classList.add("active");
}

// Close incident modal
document.getElementById("close-inc-modal")?.addEventListener("click", () => {
  document.getElementById("incident-result-modal").classList.remove("active");
});

// ==========================================
// AI Legal Rights Awareness Module
// ==========================================
function setupAwarenessUI() {
  const queryInput = document.getElementById("awareness-query-input");
  const queryBtn = document.getElementById("awareness-query-btn");
  const resultCard = document.getElementById("awareness-result-card");

  async function performQuery(text) {
    if (!text.trim()) return;
    queryBtn.disabled = true;
    queryBtn.innerText = "Analyzing Rights...";

    try {
      const res = await fetch(`${API_BASE}/awareness/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
      });

      if (!res.ok) throw new Error("Failed to query awareness module");
      const data = await res.json();

      resultCard.style.display = "block";
      resultCard.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px;">
          <div>
            <span class="decision-badge">⚖️ ${escapeHtml(data.matched_topic)}</span>
            <h3 style="font-size:20px; color:#fff; margin-top:6px;">${escapeHtml(data.applicable_law)}</h3>
          </div>
        </div>

        <div style="margin-bottom:16px; font-size:14.5px; color:#cbd5e1; line-height:1.7;">
          ${escapeHtml(data.explanation)}
        </div>

        <div style="background:rgba(99,102,241,0.1); border-left:3px solid var(--primary); padding:14px; border-radius:6px; margin-bottom:18px;">
          <h4 style="font-size:14px; color:var(--accent-cyan); margin-bottom:8px;">📜 Statutory Sections & Constitutional Provisions:</h4>
          <ul style="padding-left:20px; font-size:13.5px; color:#e2e8f0;">
            ${data.sections_cited.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
          </ul>
        </div>

        <div style="margin-bottom:18px;">
          <h4 style="font-size:14px; color:var(--accent-emerald); margin-bottom:8px;">⚡ Actionable Steps to Take:</h4>
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${data.actionable_steps
              .map(
                (step) => `
              <div style="background:rgba(255,255,255,0.03); padding:10px 14px; border-radius:6px; font-size:13.5px; color:#cbd5e1;">
                ${escapeHtml(step)}
              </div>
            `
              )
              .join("")}
          </div>
        </div>

        <div style="border-top:1px solid var(--border-subtle); padding-top:14px; display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; font-size:13px;">
          <span style="color:var(--accent-rose); font-weight:600;">📞 ${escapeHtml(data.legal_aid_contact)}</span>
          <div style="display:flex; gap:10px;">
            ${data.official_portals
              .map(
                (p) => `
              <a href="${p}" target="_blank" style="color:var(--accent-cyan); text-decoration:underline;">${p.replace("https://", "").split("/")[0]} ↗</a>
            `
              )
              .join("")}
          </div>
        </div>
      `;
      resultCard.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      queryBtn.disabled = false;
      queryBtn.innerText = "Consult Legal Rights";
    }
  }

  if (queryBtn) {
    queryBtn.addEventListener("click", () => performQuery(queryInput.value));
  }
  if (queryInput) {
    queryInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") performQuery(queryInput.value);
    });
  }

  // Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.innerText;
      performQuery(chip.innerText);
    });
  });
}

// ==========================================
// AI Health Assistant Decision Tree Wizard
// ==========================================
async function setupHealthAssistantUI() {
  const wizardContainer = document.getElementById("health-wizard-container");
  if (!wizardContainer) return;

  await loadHealthNode("root");
}

async function loadHealthNode(nodeId) {
  const container = document.getElementById("health-wizard-container");
  container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted);">Loading health guidance...</div>`;

  try {
    const res = await fetch(`${API_BASE}/health-assistant/nodes/${nodeId}`);
    if (!res.ok) throw new Error("Failed to load node");
    const data = await res.json();
    renderHealthNode(data.node, data.disclaimer);
  } catch (e) {
    container.innerHTML = `<div style="color:var(--accent-rose); padding:20px;">Error: ${e.message}</div>`;
  }
}

async function traverseHealthNode(currentNodeId, optionId) {
  const container = document.getElementById("health-wizard-container");
  try {
    const res = await fetch(`${API_BASE}/health-assistant/traverse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_node_id: currentNodeId, option_id: optionId }),
    });
    if (!res.ok) throw new Error("Traversal failed");
    const data = await res.json();
    renderHealthNode(data.node, data.disclaimer);
  } catch (e) {
    alert("Error navigating tree: " + e.message);
  }
}

function renderHealthNode(node, disclaimer) {
  const container = document.getElementById("health-wizard-container");

  let warningsHtml = "";
  if (node.warnings && node.warnings.length > 0) {
    warningsHtml = `
      <div class="alert-warning-box">
        <strong>⚠️ Medical Safety Alert:</strong>
        <ul style="padding-left:18px; margin-top:6px;">
          ${node.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  let actionsHtml = "";
  if (node.recommended_actions && node.recommended_actions.length > 0) {
    actionsHtml = `
      <div class="checklist-box">
        <strong>📋 Clinical Protocol & Next Steps:</strong>
        <ul style="padding-left:18px; margin-top:6px;">
          ${node.recommended_actions.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  let contactsHtml = "";
  if (node.helpline_contacts && node.helpline_contacts.length > 0) {
    contactsHtml = `
      <div style="background:rgba(255,255,255,0.04); padding:14px 18px; border-radius:10px; margin-bottom:20px;">
        <div style="font-size:12px; color:var(--accent-pink); font-weight:700; text-transform:uppercase; margin-bottom:6px;">🚨 Direct Support Lines:</div>
        <div style="display:flex; flex-wrap:wrap; gap:12px;">
          ${node.helpline_contacts
            .map((c) => `<span style="font-size:13px; font-weight:600; color:#fff;">📞 ${escapeHtml(c)}</span>`)
            .join("")}
        </div>
      </div>
    `;
  }

  let optionsHtml = "";
  if (node.options && node.options.length > 0) {
    optionsHtml = `
      <div class="decision-options">
        ${node.options
          .map(
            (opt) => `
          <button class="opt-btn" onclick="traverseHealthNode('${node.node_id}', '${opt.option_id}')">
            <span>${escapeHtml(opt.text)}</span>
            <span style="color:var(--accent-cyan);">→</span>
          </button>
        `
          )
          .join("")}
      </div>
    `;
  }

  container.innerHTML = `
    <div class="decision-card">
      <span class="decision-badge">${escapeHtml(node.category)}</span>
      <h2 class="decision-title">${escapeHtml(node.title)}</h2>
      <p class="decision-message">${escapeHtml(node.message)}</p>

      ${warningsHtml}
      ${actionsHtml}
      ${contactsHtml}
      ${optionsHtml}

      <div class="disclaimer-banner">
        🔒 <strong>Confidential & Safe:</strong> ${escapeHtml(disclaimer)}
      </div>
    </div>
  `;
}

// ==========================================
// Incidents / Case Management (for Verifiers)
// ==========================================
async function loadIncidents() {
  const container = document.getElementById("cases-container");
  if (!container) return;

  if (!currentAuthToken) {
    container.innerHTML = `
      <div style="text-align:center; padding:40px;">
        <p style="color:var(--text-muted); margin-bottom:16px;">Log in as an NGO Verifier or Admin to view and manage discrimination cases.</p>
        <button class="btn btn-primary" onclick="document.getElementById('login-modal').classList.add('active')">Log In as Verifier</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted);">Loading filed incidents...</div>`;

  try {
    const res = await fetch(`${API_BASE}/incidents/`, {
      headers: { Authorization: `Bearer ${currentAuthToken}` },
    });
    if (!res.ok) throw new Error("Could not load incidents");
    const incidents = await res.json();

    if (incidents.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted);">No reported incidents found.</div>`;
      return;
    }

    container.innerHTML = incidents
      .map(
        (inc) => `
      <div class="listing-card" style="margin-bottom:16px;">
        <div class="card-top">
          <span class="category-tag">🚨 ${inc.incident_type.toUpperCase()} (${inc.urgency_level.toUpperCase()})</span>
          <span class="badge badge-pending">${inc.status}</span>
        </div>
        <h3 class="card-title">${escapeHtml(inc.title)}</h3>
        <div style="font-size:13px; color:var(--text-muted); margin-bottom:8px;">
          📍 ${escapeHtml(inc.location_city)}, ${escapeHtml(inc.location_state)} | 
          ${inc.is_anonymous ? "🕵️ Anonymous" : "👤 Authenticated"} |
          ${inc.incident_date ? `📅 ${inc.incident_date}` : ""}
        </div>
        <p class="card-desc">${escapeHtml(inc.description)}</p>
        ${inc.perpetrator_details ? `<div style="font-size:12.5px; color:#fecdd3; margin-bottom:10px;"><strong>Alleged Entity:</strong> ${escapeHtml(inc.perpetrator_details)}</div>` : ""}
        ${inc.case_notes ? `<div style="font-size:12.5px; color:var(--accent-cyan); margin-bottom:10px;"><strong>Case Notes:</strong> ${escapeHtml(inc.case_notes)}</div>` : ""}
        
        <div class="card-footer" style="padding-top:14px;">
          <span>Assigned: <strong>${escapeHtml(inc.assigned_ngo || "Pending Assignment")}</strong></span>
          ${
            currentUser?.role === "verifier" || currentUser?.role === "admin"
              ? `
            <div style="display:flex; gap:8px;">
              <button class="btn btn-secondary" style="padding:4px 10px; font-size:12px;" onclick="updateIncidentStatusPrompt(${inc.id}, 'escalated_to_ngo')">Escalate to NGO</button>
              <button class="btn btn-primary" style="padding:4px 10px; font-size:12px;" onclick="updateIncidentStatusPrompt(${inc.id}, 'resolved')">Mark Resolved</button>
            </div>
          `
              : ""
          }
        </div>
      </div>
    `
      )
      .join("");
  } catch (e) {
    container.innerHTML = `<div style="color:var(--accent-rose); padding:20px;">Error: ${e.message}</div>`;
  }
}

async function updateIncidentStatusPrompt(incidentId, targetStatus) {
  const notes = prompt("Enter case notes for this status update:", "Escalated for legal notice and welfare linkage.");
  if (notes === null) return;

  try {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentAuthToken}`,
      },
      body: JSON.stringify({
        status: targetStatus,
        case_notes: notes,
        assigned_ngo: "The Humsafar Trust Legal Cell",
      }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    alert("Incident status updated successfully!");
    loadIncidents();
  } catch (err) {
    alert("Update failed: " + err.message);
  }
}

// Escape HTML utility
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
