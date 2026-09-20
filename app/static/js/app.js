/**
 * Beyond Identity — Interactive Frontend Logic
 * Connects to FastAPI endpoints: /auth, /listings, /incidents, /awareness, /health-assistant
 */

const API_BASE = ""; // Relative to current host
let currentAuthToken = localStorage.getItem("bi_token") || "";
let currentUser = JSON.parse(localStorage.getItem("bi_user") || "null");

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupTabs();
  setupAuthUI();
  loadStats();
  loadListings();
  setupIncidentForm();
  setupAwarenessUI();
  setupHealthAssistantUI();
});

// ==========================================
// Theme Management (Day / Night / System)
// ==========================================
function initTheme() {
  const savedTheme = localStorage.getItem("bi_theme") || "system";
  applyTheme(savedTheme);

  document.querySelectorAll(".theme-switch-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const val = btn.getAttribute("data-theme-val");
      localStorage.setItem("bi_theme", val);
      applyTheme(val);
      showToast(`Theme: ${val === 'light' ? '☀️ Day' : val === 'dark' ? '🌙 Night' : '💻 System Auto'}`, "info");
    });
  });

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    const currentTheme = localStorage.getItem("bi_theme") || "system";
    if (currentTheme === "system") {
      document.documentElement.setAttribute("data-theme", e.matches ? "dark" : "light");
    }
  });
}

function applyTheme(theme) {
  let active = theme;
  if (theme === "system") {
    active = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.documentElement.setAttribute("data-theme", active);

  document.querySelectorAll(".theme-switch-btn").forEach((btn) => {
    if (btn.getAttribute("data-theme-val") === theme) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

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
// Toast Notification Helper
// ==========================================
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "✕" : "ℹ";
  toast.innerHTML = `<span style="font-weight: 700; margin-right: 6px;">${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3800);
}

// ==========================================
// Authentication & Demo User Switcher
// ==========================================
function setupAuthUI() {
  const loginModal = document.getElementById("login-modal");
  const closeLoginBtn = document.getElementById("close-login-btn");
  const modalTabSignin = document.getElementById("modal-tab-signin-btn");
  const modalTabRegister = document.getElementById("modal-tab-register-btn");
  const modalLoginForm = document.getElementById("modal-login-form");
  const modalRegisterForm = document.getElementById("modal-register-form");
  const modalAuthTitle = document.getElementById("modal-auth-title");
  const modalAuthSubtitle = document.getElementById("modal-auth-subtitle");
  const modalAuthAlert = document.getElementById("modal-auth-alert");

  if (closeLoginBtn) {
    closeLoginBtn.addEventListener("click", () => loginModal.classList.remove("active"));
  }

  // Close modal when clicking on overlay background
  if (loginModal) {
    loginModal.addEventListener("click", (e) => {
      if (e.target === loginModal) loginModal.classList.remove("active");
    });
  }

  // Modal Tab Switching
  function switchModalTab(tab) {
    if (modalAuthAlert) modalAuthAlert.style.display = "none";
    if (tab === "register") {
      modalTabRegister.classList.add("active");
      modalTabSignin.classList.remove("active");
      modalRegisterForm.style.display = "block";
      modalLoginForm.style.display = "none";
      if (modalAuthTitle) modalAuthTitle.innerText = "Join Beyond Identity";
      if (modalAuthSubtitle) modalAuthSubtitle.innerText = "Create an account for community or partner access";
    } else {
      modalTabSignin.classList.add("active");
      modalTabRegister.classList.remove("active");
      modalLoginForm.style.display = "block";
      modalRegisterForm.style.display = "none";
      if (modalAuthTitle) modalAuthTitle.innerText = "Welcome to Beyond Identity";
      if (modalAuthSubtitle) modalAuthSubtitle.innerText = "Sign in to your account or use 1-click access";
    }
  }

  if (modalTabSignin) modalTabSignin.addEventListener("click", () => switchModalTab("signin"));
  if (modalTabRegister) modalTabRegister.addEventListener("click", () => switchModalTab("register"));

  // Password Toggles in Modal
  const modalPassToggle = document.getElementById("modal-pass-toggle");
  const modalLoginPass = document.getElementById("modal-login-password");
  if (modalPassToggle && modalLoginPass) {
    modalPassToggle.addEventListener("click", () => {
      modalLoginPass.type = modalLoginPass.type === "password" ? "text" : "password";
      modalPassToggle.innerText = modalLoginPass.type === "password" ? "👁️" : "🙈";
    });
  }

  const modalRegPassToggle = document.getElementById("modal-reg-pass-toggle");
  const modalRegPass = document.getElementById("modal-reg-password");
  if (modalRegPassToggle && modalRegPass) {
    modalRegPassToggle.addEventListener("click", () => {
      modalRegPass.type = modalRegPass.type === "password" ? "text" : "password";
      modalRegPassToggle.innerText = modalRegPass.type === "password" ? "👁️" : "🙈";
    });
  }

  // Handle Modal Sign In Submission
  if (modalLoginForm) {
    modalLoginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("modal-login-email").value.trim();
      const password = document.getElementById("modal-login-password").value;
      const submitBtn = document.getElementById("modal-login-submit-btn");

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="btn-spinner"></span> Authenticating...';

      const success = await executeLogin(email, password, false);
      submitBtn.disabled = false;
      submitBtn.innerHTML = "Sign In";

      if (success) {
        loginModal.classList.remove("active");
      }
    });
  }

  // Handle Modal Register Submission
  if (modalRegisterForm) {
    modalRegisterForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("modal-reg-name").value.trim();
      const email = document.getElementById("modal-reg-email").value.trim();
      const password = document.getElementById("modal-reg-password").value;
      const roleEl = document.querySelector('input[name="modal-reg-role"]:checked');
      const role = roleEl ? roleEl.value : "user";
      const submitBtn = document.getElementById("modal-reg-submit-btn");

      if (password.length < 6) {
        showModalAlert("Password must be at least 6 characters long.", true);
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="btn-spinner"></span> Creating Account...';

      try {
        const res = await fetch(`${API_BASE}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password, role }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Registration failed. Email may already be in use.");
        }

        const newUser = await res.json();
        showToast(`Account created for ${newUser.name}!`, "success");
        await executeLogin(email, password, false);
        loginModal.classList.remove("active");
      } catch (err) {
        showModalAlert(err.message, true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "Create Account & Sign In";
      }
    });
  }

  function showModalAlert(msg, isError = true) {
    if (!modalAuthAlert) return;
    modalAuthAlert.style.display = "block";
    modalAuthAlert.style.background = isError ? "rgba(244, 63, 94, 0.15)" : "rgba(16, 185, 129, 0.15)";
    modalAuthAlert.style.border = isError ? "1px solid rgba(244, 63, 94, 0.4)" : "1px solid rgba(16, 185, 129, 0.4)";
    modalAuthAlert.style.color = isError ? "#fecdd3" : "#a7f3d0";
    modalAuthAlert.innerText = msg;
  }

  // Wire up guest landing and modal trigger buttons
  document.querySelectorAll(".guest-open-login-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchModalTab("signin");
      loginModal.classList.add("active");
    });
  });

  document.querySelectorAll(".guest-open-signup-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchModalTab("register");
      loginModal.classList.add("active");
    });
  });

  // Quick 1-Click Demo Logins across landing & modal
  document.querySelectorAll(".demo-login-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const email = btn.getAttribute("data-email");
      const password = btn.getAttribute("data-password");
      await executeLogin(email, password, false);
      loginModal.classList.remove("active");
    });
  });

  renderUserStatus();
}

async function executeLogin(email, password, notify = true) {
  try {
    const res = await fetch(`${API_BASE}/auth/login-json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Incorrect email or password");
    }

    const data = await res.json();
    currentAuthToken = data.access_token;
    localStorage.setItem("bi_token", currentAuthToken);

    if (data.user) {
      currentUser = data.user;
    } else {
      const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${currentAuthToken}` },
      });
      if (meRes.ok) currentUser = await meRes.json();
    }
    localStorage.setItem("bi_user", JSON.stringify(currentUser));

    renderUserStatus();
    showToast(`Welcome, ${currentUser?.name}! Signed in as ${currentUser?.role.toUpperCase()}.`, "success");
    loadIncidents();
    loadListings();
    return true;
  } catch (err) {
    showToast("Sign in failed: " + err.message, "error");
    const modalAlert = document.getElementById("modal-auth-alert");
    if (modalAlert) {
      modalAlert.style.display = "block";
      modalAlert.className = "alert-box alert-error";
      modalAlert.removeAttribute("style");
      modalAlert.style.display = "block";
      modalAlert.innerText = err.message;
    }
    return false;
  }
}

function renderUserStatus() {
  const guestLanding = document.getElementById("guest-landing-view");
  const authPortal = document.getElementById("authenticated-portal-view");
  const guestHeroCta = document.getElementById("guest-hero-cta");
  const guestDemoStrip = document.getElementById("guest-demo-strip");
  const authTabsNav = document.getElementById("authenticated-tabs-nav");
  const container = document.getElementById("auth-actions-container");

  if (currentUser && currentAuthToken) {
    // ==========================================
    // AUTHENTICATED STATE: Unlock Full App
    // ==========================================
    if (guestLanding) guestLanding.style.display = "none";
    if (guestHeroCta) guestHeroCta.style.display = "none";
    if (guestDemoStrip) guestDemoStrip.style.display = "none";
    if (authTabsNav) authTabsNav.style.display = "flex";
    if (authPortal) authPortal.style.display = "block";

    // Update Welcome Banner
    const bannerGreeting = document.getElementById("member-banner-greeting");
    const bannerSub = document.getElementById("member-banner-sub");
    const bannerRole = document.getElementById("member-banner-role-badge");
    const bannerAvatar = document.getElementById("member-banner-avatar");

    const roleUpper = (currentUser.role || "user").toUpperCase();
    const roleClass = currentUser.role === "verifier" ? "role-verifier" : currentUser.role === "admin" ? "role-admin" : "";
    const initials = currentUser.name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

    if (bannerGreeting) bannerGreeting.innerText = `Welcome back, ${currentUser.name}!`;
    if (bannerSub) {
      bannerSub.innerText = currentUser.role === "verifier"
        ? "🛡️ NGO Partner Moderation Console: Access verified listings and confidential incident cases."
        : currentUser.role === "admin"
        ? "⚡ System Administrator Access: Full platform, moderation, and redressal management."
        : "👤 Community Seeker Portal: Full access to verified opportunities, confidential reporting, AI legal rights & health triage.";
    }
    if (bannerRole) {
      bannerRole.innerText = roleUpper;
      bannerRole.className = `user-role-badge ${roleClass}`;
    }
    if (bannerAvatar) {
      bannerAvatar.innerText = initials;
      bannerAvatar.className = `user-avatar ${roleClass}`;
    }

    // Top Navbar Profile Chip
    if (container) {
      container.innerHTML = `
        <div class="nav-user-chip">
          <div class="user-avatar ${roleClass}">${initials}</div>
          <div class="user-info-text">
            <span class="user-display-name">${currentUser.name}</span>
            <span class="user-role-badge ${roleClass}">${roleUpper}</span>
          </div>
        </div>
        <button class="btn btn-outline-danger" id="logout-btn" style="padding: 6px 12px; font-size: 12.5px;">Sign Out</button>
      `;

      document.getElementById("logout-btn").addEventListener("click", () => {
        currentAuthToken = "";
        currentUser = null;
        localStorage.removeItem("bi_token");
        localStorage.removeItem("bi_user");
        renderUserStatus();
        showToast("Signed out successfully.", "info");
      });
    }

    // Show Verifier tab if verifier or admin
    const verifierTab = document.getElementById("tab-btn-cases");
    if (verifierTab) {
      verifierTab.style.display = (currentUser.role === "verifier" || currentUser.role === "admin") ? "flex" : "none";
    }
  } else {
    // ==========================================
    // GUEST STATE: Show Attractive Landing Page
    // ==========================================
    if (guestLanding) guestLanding.style.display = "block";
    if (guestHeroCta) guestHeroCta.style.display = "flex";
    if (guestDemoStrip) guestDemoStrip.style.display = "block";
    if (authTabsNav) authTabsNav.style.display = "none";
    if (authPortal) authPortal.style.display = "none";

    if (container) {
      container.innerHTML = `
        <button class="btn btn-primary" id="open-login-btn" style="padding: 8px 16px; font-size: 13px;">Sign In / Register</button>
        <a href="/login" class="btn btn-secondary" style="padding: 8px 14px; font-size: 13px;">Auth Portal →</a>
      `;

      document.getElementById("open-login-btn").addEventListener("click", () => {
        const loginModal = document.getElementById("login-modal");
        const modalTabSignin = document.getElementById("modal-tab-signin-btn");
        const modalTabRegister = document.getElementById("modal-tab-register-btn");
        const modalLoginForm = document.getElementById("modal-login-form");
        const modalRegisterForm = document.getElementById("modal-register-form");
        const modalAuthAlert = document.getElementById("modal-auth-alert");

        if (modalAuthAlert) modalAuthAlert.style.display = "none";
        if (modalTabSignin) modalTabSignin.classList.add("active");
        if (modalTabRegister) modalTabRegister.classList.remove("active");
        if (modalLoginForm) modalLoginForm.style.display = "block";
        if (modalRegisterForm) modalRegisterForm.style.display = "none";
        if (loginModal) loginModal.classList.add("active");
      });
    }
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
    <div class="incident-scheme-card">
      <h4 class="incident-scheme-title">${escapeHtml(s.name)}</h4>
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
    <div class="incident-ngo-card">
      <h4 class="incident-ngo-title">${escapeHtml(n.name)}</h4>
      <div style="font-size:12px; color:var(--accent-violet); margin-bottom:6px;">📍 ${escapeHtml(n.location)} | ${escapeHtml(n.focus_area)}</div>
      ${n.contact_phone ? `<div class="incident-ngo-phone">📞 <strong>${escapeHtml(n.contact_phone)}</strong></div>` : ""}
      ${n.contact_email ? `<div style="font-size:12px; color:var(--text-muted);">✉️ ${escapeHtml(n.contact_email)}</div>` : ""}
    </div>
  `
    )
    .join("");

  content.innerHTML = `
    <div style="text-align:center; margin-bottom:24px;">
      <div style="font-size:40px; margin-bottom:8px;">✅</div>
      <h3 class="incident-result-title">Incident Logged Successfully</h3>
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
            <h3 class="awareness-law-title">${escapeHtml(data.applicable_law)}</h3>
          </div>
        </div>

        <div class="awareness-explanation">
          ${escapeHtml(data.explanation)}
        </div>

        <div class="awareness-sections-box">
          <h4 class="awareness-sections-title">📜 Statutory Sections & Constitutional Provisions:</h4>
          <ul class="awareness-sections-list">
            ${data.sections_cited.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
          </ul>
        </div>

        <div style="margin-bottom:18px;">
          <h4 class="awareness-steps-title">⚡ Actionable Steps to Take:</h4>
          <div style="display:flex; flex-direction:column; gap:8px;">
            ${data.actionable_steps
              .map(
                (step) => `
              <div class="awareness-step-item">
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
      <div class="health-helplines-box">
        <div style="font-size:12px; color:var(--accent-pink); font-weight:700; text-transform:uppercase; margin-bottom:6px;">🚨 Direct Support Lines:</div>
        <div style="display:flex; flex-wrap:wrap; gap:12px;">
          ${node.helpline_contacts
            .map((c) => `<span class="health-helpline-item">📞 ${escapeHtml(c)}</span>`)
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
        ${inc.perpetrator_details ? `<div class="case-perpetrator"><strong>Alleged Entity:</strong> ${escapeHtml(inc.perpetrator_details)}</div>` : ""}
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
