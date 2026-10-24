/**
 * Beyond Identity — Interactive Frontend Logic
 * Connects to FastAPI endpoints: /auth, /listings, /incidents, /awareness, /health-assistant
 */

const API_BASE = ""; // Relative to current host
let currentAuthToken = localStorage.getItem("bi_token") || "";
let currentUser = JSON.parse(localStorage.getItem("bi_user") || "null");

// Core Sanitization & Markdown Helpers
function escapeHtml(str) {
  if (typeof str !== "string") return str || "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function parseMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  // Headers
  html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 8px 0 4px 0; font-size: 14.5px; color: var(--accent-cyan);">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 10px 0 6px 0; font-size: 16px; color: var(--text-main);">$1</h3>');
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Links
  html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--accent-cyan); text-decoration: underline;">$1</a>');
  // Bullet points
  html = html.replace(/^\s*[-•]\s+(.*$)/gim, '<li style="margin-left: 18px; margin-bottom: 4px;">$1</li>');
  // Convert newlines to breaks
  html = html.replace(/\n/g, '<br />');
  return html;
}

// ============================================================================
// SWEET & SOOTHING FEMALE VOICE ENGINE (Web Speech API)
// Rate ~0.95 (soft & slow), Pitch ~1.1 (sweet & melodic female voice)
// Fallback to default voice gracefully if no female voice is detected
// ============================================================================
const SweetVoiceEngine = {
  availableVoices: [],
  currentProfile: localStorage.getItem("bi_voice_profile") || "sweet",
  activeUtterance: null,
  listeners: [],

  // Strict male disqualification terms
  maleKeywords: [
    "ravi", "david", "mark", "george", "guy", "richard", "james", "stefan",
    "prabhat", "hemant", "sean", "eric", "paul", "martin", "christopher",
    "ryan", "brian", "daniel", "oliver", "alex", "fred", "male", "man", "boy",
    "prakash", "tarun", "ajay", "karan", "vikram", "amit", "rahul", "arun", "stephen"
  ],

  // Priority female voices
  hindiFemaleKeywords: ["swara", "aditi", "kalpana", "google हिन्दी", "hindi female"],
  indianEnFemaleKeywords: ["neerja", "heera", "veena"],
  ukEnFemaleKeywords: ["google uk english female", "sonia", "hazel", "libby"],
  usEnFemaleKeywords: ["microsoft zira", "zira", "jenny", "aria", "samantha", "victoria", "karen", "google us english"],

  init() {
    if (!("speechSynthesis" in window)) return;
    this.loadVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = () => {
        this.loadVoices();
        this.notifyListeners();
      };
    }
  },

  onVoicesLoaded(callback) {
    if (typeof callback === "function") {
      this.listeners.push(callback);
      if (this.availableVoices && this.availableVoices.length > 0) {
        callback(this.availableVoices);
      }
    }
  },

  notifyListeners() {
    this.listeners.forEach(cb => {
      try { cb(this.availableVoices); } catch (e) { console.warn(e); }
    });
  },

  loadVoices() {
    if (!("speechSynthesis" in window)) return [];
    this.availableVoices = window.speechSynthesis.getVoices() || [];
    return this.availableVoices;
  },

  isMaleVoice(v) {
    if (!v || !v.name) return false;
    const lower = (v.name + " " + (v.voiceURI || "")).toLowerCase();
    return this.maleKeywords.some(keyword => lower.includes(keyword));
  },

  getSweetFemaleVoice(profile) {
    if (!this.availableVoices || this.availableVoices.length === 0) {
      this.loadVoices();
    }
    const voices = this.availableVoices;
    if (!voices || voices.length === 0) return null;

    const nonMaleVoices = voices.filter(v => !this.isMaleVoice(v));

    // Priority 1: Hindi / Hinglish female voice (hi-IN)
    const hiVoice = nonMaleVoices.find(v => {
      const l = (v.lang || "").toLowerCase();
      const n = (v.name || "").toLowerCase();
      const isHi = l === "hi-in" || l.replace("_", "-") === "hi-in" || l.startsWith("hi");
      const hasFemaleName = this.hindiFemaleKeywords.some(k => n.includes(k)) || n.includes("female");
      return isHi && (hasFemaleName || !this.isMaleVoice(v));
    });
    if (profile === "hi_female" && hiVoice) return hiVoice;

    // Priority 2: Indian English Female (Neerja, Heera, Veena)
    for (const name of this.indianEnFemaleKeywords) {
      const match = nonMaleVoices.find(v => v.name.toLowerCase().includes(name));
      if (match) return match;
    }
    const enInFemale = nonMaleVoices.find(v => {
      const l = (v.lang || "").toLowerCase();
      return (l === "en-in" || l.replace("_", "-") === "en-in") && !this.isMaleVoice(v);
    });
    if (profile === "in_female" && (enInFemale || hiVoice)) return enInFemale || hiVoice;

    // Priority 3: Google UK English Female
    for (const name of this.ukEnFemaleKeywords) {
      const match = nonMaleVoices.find(v => v.name.toLowerCase().includes(name));
      if (match) return match;
    }

    // Priority 4: Microsoft Zira & US Female (Jenny, Aria, Samantha)
    for (const name of this.usEnFemaleKeywords) {
      const match = nonMaleVoices.find(v => v.name.toLowerCase().includes(name));
      if (match) return match;
    }

    // If hiVoice exists, it's also a great fit for Indian users
    if (hiVoice) return hiVoice;

    // Priority 5: Any voice explicitly containing "female" or "woman"
    const anyFemale = nonMaleVoices.find(v => {
      const n = (v.name || "").toLowerCase();
      return n.includes("female") || n.includes("woman");
    });
    if (anyFemale) return anyFemale;

    // Priority 6: Any non-male English voice
    const anyNonMaleEn = nonMaleVoices.find(v => (v.lang || "").toLowerCase().startsWith("en"));
    if (anyNonMaleEn) return anyNonMaleEn;

    // Fallback: Return first non-male voice or default voice without crashing
    return nonMaleVoices[0] || voices[0] || null;
  },

  cleanForSpeech(text) {
    if (!text) return "";
    let clean = text
      .replace(/### (.*?)\n/g, "$1. ")
      .replace(/#### (.*?)\n/g, "$1. ")
      .replace(/[1-9]️⃣/g, "")
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/\[(.*?)\]\((.*?)\)/g, "$1")
      .replace(/₹\s*([0-9,]+)\s*(?:Lakh|L|lakh)?/gi, "$1 lakh rupees")
      .replace(/\bTG\b/g, "Transgender")
      .replace(/\bHRT\b/g, "Hormone Replacement Therapy")
      .replace(/\bNALSA\b/g, "Nalsa")
      .replace(/\bPM-JAY\b/g, "P M Jay")
      .replace(/\bNGOs\b/g, "N G Os")
      .replace(/\bNGO\b/g, "N G O")
      .replace(/[`*#_>•\-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    const sentences = clean.split(". ");
    if (sentences.length > 5) {
      clean = sentences.slice(0, 5).join(". ") + ".";
    }
    return clean;
  },

  speak(text, options = {}) {
    if (!("speechSynthesis" in window)) return;
    this.stop();
    if (!text) return;

    const speechScript = this.cleanForSpeech(text);
    if (!speechScript) return;

    const utterance = new SpeechSynthesisUtterance(speechScript);
    // User requested: voice soft aur slow (rate ~0.95, pitch ~1.1)
    utterance.rate = 0.95;
    utterance.pitch = 1.1;
    utterance.volume = 1.0;

    const bestVoice = this.getSweetFemaleVoice(options.profile || this.currentProfile);
    if (bestVoice) {
      utterance.voice = bestVoice;
      utterance.lang = bestVoice.lang || "en-IN";
    } else {
      utterance.lang = "en-IN";
    }

    window.__activeSpeechUtterance = utterance;
    this.activeUtterance = utterance;

    if (options.onstart) utterance.onstart = options.onstart;
    
    const cleanup = () => {
      window.__activeSpeechUtterance = null;
      this.activeUtterance = null;
    };

    utterance.onend = (e) => {
      cleanup();
      if (options.onend) options.onend(e);
    };

    utterance.onerror = (e) => {
      cleanup();
      if (options.onerror) options.onerror(e);
    };

    try {
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("Speech synthesis error fallback:", err);
      cleanup();
    }
    return utterance;
  },

  stop() {
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        console.warn(e);
      }
    }
    window.__activeSpeechUtterance = null;
    this.activeUtterance = null;
  },

  testVoice(customText) {
    const text =
      customText ||
      "Namaste! I am your Beyond Identity assistant. I speak with a soft, sweet and soothing voice to support you with care and respect.";
    return this.speak(text);
  },

  setProfile(profile) {
    this.currentProfile = profile;
    localStorage.setItem("bi_voice_profile", profile);
  }
};
window.SweetVoiceEngine = SweetVoiceEngine;

document.addEventListener("DOMContentLoaded", () => {
  SweetVoiceEngine.init();
  initTheme();
  setupTabs();
  setupAuthUI();
  loadStats();
  loadListings();
  setupIncidentForm();
  setupAwarenessUI();
  setupHealthAssistantUI();
  initChatbox();
  initTabChatbox();
  initVideoInterviews();

  // Initialize guest vs member presentation
  renderUserStatus();
  initGuestDemo();

  const params = new URLSearchParams(window.location.search);
  const currentPath = window.location.pathname.toLowerCase();
  const currentHash = window.location.hash.toLowerCase();
  const requestedTab = params.get("tab")?.toLowerCase();

  const isCasesRequested = (
    requestedTab === "tab-cases" ||
    requestedTab === "cases" ||
    currentHash === "#tab-cases" ||
    currentPath.includes("/cases") ||
    currentPath.includes("/triage")
  );

  const isVideosRequested = (
    requestedTab === "tab-videos" ||
    requestedTab === "videos" ||
    currentHash === "#tab-videos" ||
    currentPath.includes("/videos")
  );

  // Authenticated users or direct case triage/video requests navigate straight to target
  if (currentUser && currentAuthToken) {
    const target = isCasesRequested ? "tab-cases" : (isVideosRequested ? "tab-videos" : ((requestedTab && document.getElementById(requestedTab)) ? requestedTab : "tab-chat"));
    switchToTab(target);
  } else if (isCasesRequested) {
    switchToTab("tab-cases");
  } else if (isVideosRequested) {
    switchToTab("tab-videos");
  } else {
    // Unauthenticated guest: keep single Home as default view
    document.body.classList.remove("tab-chat-active", "portal-view-active");
    const guestHero = document.getElementById("landing-hero-section");
    if (guestHero) guestHero.style.display = "flex";
    const authPortal = document.getElementById("authenticated-portal-view");
    if (authPortal) authPortal.style.display = "none";
    const authTabsNav = document.getElementById("authenticated-tabs-nav");
    if (authTabsNav) authTabsNav.style.display = "none";
    const navHomeLink = document.querySelector('.nav-links-menu a[href="#landing-hero-section"]');
    if (navHomeLink) navHomeLink.classList.add("active");
  }

  const isAuth = !!(currentAuthToken && currentUser);
  const isPostLoginRedirect = params.get("talk") === "1" || params.get("login") === "success";

  if (isAuth && isPostLoginRedirect) {
    const netBanner = document.getElementById("post-login-network-banner");
    if (netBanner) netBanner.style.display = "flex";
    window.history.replaceState({}, document.title, window.location.pathname);
    setTimeout(() => {
      if (typeof window.triggerPostLoginChatGreeting === "function") {
        window.triggerPostLoginChatGreeting(currentUser);
      } else if (typeof window.triggerPostLoginAIChatGreeting === "function") {
        window.triggerPostLoginAIChatGreeting(currentUser);
      }
    }, 550);
  }
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
function switchToTab(targetId) {
  // All visitors (including unauthenticated guests on phones and laptops) can view the Case Triage Desk and Video Interviews
  const isGuest = !currentUser || !currentAuthToken;
  if (isGuest && targetId !== "tab-cases" && targetId !== "tab-videos") {
    showToast("Please sign in to access portal features.", "info");
    setTimeout(() => {
      window.location.href = "/login";
    }, 350);
    return;
  }

  const guestHero = document.getElementById("landing-hero-section");
  const guestLanding = document.getElementById("guest-landing-view");
  const authPortal = document.getElementById("authenticated-portal-view");
  const authTabsNav = document.getElementById("authenticated-tabs-nav");
  const floatingWin = document.getElementById("bi-chatbox-window");

  // Portal and navigation tabs become active
  if (authPortal) authPortal.style.display = "block";
  if (authTabsNav) authTabsNav.style.display = "flex";

  // Hide guest hero & landing sections
  if (guestHero) guestHero.style.display = "none";
  if (guestLanding) guestLanding.style.display = "none";

  // State classes on body
  document.body.classList.add("portal-view-active");
  document.body.classList.toggle("tab-chat-active", targetId === "tab-chat");
  if (targetId === "tab-chat" && floatingWin) {
    floatingWin.classList.remove("active");
  }

  // Update top navbar active links
  const navChatLink = document.getElementById("nav-open-chat-btn");
  const navMobileChatLink = document.getElementById("nav-mobile-chat-link");
  const navVideosLink = document.getElementById("nav-videos-link");
  const navMobileVideosLink = document.getElementById("nav-mobile-videos-link");
  const navHomeLinks = document.querySelectorAll('a[href="#landing-hero-section"]');

  if (targetId === "tab-chat") {
    if (navChatLink) navChatLink.classList.add("active");
    if (navMobileChatLink) navMobileChatLink.classList.add("active");
    navHomeLinks.forEach((l) => l.classList.remove("active"));
  } else {
    if (navChatLink) navChatLink.classList.remove("active");
    if (navMobileChatLink) navMobileChatLink.classList.remove("active");
  }

  if (targetId === "tab-videos") {
    if (navVideosLink) navVideosLink.classList.add("active");
    if (navMobileVideosLink) navMobileVideosLink.classList.add("active");
    navHomeLinks.forEach((l) => l.classList.remove("active"));
  } else {
    if (navVideosLink) navVideosLink.classList.remove("active");
    if (navMobileVideosLink) navMobileVideosLink.classList.remove("active");
  }

  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((b) => {
    if (b.getAttribute("data-tab") === targetId) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-panel").forEach((p) => {
    if (p.id === targetId) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });

  window.scrollTo({ top: 0, behavior: "smooth" });

  // Trigger refreshes if necessary
  if (targetId === "tab-cases") loadIncidents();
  if (targetId === "tab-videos") loadVideoInterviews();
  if (targetId === "tab-chat") {
    setTimeout(() => {
      const input = document.getElementById("tab-chat-text-input");
      if (input) input.focus();
    }, 150);
  }
}

function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      switchToTab(targetId);
    });
  });

  // Links pointing to #tab-cases (from More dropdown, mobile drawer, hero button)
  document.querySelectorAll('a[href="#tab-cases"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      switchToTab("tab-cases");
    });
  });

  // Links pointing to #tab-videos (from Navbar, hero button, mobile drawer)
  document.querySelectorAll('a[href="#tab-videos"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      switchToTab("tab-videos");
    });
  });

  // Filter chips in Case Triage Desk
  document.querySelectorAll(".cases-filter-btn").forEach((fBtn) => {
    fBtn.addEventListener("click", () => {
      document.querySelectorAll(".cases-filter-btn").forEach((b) => b.classList.remove("active"));
      fBtn.classList.add("active");
      const filterType = fBtn.getAttribute("data-case-filter") || "";
      loadIncidents(filterType);
    });
  });

  // Home links return guests back to the landing hero
  document.querySelectorAll('a[href="#landing-hero-section"], .nav-brand-mark').forEach((homeLink) => {
    homeLink.addEventListener("click", (e) => {
      if (!currentUser || !currentAuthToken) {
        document.body.classList.remove("tab-chat-active", "portal-view-active");
        const guestHero = document.getElementById("landing-hero-section");
        const guestLanding = document.getElementById("guest-landing-view");
        const authPortal = document.getElementById("authenticated-portal-view");
        const authTabsNav = document.getElementById("authenticated-tabs-nav");
        if (guestHero) guestHero.style.display = "flex";
        if (guestLanding) guestLanding.style.display = "none";
        if (authPortal) authPortal.style.display = "none";
        if (authTabsNav) authTabsNav.style.display = "none";
      }
      const navChatLink = document.getElementById("nav-open-chat-btn");
      const navMobileChatLink = document.getElementById("nav-mobile-chat-link");
      const navHomeLink = document.querySelector('.nav-links-menu a[href="#landing-hero-section"]');
      if (navChatLink) navChatLink.classList.remove("active");
      if (navMobileChatLink) navMobileChatLink.classList.remove("active");
      if (navHomeLink) navHomeLink.classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
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

  const modalForgotForm = document.getElementById("modal-forgot-form");
  const modalForgotPassBtn = document.getElementById("modal-forgot-pass-btn");
  const modalBackToSigninBtn = document.getElementById("modal-back-to-signin-btn");
  const modalForgotReqBtn = document.getElementById("modal-forgot-req-btn");
  const modalResetConfirmBtn = document.getElementById("modal-reset-confirm-btn");

  // Modal Tab Switching
  function switchModalTab(tab) {
    if (modalAuthAlert) modalAuthAlert.style.display = "none";
    if (tab === "register") {
      modalTabRegister.classList.add("active");
      modalTabSignin.classList.remove("active");
      modalRegisterForm.style.display = "block";
      modalLoginForm.style.display = "none";
      if (modalForgotForm) modalForgotForm.style.display = "none";
      if (modalAuthTitle) modalAuthTitle.innerHTML = 'Join <strong class="brand-bold">Beyond Identity</strong>';
      if (modalAuthSubtitle) modalAuthSubtitle.innerText = "Create an account for community or partner access";
    } else if (tab === "forgot") {
      modalTabSignin.classList.remove("active");
      modalTabRegister.classList.remove("active");
      modalLoginForm.style.display = "none";
      modalRegisterForm.style.display = "none";
      if (modalForgotForm) {
        modalForgotForm.style.display = "block";
        const step1 = document.getElementById("modal-forgot-step1");
        const step2 = document.getElementById("modal-forgot-step2");
        if (step1) step1.style.display = "block";
        if (step2) step2.style.display = "none";
      }
      if (modalAuthTitle) modalAuthTitle.innerText = "Reset Password";
      if (modalAuthSubtitle) modalAuthSubtitle.innerText = "Enter your registered email to request a reset token";
    } else {
      modalTabSignin.classList.add("active");
      modalTabRegister.classList.remove("active");
      modalLoginForm.style.display = "block";
      modalRegisterForm.style.display = "none";
      if (modalForgotForm) modalForgotForm.style.display = "none";
      if (modalAuthTitle) modalAuthTitle.innerHTML = 'Welcome to <strong class="brand-bold">Beyond Identity</strong>';
      if (modalAuthSubtitle) modalAuthSubtitle.innerText = "Sign in to your account or use 1-click access";
    }
  }

  if (modalTabSignin) modalTabSignin.addEventListener("click", () => switchModalTab("signin"));
  if (modalTabRegister) modalTabRegister.addEventListener("click", () => switchModalTab("register"));
  if (modalForgotPassBtn) modalForgotPassBtn.addEventListener("click", () => switchModalTab("forgot"));
  if (modalBackToSigninBtn) modalBackToSigninBtn.addEventListener("click", () => switchModalTab("signin"));

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

  // Handle Modal Forgot Password Request
  let modalResetEmail = "";
  if (modalForgotForm) {
    modalForgotForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("modal-forgot-email").value.trim();
      if (!email) return;

      if (modalForgotReqBtn) {
        modalForgotReqBtn.disabled = true;
        modalForgotReqBtn.innerText = "Generating Reset Token...";
      }

      try {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Unable to request password reset");

        modalResetEmail = email;
        const tokenInput = document.getElementById("modal-reset-token-input");
        if (tokenInput) tokenInput.value = data.reset_token || "";

        document.getElementById("modal-forgot-step1").style.display = "none";
        document.getElementById("modal-forgot-step2").style.display = "block";
        showModalAlert("Reset token generated! Enter your new password below.", false);
      } catch (err) {
        showModalAlert(err.message, true);
      } finally {
        if (modalForgotReqBtn) {
          modalForgotReqBtn.disabled = false;
          modalForgotReqBtn.innerText = "Request Reset Token";
        }
      }
    });
  }

  // Handle Modal Password Reset Confirm
  if (modalResetConfirmBtn) {
    modalResetConfirmBtn.addEventListener("click", async () => {
      const token = document.getElementById("modal-reset-token-input").value.trim();
      const newPassword = document.getElementById("modal-reset-newpass").value;

      if (!token) {
        showModalAlert("Please enter your reset token.", true);
        return;
      }
      if (newPassword.length < 6) {
        showModalAlert("Password must be at least 6 characters long.", true);
        return;
      }

      modalResetConfirmBtn.disabled = true;
      modalResetConfirmBtn.innerText = "Updating...";

      try {
        const res = await fetch(`${API_BASE}/auth/reset-password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password: newPassword }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to update password");

        switchModalTab("signin");
        if (modalResetEmail) {
          document.getElementById("modal-login-email").value = modalResetEmail;
        }
        document.getElementById("modal-login-password").value = "";
        showModalAlert("✅ Password reset successfully! Please sign in with your new password.", false);
      } catch (err) {
        showModalAlert(err.message, true);
      } finally {
        modalResetConfirmBtn.disabled = false;
        modalResetConfirmBtn.innerText = "Confirm & Save Password";
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
      window.location.href = "/login";
    });
  });

  document.querySelectorAll(".guest-open-signup-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      window.location.href = "/login?tab=register";
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
    switchToTab("tab-chat");
    showToast(`Welcome, ${currentUser?.name}! Chat Assistant is ready.`, "success");
    loadIncidents();
    loadListings();

    // Trigger Talking Chat Box Vocal Greeting right after login!
    if (typeof window.triggerPostLoginChatGreeting === "function") {
      window.triggerPostLoginChatGreeting(currentUser);
    } else if (typeof window.triggerPostLoginAIChatGreeting === "function") {
      window.triggerPostLoginAIChatGreeting(currentUser);
    }
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
  const guestHero = document.getElementById("landing-hero-section");
  const guestLanding = document.getElementById("guest-landing-view");
  const authPortal = document.getElementById("authenticated-portal-view");
  const guestHeroCta = document.getElementById("guest-hero-cta");
  const guestDemoStrip = document.getElementById("guest-demo-strip");
  const authTabsNav = document.getElementById("authenticated-tabs-nav");
  const container = document.getElementById("auth-actions-container");
  const navChatBtn = document.getElementById("nav-open-chat-btn");
  const navMoreDropdown = document.getElementById("nav-more-dropdown");
  const navMobileChatLink = document.getElementById("nav-mobile-chat-link");

  if (currentUser && currentAuthToken) {
    // Authenticated state
    document.body.classList.add("user-logged-in");
    document.documentElement.classList.add("user-logged-in");

    if (guestHero) guestHero.style.display = "none";
    if (guestLanding) guestLanding.style.display = "none";
    if (authPortal) authPortal.style.display = "block";
    if (authTabsNav) authTabsNav.style.display = "flex";

    // Show Chatbot and More navigation options for authenticated users
    if (navChatBtn) navChatBtn.style.display = "";
    if (navMoreDropdown) navMoreDropdown.style.display = "";
    if (navMobileChatLink) navMobileChatLink.style.display = "";
    document.querySelectorAll(".auth-only-nav").forEach((el) => {
      el.style.display = "";
    });
    document.querySelectorAll(".guest-only-nav").forEach((el) => {
      el.style.display = "none";
    });

    // Nav chat button directly switches to the chat tab
    if (navChatBtn) {
      navChatBtn.onclick = (e) => {
        e.preventDefault();
        switchToTab("tab-chat");
      };
    }

    // Update Welcome Banner
    const bannerGreeting = document.getElementById("member-banner-greeting");
    const bannerSub = document.getElementById("member-banner-sub");
    const bannerRole = document.getElementById("member-banner-role-badge");
    const bannerAvatar = document.getElementById("member-banner-avatar");

    const userName = currentUser.name || currentUser.email || "Community User";
    const roleUpper = (currentUser.role || "user").toUpperCase();
    const roleClass = currentUser.role === "verifier" ? "role-verifier" : currentUser.role === "admin" ? "role-admin" : "";
    const initials = userName
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "CU";

    if (bannerGreeting) bannerGreeting.innerText = `Welcome back, ${userName}!`;
    if (bannerSub) {
      bannerSub.innerText = currentUser.role === "verifier"
        ? "🛡️ NGO Partner Moderation Console: Access verified listings and confidential incident cases."
        : currentUser.role === "admin"
        ? "⚡ System Administrator Access: Full platform, moderation, and redressal management."
        : "👤 Community Seeker Portal: Full access to verified opportunities, confidential reporting, legal rights & health triage.";
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
            <span class="user-display-name">${escapeHtml(userName)}</span>
            <span class="user-role-badge ${roleClass}">${roleUpper}</span>
          </div>
        </div>
        <button class="btn btn-outline-danger" id="logout-btn" style="padding: 6px 14px; font-size: 12.5px; border-radius: 8px;">Sign Out</button>
      `;

      const directChatBtn = document.getElementById("nav-direct-chat-btn");
      if (directChatBtn) {
        directChatBtn.addEventListener("click", () => switchToTab("tab-chat"));
      }

      document.getElementById("logout-btn").addEventListener("click", () => {
        currentAuthToken = "";
        currentUser = null;
        localStorage.removeItem("bi_token");
        localStorage.removeItem("bi_user");
        document.body.classList.remove("user-logged-in", "portal-view-active", "tab-chat-active");
        document.documentElement.classList.remove("user-logged-in");
        renderUserStatus();
        showToast("Signed out successfully.", "info");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    // Role-specific action buttons & Case Triage Desk visibility
    const isNGOorAdmin = currentUser && (currentUser.role === "verifier" || currentUser.role === "admin");
    const verifierTab = document.getElementById("tab-btn-cases");
    const navLinkCases = document.getElementById("nav-link-cases");
    const navMobileCases = document.getElementById("nav-mobile-cases-link");

    if (verifierTab) {
      verifierTab.style.display = isNGOorAdmin ? "flex" : "none";
    }
    if (navLinkCases) {
      navLinkCases.style.display = isNGOorAdmin ? "" : "none";
    }
    if (navMobileCases) {
      navMobileCases.style.display = isNGOorAdmin ? "" : "none";
    }

    // Role-based Quick Action buttons inside authenticated portal
    const roleActionsContainer = document.getElementById("auth-role-quick-actions");
    if (roleActionsContainer) {
      if (isNGOorAdmin) {
        // NGO Partner: Case Board, Case Triage Desk, Video Interviews
        roleActionsContainer.innerHTML = `
          <span style="font-size: 12.5px; font-weight: 700; color: #2DD4BF; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">
            🏢 NGO Partner Quick Actions:
          </span>
          <a href="/cases" class="btn btn-secondary" style="padding: 10px 18px; font-size: 13px; text-decoration: none; border-color: rgba(56, 189, 248, 0.4); color: #38BDF8; border-radius: 10px; font-weight: 600;">
            <span>📋</span> Case Board
          </a>
          <button type="button" class="btn btn-secondary" id="quick-action-triage" style="padding: 10px 18px; font-size: 13px; border-color: rgba(45, 212, 191, 0.4); color: #2DD4BF; border-radius: 10px; font-weight: 600; background: rgba(45, 212, 191, 0.08); cursor: pointer;">
            <span>🛡️</span> Case Triage Desk
          </button>
          <button type="button" class="btn btn-secondary" id="quick-action-videos" style="padding: 10px 18px; font-size: 13px; border-color: rgba(244, 63, 94, 0.45); color: #FB7185; border-radius: 10px; font-weight: 700; background: rgba(244, 63, 94, 0.08); cursor: pointer;">
            <span>🎥</span> Video Interviews
          </button>
        `;
        const triageBtn = document.getElementById("quick-action-triage");
        if (triageBtn) triageBtn.addEventListener("click", () => switchToTab("tab-cases"));
        const videosBtn = document.getElementById("quick-action-videos");
        if (videosBtn) videosBtn.addEventListener("click", () => switchToTab("tab-videos"));
      } else {
        // Community Member: Anonymous Report, Case Board, Video Interviews
        roleActionsContainer.innerHTML = `
          <span style="font-size: 12.5px; font-weight: 700; color: #E8749A; text-transform: uppercase; letter-spacing: 0.05em; margin-right: 6px;">
            🌈 Community Quick Actions:
          </span>
          <button type="button" class="btn btn-secondary" id="quick-action-report" style="padding: 10px 18px; font-size: 13px; border-color: rgba(244, 63, 94, 0.45); color: #FB7185; border-radius: 10px; font-weight: 600; background: rgba(244, 63, 94, 0.08); cursor: pointer;">
            <span>🚨</span> Anonymous Report
          </button>
          <a href="/cases" class="btn btn-secondary" style="padding: 10px 18px; font-size: 13px; text-decoration: none; border-color: rgba(56, 189, 248, 0.4); color: #38BDF8; border-radius: 10px; font-weight: 600;">
            <span>📋</span> Case Board
          </a>
          <button type="button" class="btn btn-secondary" id="quick-action-videos" style="padding: 10px 18px; font-size: 13px; border-color: rgba(244, 63, 94, 0.45); color: #FB7185; border-radius: 10px; font-weight: 700; background: rgba(244, 63, 94, 0.08); cursor: pointer;">
            <span>🎥</span> Video Interviews
          </button>
        `;
        const reportBtn = document.getElementById("quick-action-report");
        if (reportBtn) reportBtn.addEventListener("click", () => switchToTab("tab-report"));
        const videosBtn = document.getElementById("quick-action-videos");
        if (videosBtn) videosBtn.addEventListener("click", () => switchToTab("tab-videos"));
      }
    }

    // Show floating launcher for authenticated users if not on chat tab
    const launcher = document.getElementById("bi-chat-launcher");
    if (launcher && !document.body.classList.contains("tab-chat-active")) {
      launcher.style.display = "flex";
    }
  } else {
    // ==========================================
    // GUEST STATE: Clean Single Home Default
    // ==========================================
    document.body.classList.remove("user-logged-in", "portal-view-active", "tab-chat-active");
    document.documentElement.classList.remove("user-logged-in");

    if (guestHero) guestHero.style.display = "flex";
    if (guestLanding) guestLanding.style.display = "none";
    if (guestHeroCta) guestHeroCta.style.display = "none";
    if (guestDemoStrip) guestDemoStrip.style.display = "none";
    if (authPortal) authPortal.style.display = "none";
    if (authTabsNav) authTabsNav.style.display = "none";

    // Strictly hide Chatbot and More navigation options for guests
    if (navChatBtn) navChatBtn.style.display = "none";
    if (navMoreDropdown) navMoreDropdown.style.display = "none";
    if (navMobileChatLink) navMobileChatLink.style.display = "none";
    document.querySelectorAll(".auth-only-nav").forEach((el) => {
      el.style.display = "none";
    });
    document.querySelectorAll(".guest-only-nav").forEach((el) => {
      el.style.display = "";
    });

    // Strictly hide floating launcher and window for unauthenticated guests
    const launcher = document.getElementById("bi-chat-launcher");
    const teaser = document.getElementById("bi-chat-teaser");
    const floatingWin = document.getElementById("bi-chatbox-window");
    if (launcher) launcher.style.display = "none";
    if (teaser) teaser.style.display = "none";
    if (floatingWin) {
      floatingWin.style.display = "none";
      floatingWin.classList.remove("active");
    }

    if (container) {
      container.innerHTML = `
        <a href="/login" class="btn btn-primary" id="open-login-btn" style="padding: 8px 18px; font-size: 13.5px; text-decoration: none; font-weight: 700;">Sign In</a>
      `;
    }
  }
}

// ==========================================================================
// Guest Limited Demo Controller (Sandbox & Opportunities Preview)
// ==========================================================================
function initGuestDemo() {
  const form = document.getElementById("guest-demo-form");
  const input = document.getElementById("guest-demo-input");
  if (!form && !input) return;
  const messagesBox = document.getElementById("guest-demo-chat-messages");
  const counterText = document.getElementById("guest-demo-counter-text");
  const lockedNotice = document.getElementById("guest-demo-locked-notice");
  const micBtn = document.getElementById("guest-demo-mic-btn");

  let demoQueryCount = parseInt(sessionStorage.getItem("bi_demo_queries_count") || "0", 10);
  const maxQueries = 2;

  function updateLimitUI() {
    const remaining = Math.max(0, maxQueries - demoQueryCount);
    if (counterText) {
      counterText.innerText = remaining > 0 ? `${remaining} Trial ${remaining === 1 ? 'Query' : 'Queries'} Left` : "Demo Limit Reached";
    }
    if (demoQueryCount >= maxQueries) {
      if (lockedNotice) lockedNotice.style.display = "flex";
      if (input) {
        input.placeholder = "🔒 Demo limit reached (2/2). Sign in to unlock unlimited voice assistant...";
        input.disabled = true;
      }
      const sendBtn = document.getElementById("guest-demo-send-btn");
      if (sendBtn) sendBtn.disabled = true;
    }
  }

  updateLimitUI();

  // Handle starter prompt chips
  document.querySelectorAll(".guest-demo-chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-query");
      if (!q) return;
      if (demoQueryCount >= maxQueries) {
        showToast("🔒 Demo limit reached. Sign in for unlimited Assistant access!", "info");
        const modal = document.getElementById("login-modal");
        if (modal) modal.classList.add("active");
        return;
      }
      if (input) {
        input.value = q;
        handleDemoSubmit(q);
      }
    });
  });

  // Handle Mic locked button
  if (micBtn) {
    micBtn.addEventListener("click", () => {
      showToast("🎙️ Voice Speech Input & Audio Playback is unlocked after login!", "info");
      const modal = document.getElementById("login-modal");
      if (modal) modal.classList.add("active");
    });
  }

  // Handle Form Submit
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = input?.value.trim();
      if (!q) return;
      handleDemoSubmit(q);
    });
  }

  async function handleDemoSubmit(queryText) {
    if (demoQueryCount >= maxQueries) {
      updateLimitUI();
      return;
    }

    if (!messagesBox) return;

    // Append User Message
    const userMsg = document.createElement("div");
    userMsg.className = "guest-demo-msg user";
    userMsg.innerHTML = `
      <div class="guest-demo-avatar">👤</div>
      <div class="guest-demo-bubble">${escapeHtml(queryText)}</div>
    `;
    messagesBox.appendChild(userMsg);

    if (input) input.value = "";

    // Append Loading Indicator
    const loadingMsg = document.createElement("div");
    loadingMsg.className = "guest-demo-msg assistant demo-loading-msg";
    loadingMsg.innerHTML = `
      <div class="guest-demo-avatar">🤖</div>
      <div class="guest-demo-bubble" style="color: var(--text-muted);">
        <span class="btn-spinner" style="display:inline-block; vertical-align: middle; margin-right: 6px;"></span>
        Consulting India Transgender Rights & Healthcare Knowledge Base...
      </div>
    `;
    messagesBox.appendChild(loadingMsg);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    try {
      const res = await fetch(`${API_BASE}/chatbot/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText, conversation_history: [] }),
      });

      loadingMsg.remove();

      let answer = "";
      if (res.ok) {
        const data = await res.json();
        answer = data.reply || data.answer || "Thank you for asking. Our system contains complete case guidance.";
      } else {
        answer = "I am currently running in limited guest demo mode. Please sign in or use 1-click evaluation to unlock live database matching and continuous voice consultation.";
      }

      const formattedHtml = parseMarkdown(answer);

      const assistantMsg = document.createElement("div");
      assistantMsg.className = "guest-demo-msg assistant";
      assistantMsg.innerHTML = `
        <div class="guest-demo-avatar">🤖</div>
        <div class="guest-demo-bubble">
          ${formattedHtml}
          <div style="margin-top: 8px; font-size: 11px; color: var(--text-muted); border-top: 1px dashed var(--border-subtle); padding-top: 5px;">
            🔒 <em>Demo Response: Sign in to unlock full voice audio synthesis, direct schemes application & caseworker triage.</em>
          </div>
        </div>
      `;
      messagesBox.appendChild(assistantMsg);
      messagesBox.scrollTop = messagesBox.scrollHeight;

      demoQueryCount++;
      sessionStorage.setItem("bi_demo_queries_count", demoQueryCount.toString());
      updateLimitUI();

    } catch (err) {
      loadingMsg.remove();
      const errMsg = document.createElement("div");
      errMsg.className = "guest-demo-msg assistant";
      errMsg.innerHTML = `
        <div class="guest-demo-avatar">🤖</div>
        <div class="guest-demo-bubble" style="color: var(--accent-rose);">
          Service temporarily busy. Please sign in to connect directly to the 24/7 Rights Assistant.
        </div>
      `;
      messagesBox.appendChild(errMsg);
    }
  }

  // Opportunities Demo Filtering
  document.querySelectorAll(".guest-opp-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".guest-opp-filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const cat = btn.getAttribute("data-cat");

      document.querySelectorAll(".guest-demo-opp-card").forEach((card) => {
        const cardCat = card.getAttribute("data-cat");
        if (cat === "all" || cardCat === cat) {
          card.style.display = "flex";
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  // Re-bind demo login buttons in demo section
  document.querySelectorAll(".demo-login-btn").forEach((btn) => {
    btn.onclick = async () => {
      const email = btn.getAttribute("data-email");
      const password = btn.getAttribute("data-password");
      if (email && password) {
        await executeLogin(email, password, false);
      }
    };
  });
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
// ==========================================
// Listings Directory
// ==========================================
let allCachedListings = [];
let currentCategoryFilter = "";
let currentListingsSearch = "";

function formatContactInfo(contactInfo) {
  if (!contactInfo) {
    return `<span class="contact-pill info-pill" style="color: var(--text-muted); font-size: 11.5px;">🛡️ Relay via Beyond Identity</span>`;
  }

  // Split by " / " or " /" or "/ " or "," while keeping parts clean
  const pieces = contactInfo.split(/\s*[\/,]\s*/).map(p => p.trim()).filter(Boolean);
  const pills = [];

  for (const piece of pieces) {
    if (piece.includes("@") && !piece.startsWith("http")) {
      pills.push(`
        <a href="mailto:${escapeHtml(piece)}" class="contact-pill email-pill" title="Send email to ${escapeHtml(piece)}">
          ✉️ <span>${escapeHtml(piece)}</span>
        </a>
      `);
    } else if (piece.startsWith("http://") || piece.startsWith("https://") || piece.startsWith("www.")) {
      const url = piece.startsWith("www.") ? `https://${piece}` : piece;
      const cleanDisplay = piece.replace(/^https?:\/\//i, "").replace(/\/$/, "");
      pills.push(`
        <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="contact-pill web-pill" title="Visit website">
          🌐 <span>${escapeHtml(cleanDisplay)}</span>
        </a>
      `);
    } else if (/\d{4,}/.test(piece) || /^\d{5}$/.test(piece)) {
      const cleanTel = piece.replace(/[^\d+]/g, "");
      pills.push(`
        <a href="tel:${escapeHtml(cleanTel)}" class="contact-pill phone-pill" title="Call ${escapeHtml(piece)}">
          📞 <strong>${escapeHtml(piece)}</strong>
        </a>
      `);
    } else {
      pills.push(`
        <span class="contact-pill info-pill">
          📌 <span>${escapeHtml(piece)}</span>
        </span>
      `);
    }
  }

  return pills.length > 0
    ? `<div class="card-contacts-wrap">${pills.join("")}</div>`
    : `<span class="contact-pill info-pill">📌 ${escapeHtml(contactInfo)}</span>`;
}

function renderListings(listings) {
  const container = document.getElementById("listings-container");
  if (!container) return;

  const countBadge = document.getElementById("listings-count-badge");
  if (countBadge) {
    countBadge.textContent = `${listings.length} verified opportunit${listings.length === 1 ? 'y' : 'ies'}`;
  }

  if (listings.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding: 48px 20px; color: var(--text-muted); background: var(--bg-card); border-radius: 12px; border: 1px dashed var(--border-subtle);">
        <div style="font-size: 32px; margin-bottom: 12px;">🔍</div>
        <h4 style="font-size: 16px; margin-bottom: 6px; color: var(--text-main);">No verified opportunities match your search</h4>
        <p style="font-size: 13px;">Try selecting "All Categories" or searching for a different city, college, NGO, or workplace.</p>
      </div>
    `;
    return;
  }

  const categoryIcons = {
    education: "🎓",
    employment: "💼",
    housing: "🏠",
    healthcare: "🏥",
    scheme: "🏛️",
    scholarship: "📜",
    community: "🤝",
  };

  container.innerHTML = listings
    .map((item) => {
      const badgeClass =
        item.status === "verified"
          ? "badge-verified"
          : item.status === "pending"
          ? "badge-pending"
          : "badge-delisted";

      const catIcon = categoryIcons[item.category] || "📂";

      return `
      <div class="listing-card">
        <div>
          <div class="card-top">
            <span class="category-tag">${catIcon} ${item.category.toUpperCase()}</span>
            <span class="badge ${badgeClass}">${item.status}</span>
          </div>
          <h3 class="card-title">${escapeHtml(item.title)}</h3>
          <div class="card-org">🏛️ ${escapeHtml(item.organization_name || "Community Partner")}</div>
          <p class="card-desc">${escapeHtml(item.description || "No description provided.")}</p>
        </div>
        <div>
          <div class="card-footer">
            <div class="card-footer-row">
              <span class="card-location">📍 <strong>${escapeHtml(item.location || "Pan-India")}</strong></span>
            </div>
            <div class="card-footer-row" style="margin-top: 8px;">
              ${formatContactInfo(item.contact_info)}
            </div>
          </div>
        </div>
      </div>
    `;
    })
    .join("");
}

function filterAndRenderListings() {
  let filtered = allCachedListings;
  if (currentListingsSearch) {
    const term = currentListingsSearch.toLowerCase();
    filtered = filtered.filter(item => {
      const title = (item.title || "").toLowerCase();
      const org = (item.organization_name || "").toLowerCase();
      const desc = (item.description || "").toLowerCase();
      const loc = (item.location || "").toLowerCase();
      const contact = (item.contact_info || "").toLowerCase();
      const cat = (item.category || "").toLowerCase();
      return title.includes(term) || org.includes(term) || desc.includes(term) || loc.includes(term) || contact.includes(term) || cat.includes(term);
    });
  }
  renderListings(filtered);
}

async function loadListings(categoryFilter = "") {
  currentCategoryFilter = categoryFilter;
  const container = document.getElementById("listings-container");
  if (!container) return;

  container.innerHTML = `<div style="grid-column: 1 / -1; text-align:center; padding: 40px; color: var(--text-muted);">Loading verified opportunities...</div>`;

  try {
    let url = `${API_BASE}/listings/`;
    if (categoryFilter) url += `?category=${encodeURIComponent(categoryFilter)}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load listings");
    allCachedListings = await res.json();
    filterAndRenderListings();
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

// Setup search bar listener
document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("listings-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      currentListingsSearch = e.target.value.trim();
      filterAndRenderListings();
    });
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
      reporter_consent_public: !!document.getElementById("inc-consent-public")?.checked,
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
// Legal Rights Awareness Module
// ==========================================
function setupAwarenessUI() {
  const queryInput = document.getElementById("awareness-query-input");
  const queryBtn = document.getElementById("awareness-query-btn");
  const resultCard = document.getElementById("awareness-result-card");

  // Modal elements
  const modal =
    document.getElementById("awareness-assistant-modal") ||
    document.getElementById("awareness-ai-modal");
  const openChatBtn = document.getElementById("open-awareness-chat-btn");
  const openTalkBtn = document.getElementById("open-awareness-talk-btn");
  const closeModalBtn = document.getElementById("close-awareness-modal");
  const switchToChatBtn = document.getElementById("switch-to-chat-btn");
  const switchToTalkBtn = document.getElementById("switch-to-talk-btn");
  const chatView = document.getElementById("awareness-chat-view");
  const talkView = document.getElementById("awareness-talk-view");

  // Chat view elements
  const chatMessages = document.getElementById("awareness-chat-messages");
  const chatInput = document.getElementById("awareness-chat-input");
  const chatSendBtn = document.getElementById("awareness-chat-send-btn");
  const chatMicBtn = document.getElementById("chat-input-mic-btn");

  // Talking view elements
  const talkOrb = document.querySelector(".talk-orb-container");
  const talkMicBtn = document.getElementById("talk-main-mic-btn");
  const talkStatusText = document.getElementById("talk-status-text");
  const talkSubstatus = document.getElementById("talk-substatus");
  const talkTranscriptBox = document.getElementById("talk-transcript-box");
  const talkUserTranscript = document.getElementById("talk-user-transcript");
  const talkResponseBox = document.getElementById("talk-response-box");
  const talkAiText =
    document.getElementById("talk-assistant-text") ||
    document.getElementById("talk-ai-text");
  const talkLawCite = document.getElementById("talk-law-cite");
  const talkReplayBtn = document.getElementById("talk-replay-btn");
  const talkStopBtn = document.getElementById("talk-stop-btn");
  const talkAutoSpeakToggle = document.getElementById("talk-auto-speak-toggle");

  // Conversation history state
  let awarenessChatHistory = [
    {
      role: "assistant",
      content:
        "Welcome! I am your Legal Rights Awareness Assistant. Ask me anything about your rights under the **Transgender Persons (Protection of Rights) Act 2019**, **NALSA (2014)** Supreme Court judgment, Section 12 Free Legal Aid, workplace non-discrimination, or housing protections.",
      speech_text:
        "Welcome to the Legal Rights Awareness Assistant. Ask me anything about your rights under Indian law, workplace non-discrimination, or how to get free legal aid under Section 12.",
    },
  ];

  let isSpeechListening = false;
  let activeSpeechRecognition = null;
  let lastSpokenText = "";

  // Speech Synthesis Helper
  function speakText(text) {
    if (!("speechSynthesis" in window)) return;
    if (!text) return;

    lastSpokenText = text;
    SweetVoiceEngine.speak(text, {
      onstart: () => {
        if (talkOrb && talkMicBtn) {
          talkOrb.classList.add("speaking");
          talkOrb.classList.remove("listening");
          talkMicBtn.classList.add("speaking");
          talkMicBtn.classList.remove("listening");
          if (talkStatusText) talkStatusText.innerText = "Speaking Answer Aloud (Female Voice)...";
        }
      },
      onend: () => {
        if (talkOrb && talkMicBtn) {
          talkOrb.classList.remove("speaking");
          talkMicBtn.classList.remove("speaking");
          if (talkStatusText) talkStatusText.innerText = "Click Microphone to Talk";
        }
      },
      onerror: () => {
        if (talkOrb && talkMicBtn) {
          talkOrb.classList.remove("speaking");
          talkMicBtn.classList.remove("speaking");
          if (talkStatusText) talkStatusText.innerText = "Click Microphone to Talk";
        }
      }
    });
  }

  function stopSpeech() {
    SweetVoiceEngine.stop();
    if (talkOrb && talkMicBtn) {
      talkOrb.classList.remove("speaking");
      talkMicBtn.classList.remove("speaking");
      if (talkStatusText) talkStatusText.innerText = "Click Microphone to Talk";
    }
  }

  // Markdown-to-HTML parser for chat bubbles
  function formatReply(text) {
    let html = escapeHtml(text);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Headers
    html = html.replace(/### (.*?)\n/g, "<h4 style='margin:6px 0; color:var(--accent-cyan);'>$1</h4>");
    html = html.replace(/#### (.*?)\n/g, "<h5 style='margin:4px 0; color:var(--text-primary); font-weight:700;'>$1</h5>");
    // Line breaks
    html = html.replace(/\n/g, "<br/>");
    return html;
  }

  // Render chat messages
  function renderChat() {
    if (!chatMessages) return;
    chatMessages.innerHTML = "";

    awarenessChatHistory.forEach((msg) => {
      const isUser = msg.role === "user";
      const row = document.createElement("div");
      row.className = `awareness-msg ${isUser ? "user" : "assistant"}`;

      const avatar = document.createElement("div");
      avatar.className = "awareness-avatar";
      avatar.innerText = isUser ? "👤" : "⚖️";

      const bubbleWrap = document.createElement("div");
      bubbleWrap.style.display = "flex";
      bubbleWrap.style.flexDirection = "column";
      bubbleWrap.style.maxWidth = "100%";

      const bubble = document.createElement("div");
      bubble.className = "awareness-bubble";
      bubble.innerHTML = isUser ? escapeHtml(msg.content) : formatReply(msg.content);
      bubbleWrap.appendChild(bubble);

      // Actions row for assistant messages
      if (!isUser && msg.speech_text) {
        const actions = document.createElement("div");
        actions.className = "awareness-bubble-actions";

        const listenBtn = document.createElement("button");
        listenBtn.className = "awareness-bubble-btn";
        listenBtn.innerHTML = "<span>🔊</span> Listen";
        listenBtn.onclick = () => speakText(msg.speech_text);
        actions.appendChild(listenBtn);

        const copyBtn = document.createElement("button");
        copyBtn.className = "awareness-bubble-btn";
        copyBtn.innerHTML = "<span>📋</span> Copy";
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(msg.content);
          copyBtn.innerText = "✓ Copied";
          setTimeout(() => (copyBtn.innerHTML = "<span>📋</span> Copy"), 1500);
        };
        actions.appendChild(copyBtn);

        bubbleWrap.appendChild(actions);
      }

      row.appendChild(avatar);
      row.appendChild(bubbleWrap);
      chatMessages.appendChild(row);
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Send message in Chat Form
  async function sendChatMessage(text) {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    if (chatInput) chatInput.value = "";

    awarenessChatHistory.push({ role: "user", content: cleanText });
    renderChat();

    // Add temporary loading indicator
    const loadingRow = document.createElement("div");
    loadingRow.className = "awareness-msg assistant";
    loadingRow.id = "chat-loading-indicator";
    loadingRow.innerHTML = `
      <div class="awareness-avatar">⚖️</div>
      <div class="awareness-bubble" style="color:var(--text-muted); font-style:italic;">
        Consulting Indian statutory knowledge base...
      </div>
    `;
    chatMessages.appendChild(loadingRow);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const messagesPayload = awarenessChatHistory
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE}/awareness/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: messagesPayload, voice_mode: false }),
      });

      if (!res.ok) throw new Error("Failed to consult awareness assistant");
      const data = await res.json();

      const loader = document.getElementById("chat-loading-indicator");
      if (loader) loader.remove();

      awarenessChatHistory.push({
        role: "assistant",
        content: data.reply,
        speech_text: data.speech_text,
        matched_topic: data.matched_topic,
        actionable_steps: data.actionable_steps,
      });

      renderChat();
    } catch (err) {
      const loader = document.getElementById("chat-loading-indicator");
      if (loader) loader.remove();

      awarenessChatHistory.push({
        role: "assistant",
        content: `Error: Unable to complete legal query (${escapeHtml(err.message)}). Please check connection or try again.`,
        speech_text: "Sorry, I encountered an issue processing your legal request.",
      });
      renderChat();
    }
  }

  // Modal Open & Mode Switchers
  function openModal(mode = "chat") {
    if (!modal) return;
    modal.classList.add("active");
    setModalMode(mode);
    renderChat();
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("active");
    stopSpeech();
    if (activeSpeechRecognition) {
      try {
        activeSpeechRecognition.stop();
      } catch (e) {}
    }
  }

  function setModalMode(mode) {
    stopSpeech();
    if (mode === "chat") {
      switchToChatBtn.classList.add("active");
      switchToChatBtn.style.background = "var(--accent-cyan)";
      switchToChatBtn.style.color = "#000";
      switchToTalkBtn.classList.remove("active");
      switchToTalkBtn.style.background = "transparent";
      switchToTalkBtn.style.color = "var(--text-muted)";
      if (chatView) chatView.style.display = "flex";
      if (talkView) talkView.style.display = "none";
      if (chatInput) chatInput.focus();
    } else {
      switchToTalkBtn.classList.add("active");
      switchToTalkBtn.style.background = "var(--accent-violet)";
      switchToTalkBtn.style.color = "#fff";
      switchToChatBtn.classList.remove("active");
      switchToChatBtn.style.background = "transparent";
      switchToChatBtn.style.color = "var(--text-muted)";
      if (chatView) chatView.style.display = "none";
      if (talkView) talkView.style.display = "flex";
    }
  }

  if (openChatBtn) openChatBtn.addEventListener("click", () => openModal("chat"));
  if (openTalkBtn) openTalkBtn.addEventListener("click", () => openModal("talk"));
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);
  if (switchToChatBtn) switchToChatBtn.addEventListener("click", () => setModalMode("chat"));
  if (switchToTalkBtn) switchToTalkBtn.addEventListener("click", () => setModalMode("talk"));

  // Close modal when clicking outside
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  }

  // Chat send listeners
  if (chatSendBtn) {
    chatSendBtn.addEventListener("click", () => sendChatMessage(chatInput.value));
  }
  if (chatInput) {
    chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendChatMessage(chatInput.value);
    });
  }

  // Chat Prompt Chips
  document.querySelectorAll(".chat-prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt") || chip.innerText;
      sendChatMessage(prompt);
    });
  });

  // Speech Recognition Initializer
  function createSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) return null;
    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = "en-IN";
    return rec;
  }

  // Chat Mic button (Quick Speech-to-Text)
  if (chatMicBtn) {
    chatMicBtn.addEventListener("click", () => {
      const rec = createSpeechRecognition();
      if (!rec) {
        alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
        return;
      }
      chatMicBtn.innerText = "🔴";
      chatInput.placeholder = "Listening... Speak your legal question now";

      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        chatInput.value = transcript;
        chatMicBtn.innerText = "🎙️";
        chatInput.placeholder = "Type your legal question or click 🎙️ to talk...";
        sendChatMessage(transcript);
      };
      rec.onerror = () => {
        chatMicBtn.innerText = "🎙️";
        chatInput.placeholder = "Type your legal question or click 🎙️ to talk...";
      };
      rec.onend = () => {
        chatMicBtn.innerText = "🎙️";
        chatInput.placeholder = "Type your legal question or click 🎙️ to talk...";
      };
      rec.start();
    });
  }

  // Talking Form Mic Handler
  if (talkMicBtn) {
    talkMicBtn.addEventListener("click", () => {
      stopSpeech();
      const rec = createSpeechRecognition();
      if (!rec) {
        alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
        return;
      }

      if (isSpeechListening && activeSpeechRecognition) {
        activeSpeechRecognition.stop();
        isSpeechListening = false;
        talkOrb.classList.remove("listening");
        talkMicBtn.classList.remove("listening");
        talkStatusText.innerText = "Click the Microphone to Talk";
        return;
      }

      activeSpeechRecognition = rec;
      isSpeechListening = true;
      talkOrb.classList.add("listening");
      talkMicBtn.classList.add("listening");
      talkStatusText.innerText = "Listening... (Speak your question)";
      talkSubstatus.innerText = "Go ahead, we are listening to your legal question...";

      rec.onresult = async (e) => {
        isSpeechListening = false;
        talkOrb.classList.remove("listening");
        talkMicBtn.classList.remove("listening");
        const transcript = e.results[0][0].transcript;

        // Show transcript
        if (talkTranscriptBox && talkUserTranscript) {
          talkTranscriptBox.style.display = "block";
          talkUserTranscript.innerText = `"${transcript}"`;
        }

        talkStatusText.innerText = "Analyzing Indian Legal Rights...";
        talkSubstatus.innerText = "Formulating plain-language guidance and statutory provisions...";

        try {
          const res = await fetch(`${API_BASE}/awareness/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              messages: [{ role: "user", content: transcript }],
              voice_mode: true,
            }),
          });

          if (!res.ok) throw new Error("Failed to process question");
          const data = await res.json();

          // Also record into conversation history
          awarenessChatHistory.push({ role: "user", content: transcript });
          awarenessChatHistory.push({
            role: "assistant",
            content: data.reply,
            speech_text: data.speech_text,
            matched_topic: data.matched_topic,
            actionable_steps: data.actionable_steps,
          });

          // Display talking response box
          if (talkResponseBox && talkAiText) {
            talkResponseBox.style.display = "block";
            talkAiText.innerText = data.speech_text || data.reply;
            if (talkLawCite) talkLawCite.innerText = data.applicable_law || "Statutory Protection";
          }

          talkStatusText.innerText = "Click Microphone to Ask Another Question";
          talkSubstatus.innerText = "Your rights are protected under Indian Law.";

          // Auto-speak out loud
          if (talkAutoSpeakToggle && talkAutoSpeakToggle.checked) {
            speakText(data.speech_text);
          }
        } catch (err) {
          talkStatusText.innerText = "Error analyzing question";
          talkSubstatus.innerText = err.message;
        }
      };

      rec.onerror = (e) => {
        isSpeechListening = false;
        talkOrb.classList.remove("listening");
        talkMicBtn.classList.remove("listening");
        talkStatusText.innerText = "Click the Microphone to Talk";
        talkSubstatus.innerText = "Could not detect audio clearly. Please try again.";
      };

      rec.onend = () => {
        isSpeechListening = false;
        talkOrb.classList.remove("listening");
        talkMicBtn.classList.remove("listening");
      };

      rec.start();
    });
  }

  // Talking replay and stop buttons
  if (talkReplayBtn) {
    talkReplayBtn.addEventListener("click", () => {
      if (lastSpokenText) speakText(lastSpokenText);
    });
  }
  if (talkStopBtn) {
    talkStopBtn.addEventListener("click", stopSpeech);
  }

  // Original single-query in tab
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
          <button type="button" class="btn btn-secondary" id="speak-query-result-btn" style="font-size:12px; padding:6px 12px; display:flex; align-items:center; gap:6px;">
            <span>🔊</span> Read Aloud
          </button>
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

      const speakResultBtn = document.getElementById("speak-query-result-btn");
      if (speakResultBtn) {
        speakResultBtn.addEventListener("click", () => {
          speakText(`Under ${data.applicable_law}, your rights are legally protected. ${data.explanation} For free legal support, contact NALSA Helpline at 15100.`);
        });
      }

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

  // Chips in Tab 3
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.innerText;
      performQuery(chip.innerText);
    });
  });
}

// ==========================================
// Health Assistant Decision Tree Wizard
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
// Incidents / Case Management (Visible to All)
// ==========================================
async function loadIncidents(filterType = "") {
  const container = document.getElementById("cases-container");
  if (!container) return;

  const headerAction = document.getElementById("cases-header-action");
  if (headerAction) {
    if (currentUser?.role === "verifier" || currentUser?.role === "admin") {
      headerAction.innerHTML = `
        <span style="font-size:12px; color:var(--accent-cyan); display:flex; align-items:center; gap:6px; background:rgba(45,212,191,0.1); padding:6px 12px; border-radius:20px; border:1px solid rgba(45,212,191,0.25);">
          🛡️ NGO Verifier: <strong>${escapeHtml(currentUser.name || currentUser.email)}</strong>
        </span>
      `;
    } else {
      headerAction.innerHTML = `
        <a href="/login?role=ngo" class="btn btn-secondary" style="font-size:12px; padding:6px 14px; text-decoration:none; border-radius:20px;">
          🏢 NGO Partner Sign In
        </a>
      `;
    }
  }

  container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted);"><span style="display:inline-block; font-size:24px;">⏳</span><p style="margin-top:8px;">Loading filed discrimination cases...</p></div>`;

  try {
    const headers = {};
    if (currentAuthToken) {
      headers["Authorization"] = `Bearer ${currentAuthToken}`;
    }
    const queryUrl = filterType ? `${API_BASE}/incidents/?incident_type=${encodeURIComponent(filterType)}` : `${API_BASE}/incidents/`;
    const res = await fetch(queryUrl, { headers });
    if (!res.ok) throw new Error("Could not load incidents");
    const incidents = await res.json();

    if (incidents.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--text-muted); background:var(--bg-tertiary); border-radius:16px; border:1px solid var(--border-subtle);">
          <div style="font-size:32px; margin-bottom:8px;">📋</div>
          <p style="font-size:15px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">No cases found${filterType ? ` for category "${escapeHtml(filterType)}"` : ""}</p>
          <p style="font-size:13px;">Community members can safely report discrimination using the <a href="#tab-report" style="color:var(--accent-cyan);" onclick="switchToTab('tab-report')">Report Incident</a> module.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = incidents
      .map(
        (inc) => {
          const urgencyColor = inc.urgency_level === "high" ? "#FB7185" : inc.urgency_level === "medium" ? "#FBBF24" : "#34D399";
          const statusBadgeClass = inc.status === "resolved" ? "badge-verified" : inc.status === "escalated_to_ngo" ? "badge-featured" : "badge-pending";
          const statusLabel = inc.status === "escalated_to_ngo" ? "ESCALATED TO NGO" : inc.status.toUpperCase();

          const schemesList = (inc.matched_schemes || []).slice(0, 2).map((s) => `
            <span style="display:inline-flex; align-items:center; gap:4px; font-size:11.5px; background:rgba(45,212,191,0.12); color:var(--accent-cyan); padding:3px 8px; border-radius:6px; border:1px solid rgba(45,212,191,0.25);">
              🏛️ ${escapeHtml(s.name)}
            </span>
          `).join(" ");

          const ngosList = (inc.matched_ngos || []).slice(0, 2).map((n) => {
            const phone = (n.contact_phone || "").trim();
            const phoneStr = phone ? ` (${escapeHtml(phone)})` : "";
            return `
              <span style="display:inline-flex; align-items:center; gap:4px; font-size:11.5px; background:rgba(165,180,252,0.12); color:var(--accent-violet); padding:3px 8px; border-radius:6px; border:1px solid rgba(165,180,252,0.25);">
                🤝 ${escapeHtml(n.name)}${phoneStr}
              </span>
            `;
          }).join(" ");

          const dateDisplay = inc.incident_date || (inc.created_at ? inc.created_at.slice(0, 10) : "");

          return `
      <div class="listing-card" style="margin-bottom:16px; border:1px solid var(--border-subtle); border-radius:14px; padding:18px; background:var(--bg-card); box-shadow:0 4px 14px rgba(0,0,0,0.04);">
        <div class="card-top" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="category-tag" style="font-weight:700; font-size:12px;">🚨 ${inc.incident_type ? inc.incident_type.replace('_', ' ').toUpperCase() : 'INCIDENT'}</span>
            <span style="font-size:11px; font-weight:700; color:${urgencyColor}; border:1px solid ${urgencyColor}44; padding:2px 8px; border-radius:12px; background:${urgencyColor}15;">
              ⚠️ ${inc.urgency_level ? inc.urgency_level.toUpperCase() : 'NORMAL'}
            </span>
          </div>
          <span class="badge ${statusBadgeClass}" style="font-size:11px; font-weight:700;">${statusLabel}</span>
        </div>
        <h3 class="card-title" style="font-size:17px; margin-bottom:6px; color:var(--text-primary);">${escapeHtml(inc.title)}</h3>
        <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:10px; display:flex; flex-wrap:wrap; gap:12px;">
          <span>📍 <strong>${escapeHtml(inc.location_city || "Pan-India")}, ${escapeHtml(inc.location_state || "")}</strong></span>
          <span>${inc.is_anonymous ? "🕵️ Anonymous Report" : "👤 Community Member"}</span>
          <span>📅 <strong>${escapeHtml(dateDisplay || "Recent")}</strong></span>
          <span style="font-size:11.5px; padding:2px 6px; border-radius:6px; background:${inc.public_visible && inc.reporter_consent_public ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)'}; color:${inc.public_visible && inc.reporter_consent_public ? '#34D399' : '#FB7185'};">
            ${inc.public_visible && inc.reporter_consent_public ? '🌐 Public Board: Visible' : '🔒 Public Board: Hidden'}
          </span>
        </div>
        <p class="card-desc" style="font-size:14px; line-height:1.55; color:var(--text-secondary); margin-bottom:12px;">${escapeHtml(inc.description)}</p>
        
        ${inc.perpetrator_details ? `<div class="case-perpetrator" style="font-size:12.5px; margin-bottom:10px; padding:6px 10px; border-radius:8px; background:rgba(244,63,94,0.08); border:1px solid rgba(244,63,94,0.2); color:var(--accent-rose);"><strong>Alleged Entity:</strong> ${escapeHtml(inc.perpetrator_details)}</div>` : ""}
        
        ${schemesList || ngosList ? `
          <div style="margin-bottom:12px; display:flex; flex-wrap:wrap; gap:6px;">
            ${schemesList}
            ${ngosList}
          </div>
        ` : ""}

        ${inc.public_summary ? `<div style="font-size:12.5px; color:#A78BFA; margin-bottom:10px; padding:6px 10px; border-radius:8px; background:rgba(168,85,247,0.08); border:1px solid rgba(168,85,247,0.25);"><strong>Public Summary:</strong> ${escapeHtml(inc.public_summary)}</div>` : ""}

        ${inc.case_notes ? `<div style="font-size:12.5px; color:var(--accent-cyan); margin-bottom:10px; padding:6px 10px; border-radius:8px; background:rgba(45,212,191,0.08); border:1px solid rgba(45,212,191,0.2);"><strong>Case Triage Notes:</strong> ${escapeHtml(inc.case_notes)}</div>` : ""}
        
        <div class="card-footer" style="padding-top:14px; border-top:1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
          <span style="font-size:13px; color:var(--text-muted);">Assigned Partner: <strong style="color:var(--text-primary);">${escapeHtml(inc.assigned_ngo || "National Triage Cell / Pending")}</strong></span>
          ${
            currentUser?.role === "verifier" || currentUser?.role === "admin"
              ? `
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn btn-secondary" style="padding:6px 12px; font-size:12px; border-radius:8px;" onclick="updateIncidentStatusPrompt(${inc.id}, 'escalated_to_ngo')">Escalate to NGO</button>
              <button class="btn btn-primary" style="padding:6px 12px; font-size:12px; border-radius:8px;" onclick="updateIncidentStatusPrompt(${inc.id}, 'resolved')">Mark Resolved</button>
              <button class="btn btn-secondary" style="padding:6px 12px; font-size:12px; border-radius:8px; border-color:${inc.public_visible ? '#10B981' : '#F43F5E'}; color:${inc.public_visible ? '#34D399' : '#FB7185'};" onclick="toggleIncidentPublicVisibility(${inc.id}, ${!inc.public_visible})">${inc.public_visible ? '🌐 Public Board: ON' : '🔒 Public Board: OFF'}</button>
              <button class="btn btn-secondary" style="padding:6px 12px; font-size:12px; border-radius:8px;" onclick="editIncidentPublicSummaryPrompt(${inc.id})">✏️ Edit Summary</button>
            </div>
          `
              : ""
          }
        </div>
      </div>
    `;
        }
      )
      .join("");
  } catch (e) {
    container.innerHTML = `<div style="color:var(--accent-rose); padding:20px; background:rgba(244,63,94,0.08); border-radius:12px;">Error loading incidents: ${escapeHtml(e.message)}</div>`;
  }
}

async function toggleIncidentPublicVisibility(incidentId, targetVisible) {
  try {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentAuthToken}`,
      },
      body: JSON.stringify({ public_visible: targetVisible }),
    });
    if (!res.ok) throw new Error("Failed to toggle public visibility");
    alert(`Case #${incidentId} public visibility set to: ${targetVisible ? "VISIBLE" : "HIDDEN"}`);
    loadIncidents();
  } catch (err) {
    alert("Visibility toggle failed: " + err.message);
  }
}

async function editIncidentPublicSummaryPrompt(incidentId) {
  const newSummary = prompt("Enter public summary (anonymized description shown to visitors on Case Board):", "");
  if (newSummary === null) return;

  try {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentAuthToken}`,
      },
      body: JSON.stringify({ public_summary: newSummary.trim() }),
    });
    if (!res.ok) throw new Error("Failed to update public summary");
    alert(`Case #${incidentId} public summary updated successfully!`);
    loadIncidents();
  } catch (err) {
    alert("Public summary update failed: " + err.message);
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

// ==========================================================================
// 24/7 Beyond Identity Chatbox Controller
// ==========================================================================
function initChatbox() {
  const launcher = document.getElementById("bi-chat-launcher");
  const navBtn = document.getElementById("nav-open-chat-btn");
  const heroBtn = document.getElementById("hero-open-chat-btn");
  const teaser = document.getElementById("bi-chat-teaser");
  const teaserClose = document.getElementById("bi-chat-teaser-close");
  const windowEl = document.getElementById("bi-chatbox-window");
  const closeBtn = document.getElementById("bi-chat-close-btn");
  const clearBtn = document.getElementById("bi-chat-clear-btn");
  const voiceToggle = document.getElementById("bi-chat-voice-toggle");
  const categoryBar = document.getElementById("bi-chat-category-bar");
  const messagesContainer = document.getElementById("bi-chat-messages");
  const input = document.getElementById("bi-chat-input");
  const sendBtn = document.getElementById("bi-chat-send-btn");
  const micBtn = document.getElementById("bi-chat-mic-btn");

  if (!launcher || !windowEl || !messagesContainer) return;

  let biChatVoiceEnabled = localStorage.getItem("bi_chat_voice") !== "false";
  let biChatActiveCategory = "";
  let biActiveSpeechRec = null;
  let isSending = false;

  function formatTime(d) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  const defaultGreeting = {
    role: "assistant",
    content:
      "### 🙏 Namaste! Welcome to Beyond Identity\n\n" +
      "I am your 24/7 Assistant. How are you doing today?\n\n" +
      "Please choose an option below or type your question:\n\n" +
      "1️⃣ 💼 **Jobs & Employment** — Find verified trans-inclusive jobs & career opportunities\n" +
      "2️⃣ 🏠 **Housing & Shelters** — Safe rental housing & Garima Greh transit shelters\n" +
      "3️⃣ 🩺 **Healthcare & HRT** — Hormone therapy roadmap & Ayushman Bharat ₹5L coverage\n" +
      "4️⃣ ⚖️ **Legal Rights** — TG Act 2019 protections, Certificate of Identity & free legal aid\n" +
      "5️⃣ 🚨 **Crisis & Helplines** — 24/7 Community Crisis Helpline (868989330)",
    suggestions: [],
    suggested_prompts: [
      "💼 Find Verified Jobs",
      "🏠 Safe Housing & Transit Shelters",
      "🩺 Healthcare & HRT Guidance",
      "⚖️ Know My Legal Rights",
      "🚨 24/7 Crisis Helpline (868989330)",
    ],
    timestamp: formatTime(new Date()),
  };

  let biChatHistory = [defaultGreeting];

  function updateVoiceIcon() {
    if (!voiceToggle) return;
    const label = document.getElementById("bi-chat-voice-label");
    const icon = document.getElementById("bi-chat-voice-icon");
    if (biChatVoiceEnabled) {
      if (icon) icon.innerText = "🌸";
      if (label) label.innerText = "Voice: ON";
      voiceToggle.title = "Sweet Female Voice is ON. Click to mute.";
      voiceToggle.classList.add("active");
    } else {
      if (icon) icon.innerText = "🔇";
      if (label) label.innerText = "Voice: OFF";
      voiceToggle.title = "Audio speech is OFF. Click to turn audio ON.";
      voiceToggle.classList.remove("active");
    }
  }

  function toggleVoice() {
    biChatVoiceEnabled = !biChatVoiceEnabled;
    localStorage.setItem("bi_chat_voice", biChatVoiceEnabled ? "true" : "false");
    updateVoiceIcon();
    if (!biChatVoiceEnabled) {
      SweetVoiceEngine.stop();
    }
  }

  function speakText(text) {
    if (!("speechSynthesis" in window) || !biChatVoiceEnabled) return;
    if (!text) return;
    SweetVoiceEngine.speak(text);
  }

  function openChatbox() {
    windowEl.classList.add("active");
    launcher.style.transform = "scale(0.9)";
    if (teaser) teaser.style.display = "none";
    sessionStorage.setItem("bi_teaser_dismissed", "true");
    setTimeout(() => {
      if (input) input.focus();
    }, 150);
    renderChatMessages();
  }

  function closeChatbox() {
    windowEl.classList.remove("active");
    launcher.style.transform = "";
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    stopMicListening();
  }

  function toggleChatbox() {
    if (windowEl.classList.contains("active")) {
      closeChatbox();
    } else {
      openChatbox();
    }
  }

  // Teaser dismiss logic
  if (sessionStorage.getItem("bi_teaser_dismissed") === "true") {
    if (teaser) teaser.style.display = "none";
  }
  if (teaserClose && teaser) {
    teaserClose.addEventListener("click", (e) => {
      e.stopPropagation();
      teaser.style.display = "none";
      sessionStorage.setItem("bi_teaser_dismissed", "true");
    });
  }

  // Markdown Parser
  function parseMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Headers
    html = html.replace(/### (.*?)(<br\/>|\n|$)/g, "<h4>$1</h4>");
    html = html.replace(/#### (.*?)(<br\/>|\n|$)/g, "<h5>$1</h5>");

    // Bold & Italics
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Markdown Links [text](url)
    html = html.replace(
      /\[(.*?)\]\((.*?)\)/g,
      `<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>`
    );

    // Linebreaks
    html = html.replace(/\n/g, "<br/>");

    // Clean up br tags right after h4/h5
    html = html.replace(/<\/h4><br\/>/g, "</h4>");
    html = html.replace(/<\/h5><br\/>/g, "</h5>");

    return html;
  }

  // Render Messages
  function renderChatMessages() {
    messagesContainer.innerHTML = "";

    biChatHistory.forEach((msg, idx) => {
      const isUser = msg.role === "user";
      const row = document.createElement("div");
      row.className = `bi-chat-row ${isUser ? "user" : "assistant"}`;

      if (!isUser) {
        const avatar = document.createElement("div");
        avatar.className = "bi-chat-avatar";
        avatar.innerText = "🤖";
        row.appendChild(avatar);
      }

      const bubbleWrap = document.createElement("div");
      bubbleWrap.className = "bi-chat-bubble-wrap";

      const bubble = document.createElement("div");
      bubble.className = "bi-chat-bubble";
      bubble.innerHTML = isUser ? escapeHtml(msg.content) : parseMarkdown(msg.content);

      // Suggestions from Database
      if (!isUser && msg.suggestions && msg.suggestions.length > 0) {
        const grid = document.createElement("div");
        grid.className = "bi-chat-suggestions-grid";

        msg.suggestions.forEach((item) => {
          const card = document.createElement("div");
          card.className = "bi-chat-card";
          card.innerHTML = `
            <div class="bi-chat-card-top">
              <span class="bi-chat-card-title">${escapeHtml(item.title)}</span>
              <span class="bi-chat-card-badge">${escapeHtml(item.category || "Verified")}</span>
            </div>
            <div class="bi-chat-card-meta">
              <span>🏛️ ${escapeHtml(item.organization_name || "Verified Org")}</span>
              <span>📍 ${escapeHtml(item.location || "Pan-India")}</span>
            </div>
            ${item.contact_info ? `<div class="bi-chat-card-contact">📞 ${escapeHtml(item.contact_info)}</div>` : ""}
          `;
          grid.appendChild(card);
        });
        bubble.appendChild(grid);
      }

      // Action Buttons (Listen Aloud & Copy)
      if (!isUser) {
        const actions = document.createElement("div");
        actions.className = "bi-chat-actions";

        const listenBtn = document.createElement("button");
        listenBtn.type = "button";
        listenBtn.className = "bi-chat-action-btn bi-chat-audio-btn";
        listenBtn.innerHTML = "<span>🔊</span> Play Audio";
        listenBtn.title = "Play this response aloud (Audio ON)";
        listenBtn.onclick = () => {
          biChatVoiceEnabled = true;
          localStorage.setItem("bi_chat_voice", "true");
          updateVoiceIcon();
          speakText(msg.content);
        };
        actions.appendChild(listenBtn);

        const stopBtn = document.createElement("button");
        stopBtn.type = "button";
        stopBtn.className = "bi-chat-action-btn bi-chat-stop-btn";
        stopBtn.innerHTML = "<span>⏹️</span> Stop Audio";
        stopBtn.title = "Stop Audio Speech";
        stopBtn.onclick = () => {
          if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
          }
        };
        actions.appendChild(stopBtn);

        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "bi-chat-action-btn";
        copyBtn.innerHTML = "<span>📋</span> Copy";
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(msg.content);
          copyBtn.innerHTML = "<span>✓</span> Copied";
          setTimeout(() => (copyBtn.innerHTML = "<span>📋</span> Copy"), 1500);
        };
        actions.appendChild(copyBtn);

        bubbleWrap.appendChild(bubble);
        bubbleWrap.appendChild(actions);

        // Suggested Prompt Chips (only on latest assistant message)
        if (idx === biChatHistory.length - 1 && msg.suggested_prompts && msg.suggested_prompts.length > 0) {
          const promptsWrap = document.createElement("div");
          promptsWrap.className = "bi-chat-prompts-wrap";

          msg.suggested_prompts.forEach((p) => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "bi-chat-prompt-chip";
            chip.innerHTML = `<span>${escapeHtml(p)}</span> <span>→</span>`;
            chip.onclick = () => {
              sendMessage(p);
            };
            promptsWrap.appendChild(chip);
          });
          bubbleWrap.appendChild(promptsWrap);
        }
      } else {
        bubbleWrap.appendChild(bubble);
      }

      row.appendChild(bubbleWrap);
      messagesContainer.appendChild(row);
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Send Message Logic
  async function sendMessage(text) {
    if (!text || !text.trim() || isSending) return;
    const cleanText = text.trim();
    if (input) input.value = "";

    isSending = true;

    // Push User message
    biChatHistory.push({
      role: "user",
      content: cleanText,
      timestamp: formatTime(new Date()),
    });
    renderChatMessages();

    // Show typing indicator
    const typingIndicator = document.createElement("div");
    typingIndicator.className = "bi-chat-row assistant";
    typingIndicator.id = "bi-chat-typing-indicator";
    typingIndicator.innerHTML = `
      <div class="bi-chat-avatar">🤖</div>
      <div class="bi-chat-bubble-wrap">
        <div class="bi-chat-typing">
          <div class="bi-typing-dots">
            <span class="bi-typing-dot"></span>
            <span class="bi-typing-dot"></span>
            <span class="bi-typing-dot"></span>
          </div>
          <span>Consulting live database & legal statutes...</span>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingIndicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
      const historyPayload = biChatHistory
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const headers = { "Content-Type": "application/json" };
      if (currentAuthToken) {
        headers["Authorization"] = `Bearer ${currentAuthToken}`;
      }

      const res = await fetch(`${API_BASE}/chatbot/query`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          query: cleanText,
          history: historyPayload,
          category_filter: biChatActiveCategory || null,
        }),
      });

      const loader = document.getElementById("bi-chat-typing-indicator");
      if (loader) loader.remove();

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Server error communicating with assistant");
      }

      const data = await res.json();

      biChatHistory.push({
        role: "assistant",
        content: data.reply,
        suggestions: data.suggestions || [],
        suggested_prompts: data.suggested_prompts || [],
        timestamp: formatTime(new Date()),
      });

      renderChatMessages();

      if (biChatVoiceEnabled) {
        speakText(data.reply);
      }
    } catch (err) {
      const loader = document.getElementById("bi-chat-typing-indicator");
      if (loader) loader.remove();

      biChatHistory.push({
        role: "assistant",
        content:
          `⚠️ **Unable to complete consultation:** ${escapeHtml(err.message)}.\n\n` +
          `If this is an emergency, please call the 24x7 Helpline immediately: [**868989330**](tel:868989330) or Tele-MANAS [**14416**](tel:14416).`,
        suggestions: [],
        suggested_prompts: ["Retry query", "Call 24/7 Helpline: 868989330"],
        timestamp: formatTime(new Date()),
      });
      renderChatMessages();
    } finally {
      isSending = false;
      if (input) input.focus();
    }
  }

  // Clear Chat History
  function clearChat() {
    biChatHistory = [defaultGreeting];
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    renderChatMessages();
    if (input) input.focus();
  }

  // Speech-to-Text Microphone
  function startMicListening() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Voice recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }

    try {
      biActiveSpeechRec = new SpeechRec();
      biActiveSpeechRec.lang = "en-IN";
      biActiveSpeechRec.continuous = false;
      biActiveSpeechRec.interimResults = false;

      biActiveSpeechRec.onstart = () => {
        if (micBtn) {
          micBtn.classList.add("listening");
          micBtn.innerText = "🔴";
        }
        if (input) input.placeholder = "Listening... Speak your question now";
      };

      biActiveSpeechRec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (transcript) {
          if (input) input.value = transcript;
          sendMessage(transcript);
        }
      };

      biActiveSpeechRec.onerror = () => {
        stopMicListening();
      };

      biActiveSpeechRec.onend = () => {
        stopMicListening();
      };

      biActiveSpeechRec.start();
    } catch (e) {
      stopMicListening();
    }
  }

  function stopMicListening() {
    if (micBtn) {
      micBtn.classList.remove("listening");
      micBtn.innerText = "🎙️";
    }
    if (input) input.placeholder = "Ask about rights, jobs, HRT, shelters...";
    if (biActiveSpeechRec) {
      try {
        biActiveSpeechRec.stop();
      } catch (e) {}
      biActiveSpeechRec = null;
    }
  }

  // Category Chip Filtering
  if (categoryBar) {
    categoryBar.querySelectorAll(".bi-chat-cat-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        categoryBar.querySelectorAll(".bi-chat-cat-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        biChatActiveCategory = chip.getAttribute("data-cat") || "";
        const catLabel = chip.innerText.trim();
        if (biChatActiveCategory) {
          sendMessage(`Show me verified ${catLabel} resources and rights`);
        }
      });
    });
  }

  // Event Listeners for floating widget
  launcher.addEventListener("click", toggleChatbox);
  if (closeBtn) closeBtn.addEventListener("click", closeChatbox);
  if (clearBtn) clearBtn.addEventListener("click", clearChat);
  if (voiceToggle) voiceToggle.addEventListener("click", toggleVoice);
  const biStopBtn = document.getElementById("bi-chat-stop-btn");
  if (biStopBtn) {
    biStopBtn.addEventListener("click", () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    });
  }

  if (sendBtn && input) {
    sendBtn.addEventListener("click", () => sendMessage(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input.value);
      }
    });
  }

  if (micBtn) {
    micBtn.addEventListener("click", () => {
      if (micBtn.classList.contains("listening")) {
        stopMicListening();
      } else {
        startMicListening();
      }
    });
  }

  updateVoiceIcon();
  renderChatMessages();
}

// ==========================================================================
// Dedicated Full-Width Talking Chat Box Tab Controller (#tab-chat)
// ==========================================================================
function initTabChatbox() {
  const container = document.getElementById("tab-chat");
  const messagesContainer = document.getElementById("tab-chat-messages-container");
  const input = document.getElementById("tab-chat-text-input");
  const sendBtn = document.getElementById("tab-chat-send-btn");
  const micBtn = document.getElementById("tab-chat-mic-btn");
  const micIcon = document.getElementById("tab-chat-mic-icon");
  const voiceToggle = document.getElementById("tab-chat-voice-toggle");
  const voiceIcon = document.getElementById("tab-chat-voice-icon");
  const voiceLabel = document.getElementById("tab-chat-voice-label");
  const clearBtn = document.getElementById("tab-chat-clear-btn");
  const categoryBar = document.getElementById("tab-chat-category-bar");
  const starterPrompts = document.getElementById("tab-chat-starter-prompts");

  // Talking Status & Visualizer Elements
  const avatarBox = document.getElementById("tab-chat-avatar-box");
  const statusDot = document.getElementById("tab-chat-status-dot");
  const liveBadge = document.getElementById("tab-chat-live-badge");
  const speakingBadge = document.getElementById("tab-chat-speaking-badge");
  const badgeStopBtn = document.getElementById("tab-chat-badge-stop-btn");
  const stopSpeakingBtn = document.getElementById("tab-chat-stop-speaking-btn");

  if (!container || !messagesContainer || !input) return;

  let tabVoiceEnabled = localStorage.getItem("bi_tab_voice") !== "false";
  let tabActiveCategory = "";
  let tabSpeechRec = null;
  let isSending = false;
  let activeSpeakingRow = null;

  function formatTime(d) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  const defaultGreeting = {
    role: "assistant",
    content: "🙏 Namaste! I'm Beyond Identity — a verified platform where you get trustworthy information about transgender rights, healthcare, and opportunities.",
    suggestions: [],
    suggested_prompts: [],
    timestamp: formatTime(new Date()),
  };

  let tabChatHistory = [defaultGreeting];

  function updateVoiceUI() {
    if (!voiceToggle) return;
    if (tabVoiceEnabled) {
      if (voiceIcon) voiceIcon.innerText = "🌸";
      if (voiceLabel) voiceLabel.innerText = "Voice: ON";
      voiceToggle.title = "Sweet Female Voice is ON. Click to mute.";
      voiceToggle.classList.add("active");
    } else {
      if (voiceIcon) voiceIcon.innerText = "🔇";
      if (voiceLabel) voiceLabel.innerText = "Voice: OFF";
      voiceToggle.title = "Audio speech is OFF. Click to unmute and turn audio ON.";
      voiceToggle.classList.remove("active");
      stopSpeech();
    }
  }

  function toggleVoice() {
    tabVoiceEnabled = !tabVoiceEnabled;
    localStorage.setItem("bi_tab_voice", tabVoiceEnabled ? "true" : "false");
    updateVoiceUI();
  }

  function stopSpeech() {
    SweetVoiceEngine.stop();
    if (avatarBox) avatarBox.classList.remove("is-talking");
    if (speakingBadge) speakingBadge.classList.remove("active");
    if (stopSpeakingBtn) {
      stopSpeakingBtn.classList.remove("is-active-speaking");
      const label = stopSpeakingBtn.querySelector(".tab-chat-btn-text");
      if (label) label.innerText = "Stop Audio";
    }
    if (liveBadge) liveBadge.innerText = "🟢 Online";
    document.querySelectorAll(".tab-chat-row.speaking-now").forEach((r) => r.classList.remove("speaking-now"));
    document.querySelectorAll(".tab-chat-speaking-indicator-mini").forEach((ind) => ind.remove());
    activeSpeakingRow = null;
  }

  function speakText(text, rowElement) {
    if (!("speechSynthesis" in window) || !tabVoiceEnabled) return;
    stopSpeech();
    if (!text) return;

    SweetVoiceEngine.speak(text, {
      onstart: () => {
        if (avatarBox) avatarBox.classList.add("is-talking");
        if (speakingBadge) speakingBadge.classList.add("active");
        if (stopSpeakingBtn) {
          stopSpeakingBtn.classList.add("is-active-speaking");
          const label = stopSpeakingBtn.querySelector(".tab-chat-btn-text");
          if (label) label.innerText = "Stop Audio (Playing)";
        }
        if (liveBadge) liveBadge.innerText = "🌸 Speaking...";

        if (rowElement) {
          activeSpeakingRow = rowElement;
          rowElement.classList.add("speaking-now");
          const actionsRow = rowElement.querySelector(".tab-chat-actions-row");
          if (actionsRow && !actionsRow.querySelector(".tab-chat-speaking-indicator-mini")) {
            const mini = document.createElement("div");
            mini.className = "tab-chat-speaking-indicator-mini";
            mini.innerHTML = `
              <div class="voice-waves animating">
                <span class="voice-wave-bar"></span>
                <span class="voice-wave-bar"></span>
                <span class="voice-wave-bar"></span>
              </div>
              <span>Speaking with sweet girl voice...</span>
            `;
            actionsRow.appendChild(mini);
          }
        }
      },
      onend: () => {
        stopSpeech();
      },
      onerror: () => {
        stopSpeech();
      }
    });
  }

  // Voice Picker Dropdown Controls
  const voicePickerBtn = document.getElementById("tab-chat-voice-picker-btn");
  const voiceDropdown = document.getElementById("tab-chat-voice-dropdown");
  const voiceSelect = document.getElementById("tab-chat-voice-select");
  const voiceToneSelect = document.getElementById("tab-chat-tone-select");
  const voiceTestBtn = document.getElementById("tab-chat-voice-test-btn");
  const voiceCloseBtn = document.getElementById("tab-chat-voice-close-btn");
  const voiceDetectedName = document.getElementById("voice-detected-name");

  function refreshVoiceUI() {
    const v = SweetVoiceEngine.getSweetFemaleVoice();
    if (voiceDetectedName) {
      voiceDetectedName.textContent = v ? `${v.name} (${v.lang})` : "Default Female Voice";
    }
  }

  if (voicePickerBtn && voiceDropdown) {
    voicePickerBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = voiceDropdown.style.display !== "none";
      voiceDropdown.style.display = isVisible ? "none" : "block";
      if (!isVisible) refreshVoiceUI();
    });

    if (voiceCloseBtn) {
      voiceCloseBtn.addEventListener("click", () => {
        voiceDropdown.style.display = "none";
      });
    }

    if (voiceSelect) {
      voiceSelect.value = SweetVoiceEngine.currentProfile || "sweet";
      voiceSelect.addEventListener("change", (e) => {
        SweetVoiceEngine.setProfile(e.target.value);
        refreshVoiceUI();
      });
    }

    if (voiceTestBtn) {
      voiceTestBtn.addEventListener("click", () => {
        SweetVoiceEngine.testVoice();
      });
    }

    document.addEventListener("click", (e) => {
      if (voiceDropdown && !voiceDropdown.contains(e.target) && e.target !== voicePickerBtn && !voicePickerBtn.contains(e.target)) {
        voiceDropdown.style.display = "none";
      }
    });

    SweetVoiceEngine.onVoicesLoaded(() => refreshVoiceUI());
  }

  // Global post-login vocal greeting trigger
  window.triggerPostLoginChatGreeting = function(user) {
    if (!user) return;
    switchToTab("tab-chat");

    const welcomeGreeting = {
      role: "assistant",
      content:
        `### 🙏 Namaste ${user.name}! Welcome to Beyond Identity\n\n` +
        `I am your **24/7 Rights and Healthcare Assistant**. How are you doing today?\n\n` +
        `Please choose an option below or type what you need:\n\n` +
        `1️⃣ 💼 **Jobs & Employment** — Find verified inclusive job openings\n` +
        `2️⃣ 🏠 **Housing & Shelters** — Safe rental housing & Garima Greh transit shelters\n` +
        `3️⃣ 🩺 **Healthcare & HRT** — Hormone therapy roadmap & Ayushman Bharat ₹5L coverage\n` +
        `4️⃣ ⚖️ **Legal Rights** — TG Act 2019 protections, Certificate of Identity & free legal aid\n` +
        `5️⃣ 🚨 **Crisis & Helplines** — 24/7 Community Crisis Helpline (868989330)\n\n` +
        `🎙️ **Voice Assistant Active:** Click the microphone or type below to talk with me!`,
      isPostLogin: true,
      suggestions: [],
      suggested_prompts: [
        "💼 Find Verified Jobs",
        "🏠 Safe Housing & Transit Shelters",
        "🩺 Healthcare & HRT Guidance",
        "⚖️ Know My Legal Rights",
        "🚨 24/7 Crisis Helpline (868989330)",
      ],
      timestamp: formatTime(new Date()),
    };

    // Replace generic initial greeting or append
    if (tabChatHistory.length <= 1) {
      tabChatHistory = [welcomeGreeting];
    } else {
      tabChatHistory.push(welcomeGreeting);
    }

    renderMessages();

    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    if (input) input.focus();

    // Vocal Speech Greeting
    if (tabVoiceEnabled && "speechSynthesis" in window) {
      const speechGreeting = `Namaste ${user.name}! Welcome to Beyond Identity. I am your 24/7 assistant. I can guide you through statutory legal rights, verified housing, jobs, and healthcare. Feel free to talk with me anytime by clicking the microphone or typing below.`;
      setTimeout(() => {
        const rows = messagesContainer.querySelectorAll(".tab-chat-row.assistant");
        const lastRow = rows[rows.length - 1];
        speakText(speechGreeting, lastRow);
      }, 550);
    }
  };
  window.triggerPostLoginAIChatGreeting = window.triggerPostLoginChatGreeting;

  function parseMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Headers
    html = html.replace(/### (.*?)(<br\/>|\n|$)/g, "<h4>$1</h4>");
    html = html.replace(/#### (.*?)(<br\/>|\n|$)/g, "<h5>$1</h5>");

    // Bold & Italics
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Markdown Links [text](url)
    html = html.replace(
      /\[(.*?)\]\((.*?)\)/g,
      `<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>`
    );

    // Linebreaks
    html = html.replace(/\n/g, "<br/>");
    html = html.replace(/<\/h4><br\/>/g, "</h4>");
    html = html.replace(/<\/h5><br\/>/g, "</h5>");

    return html;
  }

  function renderMessages() {
    messagesContainer.innerHTML = "";

    tabChatHistory.forEach((msg, idx) => {
      const isUser = msg.role === "user";
      const row = document.createElement("div");
      row.className = `tab-chat-row ${isUser ? "user" : "assistant"}`;

      if (!isUser) {
        const avatar = document.createElement("div");
        avatar.className = "tab-chat-msg-avatar";
        avatar.innerText = "🤖";
        row.appendChild(avatar);
      }

      const bubbleWrap = document.createElement("div");
      bubbleWrap.className = "tab-chat-bubble-wrap";

      const bubble = document.createElement("div");
      bubble.className = "tab-chat-bubble";

      // If this is the special post-login greeting, show the Welcome Banner
      if (!isUser && msg.isPostLogin) {
        const bannerCard = document.createElement("div");
        bannerCard.className = "post-login-welcome-banner";
        bannerCard.innerHTML = `
          <div class="post-login-welcome-left">
            <div class="post-login-welcome-avatar">🤖</div>
            <div>
              <div class="post-login-welcome-title">Assistant Connected for ${escapeHtml(currentUser?.name || "Member")}</div>
              <div class="post-login-welcome-sub">Voice Speech Active • Verified Indian Statutory Knowledge Base</div>
            </div>
          </div>
          <button type="button" class="post-login-talk-cta-btn" id="post-login-mic-cta-${idx}">
            <span>🎙️</span> Click to Speak Question
          </button>
        `;
        const micCta = bannerCard.querySelector(`#post-login-mic-cta-${idx}`);
        if (micCta) {
          micCta.onclick = () => {
            if (micBtn.classList.contains("listening")) {
              stopMic();
            } else {
              startMic();
            }
          };
        }
        bubble.appendChild(bannerCard);
      }

      // Always showcase the affirming light artwork inside the initial chatbot bubble
      if (!isUser && idx === 0) {
        const artCard = document.createElement("div");
        artCard.className = "tab-chat-art-welcome-card";
        artCard.innerHTML = `
          <div class="tab-chat-art-thumb-wrap">
            <img src="/static/assets/chatbot-watermark.jpg" alt="Beyond Identity Sacred Light" class="tab-chat-art-thumb" />
          </div>
          <div class="tab-chat-art-details">
            <span class="tab-chat-art-badge">🌈 Safe, Verified &amp; Welcoming Sanctuary</span>
            <h4 class="tab-chat-art-title">Welcome to Beyond Identity 24/7 Sanctuary</h4>
            <p class="tab-chat-art-text">Your safe, affirming portal for statutory Indian transgender rights, Garima Greh housing shelters, verified inclusive jobs, and PM-JAY Ayushman Bharat healthcare.</p>
          </div>
        `;
        bubble.appendChild(artCard);
      }

      const bodyDiv = document.createElement("div");
      bodyDiv.innerHTML = isUser ? escapeHtml(msg.content) : parseMarkdown(msg.content);
      bubble.appendChild(bodyDiv);

      // Suggestions from database
      if (!isUser && msg.suggestions && msg.suggestions.length > 0) {
        const grid = document.createElement("div");
        grid.className = "tab-chat-db-grid";

        msg.suggestions.forEach((item) => {
          const card = document.createElement("div");
          card.className = "tab-chat-db-card";
          card.innerHTML = `
            <div class="tab-chat-db-card-top">
              <span class="tab-chat-db-card-title">${escapeHtml(item.title)}</span>
              <span class="tab-chat-db-card-badge">${escapeHtml(item.category || "Verified")}</span>
            </div>
            <div class="tab-chat-db-card-meta">
              <span>🏛️ ${escapeHtml(item.organization_name || "Verified Provider")}</span>
              <span>📍 ${escapeHtml(item.location || "Pan-India")}</span>
            </div>
            ${item.contact_info ? `<div class="tab-chat-db-card-contact">📞 ${escapeHtml(item.contact_info)}</div>` : ""}
          `;
          grid.appendChild(card);
        });
        bubble.appendChild(grid);
      }

      bubbleWrap.appendChild(bubble);

      // Actions & Prompts for Assistant messages
      if (!isUser) {
        const actionsRow = document.createElement("div");
        actionsRow.className = "tab-chat-actions-row";

        const listenBtn = document.createElement("button");
        listenBtn.type = "button";
        listenBtn.className = "tab-chat-action-btn tab-chat-play-audio-btn";
        listenBtn.innerHTML = "<span>🔊</span> Play Audio";
        listenBtn.title = "Play this response aloud (Audio ON)";
        listenBtn.onclick = () => {
          tabVoiceEnabled = true;
          localStorage.setItem("bi_tab_voice", "true");
          updateVoiceUI();
          speakText(msg.content, row);
        };
        actionsRow.appendChild(listenBtn);

        const stopBtn = document.createElement("button");
        stopBtn.type = "button";
        stopBtn.className = "tab-chat-action-btn tab-chat-stop-btn";
        stopBtn.innerHTML = "<span>⏹️</span> Stop Audio";
        stopBtn.title = "Stop Audio Speech";
        stopBtn.onclick = () => {
          stopSpeech();
        };
        actionsRow.appendChild(stopBtn);

        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "tab-chat-action-btn";
        copyBtn.innerHTML = "<span>📋</span> Copy";
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(msg.content);
          copyBtn.innerHTML = "<span>✓</span> Copied";
          setTimeout(() => (copyBtn.innerHTML = "<span>📋</span> Copy"), 1500);
        };
        actionsRow.appendChild(copyBtn);

        bubbleWrap.appendChild(actionsRow);

        // Suggested Follow-up Prompts (Only on the last message)
        if (idx === tabChatHistory.length - 1 && msg.suggested_prompts && msg.suggested_prompts.length > 0) {
          const promptsWrap = document.createElement("div");
          promptsWrap.className = "tab-chat-bubble-prompts";

          msg.suggested_prompts.forEach((p) => {
            const pBtn = document.createElement("button");
            pBtn.type = "button";
            pBtn.className = "tab-chat-bubble-prompt-btn";
            pBtn.innerHTML = `<span>${escapeHtml(p)}</span> <span>→</span>`;
            pBtn.onclick = () => sendTabMessage(p);
            promptsWrap.appendChild(pBtn);
          });
          bubbleWrap.appendChild(promptsWrap);
        }
      }

      if (isUser) {
        const userAvatar = document.createElement("div");
        userAvatar.className = "tab-chat-msg-avatar";
        userAvatar.innerText = "👤";
        row.appendChild(bubbleWrap);
        row.appendChild(userAvatar);
      } else {
        row.appendChild(bubbleWrap);
      }

      messagesContainer.appendChild(row);
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  async function sendTabMessage(text) {
    if (!text || !text.trim() || isSending) return;
    const cleanText = text.trim();
    if (input) input.value = "";

    isSending = true;
    stopSpeech();

    const starterContainer = document.getElementById("tab-chat-quick-prompts-container");
    if (starterContainer) {
      starterContainer.style.display = "none";
    }

    tabChatHistory.push({
      role: "user",
      content: cleanText,
      timestamp: formatTime(new Date()),
    });
    renderMessages();

    // Show typing indicator
    const typingRow = document.createElement("div");
    typingRow.className = "tab-chat-row assistant";
    typingRow.id = "tab-chat-typing-indicator";
    typingRow.innerHTML = `
      <div class="tab-chat-msg-avatar">🤖</div>
      <div class="tab-chat-bubble-wrap">
        <div class="tab-chat-typing-box">
          <div class="tab-chat-typing-dots">
            <span class="tab-chat-typing-dot"></span>
            <span class="tab-chat-typing-dot"></span>
            <span class="tab-chat-typing-dot"></span>
          </div>
          <span>Consulting Indian statutory statutes & verified database...</span>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingRow);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
      const historyPayload = tabChatHistory
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const headers = { "Content-Type": "application/json" };
      if (currentAuthToken) {
        headers["Authorization"] = `Bearer ${currentAuthToken}`;
      }

      const res = await fetch(`${API_BASE}/chatbot/query`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          query: cleanText,
          history: historyPayload,
          category_filter: tabActiveCategory || null,
        }),
      });

      const loader = document.getElementById("tab-chat-typing-indicator");
      if (loader) loader.remove();

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Server error communicating with assistant");
      }

      const data = await res.json();

      tabChatHistory.push({
        role: "assistant",
        content: data.reply,
        suggestions: data.suggestions || [],
        suggested_prompts: data.suggested_prompts || [],
        timestamp: formatTime(new Date()),
      });

      renderMessages();

      // Talk aloud the answer!
      if (tabVoiceEnabled) {
        const rows = messagesContainer.querySelectorAll(".tab-chat-row.assistant");
        const lastRow = rows[rows.length - 1];
        speakText(data.reply, lastRow);
      }
    } catch (err) {
      const loader = document.getElementById("tab-chat-typing-indicator");
      if (loader) loader.remove();

      tabChatHistory.push({
        role: "assistant",
        content:
          `⚠️ **Unable to complete consultation:** ${escapeHtml(err.message)}.\n\n` +
          `If this is an emergency, please call the 24x7 Helpline immediately: [**868989330**](tel:868989330) or Tele-MANAS [**14416**](tel:14416).`,
        suggestions: [],
        suggested_prompts: ["Retry query", "Call 24/7 Helpline: 868989330"],
        timestamp: formatTime(new Date()),
      });
      renderMessages();
    } finally {
      isSending = false;
      if (input) input.focus();
    }
  }

  function clearChat() {
    stopSpeech();
    tabChatHistory = [defaultGreeting];
    renderMessages();
    const starterContainer = document.getElementById("tab-chat-quick-prompts-container");
    if (starterContainer) {
      starterContainer.style.display = "";
    }
    if (input) input.focus();
  }

  function startMic() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Voice speech recognition is not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    stopSpeech();

    try {
      tabSpeechRec = new SpeechRec();
      tabSpeechRec.lang = "en-IN";
      tabSpeechRec.continuous = false;
      tabSpeechRec.interimResults = false;

      tabSpeechRec.onstart = () => {
        if (micBtn) {
          micBtn.classList.add("listening");
        }
        if (liveBadge) liveBadge.innerText = "🎙️ Listening to You...";
        if (input) input.placeholder = "Listening... Speak your question now";
      };

      tabSpeechRec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (transcript) {
          if (input) input.value = transcript;
          sendTabMessage(transcript);
        }
      };

      tabSpeechRec.onerror = () => stopMic();
      tabSpeechRec.onend = () => stopMic();

      tabSpeechRec.start();
    } catch (e) {
      stopMic();
    }
  }

  function stopMic() {
    if (micBtn) {
      micBtn.classList.remove("listening");
    }
    if (liveBadge) liveBadge.innerText = "🟢 Online";
    if (input) input.placeholder = "Ask anything about legal rights, inclusive jobs, Garima Greh shelters, HRT protocols...";
    if (tabSpeechRec) {
      try { tabSpeechRec.stop(); } catch (e) {}
      tabSpeechRec = null;
    }
  }

  // Category filter buttons
  if (categoryBar) {
    categoryBar.querySelectorAll(".tab-chat-cat-btn").forEach((chip) => {
      chip.addEventListener("click", () => {
        categoryBar.querySelectorAll(".tab-chat-cat-btn").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        tabActiveCategory = chip.getAttribute("data-cat") || "";
        const catLabel = chip.innerText.trim();
        if (tabActiveCategory) {
          sendTabMessage(`Show verified ${catLabel} opportunities, resources and legal rights`);
        }
      });
    });
  }

  // Starter quick questions
  if (starterPrompts) {
    starterPrompts.querySelectorAll(".tab-chat-starter-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const promptText = chip.getAttribute("data-prompt") || chip.innerText.trim();
        sendTabMessage(promptText);
      });
    });
  }

  // Quick prompt pills above input bar
  const quickQueryPills = document.getElementById("tab-chat-quick-query-pills");
  if (quickQueryPills) {
    quickQueryPills.querySelectorAll(".tab-chat-quick-query-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        const promptText = pill.getAttribute("data-prompt") || pill.innerText.trim();
        sendTabMessage(promptText);
      });
    });
  }

  // Event Listeners
  if (sendBtn && input) {
    sendBtn.addEventListener("click", () => sendTabMessage(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendTabMessage(input.value);
      }
    });
  }

  if (micBtn) {
    micBtn.addEventListener("click", () => {
      if (micBtn.classList.contains("listening")) {
        stopMic();
      } else {
        startMic();
      }
    });
  }

  if (voiceToggle) voiceToggle.addEventListener("click", toggleVoice);
  if (clearBtn) clearBtn.addEventListener("click", clearChat);
  if (badgeStopBtn) badgeStopBtn.addEventListener("click", stopSpeech);
  if (stopSpeakingBtn) stopSpeakingBtn.addEventListener("click", stopSpeech);

  const staticListen = container.querySelector(".tab-chat-static-listen-btn");
  if (staticListen) {
    staticListen.onclick = () => {
      tabVoiceEnabled = true;
      localStorage.setItem("bi_tab_voice", "true");
      updateVoiceUI();
      const firstRow = container.querySelector(".tab-chat-row.assistant");
      const heading = document.getElementById("tab-chat-initial-heading");
      const text = heading ? heading.parentElement.innerText : defaultGreeting.content;
      speakText(text, firstRow);
    };
  }
  const staticStop = container.querySelector(".tab-chat-static-stop-btn");
  if (staticStop) {
    staticStop.onclick = () => {
      stopSpeech();
    };
  }

  // Full Page Toggle Button for Chatbot (#tab-chat-fullscreen-btn)
  const fullscreenBtn = document.getElementById("tab-chat-fullscreen-btn");
  const fullscreenLabel = document.getElementById("tab-chat-fullscreen-label");
  const mainChatContainer = document.getElementById("tab-chat-main-container");

  function toggleChatFullscreen(forceState) {
    if (!mainChatContainer) return;
    const isNowFull = typeof forceState === "boolean"
      ? (forceState ? mainChatContainer.classList.add("full-page-mode") || true : (mainChatContainer.classList.remove("full-page-mode"), false))
      : mainChatContainer.classList.toggle("full-page-mode");

    document.body.classList.toggle("chatbot-fullscreen-active", isNowFull);

    if (fullscreenBtn) {
      if (isNowFull) {
        fullscreenBtn.classList.add("active");
        if (fullscreenLabel) fullscreenLabel.innerText = "Exit Full Page";
        showToast("🌈 Full-Page Chatbot Active • Press Esc to Exit", "info");
      } else {
        fullscreenBtn.classList.remove("active");
        if (fullscreenLabel) fullscreenLabel.innerText = "Full Page";
      }
    }

    setTimeout(() => {
      if (input) input.focus();
      if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 120);
  }

  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", () => toggleChatFullscreen());
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && mainChatContainer && mainChatContainer.classList.contains("full-page-mode")) {
      toggleChatFullscreen(false);
    }
  });

  // Buttons that navigate directly to the full-page chatbot
  const navBtn = document.getElementById("nav-open-chat-btn");
  const mobileNavBtn = document.getElementById("nav-mobile-chat-link");
  const heroBtn = document.getElementById("hero-open-chat-btn");
  const landingBtn = document.getElementById("landing-launch-chat-btn");
  const bannerBtn = document.getElementById("banner-open-chat-btn");

  [navBtn, mobileNavBtn, heroBtn, landingBtn, bannerBtn].forEach((btn) => {
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const drawer = document.getElementById("nav-mobile-drawer");
        if (drawer) drawer.classList.remove("active");
        switchToTab("tab-chat");
      });
    }
  });

  updateVoiceUI();
  renderMessages();
}

window.initAIChatbox = initChatbox;
window.initTabAIChatbox = initTabChatbox;

// =========================================================================
// LGBTQ+ Community Voices & Video Interviews System
// =========================================================================
let currentVideoCategory = "all";
let currentVideoSearchQuery = "";
let cachedVideoInterviews = [];

async function loadVideoInterviews(category = "", search = "") {
  const container = document.getElementById("video-interviews-container");
  if (!container) return;

  if (category) currentVideoCategory = category;
  if (typeof search === "string") currentVideoSearchQuery = search;

  container.innerHTML = `
    <div class="video-loading-state" style="grid-column: 1 / -1; text-align: center; padding: 40px 20px;">
      <div class="video-spinner" style="width: 38px; height: 38px; border: 3px solid rgba(99,102,241,0.2); border-top-color: var(--bi-primary, #6366f1); border-radius: 50%; margin: 0 auto 14px; animation: spin 0.8s linear infinite;"></div>
      <p style="color: var(--bi-text-muted, #94a3b8); font-size: 13.5px; margin: 0;">Loading authentic community video interviews...</p>
    </div>
  `;

  try {
    const params = new URLSearchParams();
    if (currentVideoCategory && currentVideoCategory !== "all") {
      params.append("category", currentVideoCategory);
    }
    if (currentVideoSearchQuery && currentVideoSearchQuery.trim()) {
      params.append("search", currentVideoSearchQuery.trim());
    }

    const url = `/api/videos${params.toString() ? "?" + params.toString() : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load video interviews");
    const videos = await res.json();
    cachedVideoInterviews = videos;

    if (!videos || videos.length === 0) {
      container.innerHTML = `
        <div class="video-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 50px 20px; background: var(--bi-surface-2, rgba(255,255,255,0.03)); border: 1px dashed var(--bi-border-subtle, rgba(255,255,255,0.12)); border-radius: 18px;">
          <div style="font-size: 42px; margin-bottom: 12px;">🎬</div>
          <h4 style="font-size: 17px; font-weight: 700; margin: 0 0 6px; color: var(--bi-text-main, #f8fafc);">No video interviews found</h4>
          <p style="color: var(--bi-text-muted, #94a3b8); font-size: 13.5px; max-width: 440px; margin: 0 auto 18px;">
            ${currentVideoSearchQuery ? `No videos matched "${escapeHtml(currentVideoSearchQuery)}". Try another topic or search term.` : 'Be the first to share an inspiring LGBTQ+ video interview, personal story, or workplace journey!'}
          </p>
          <button type="button" class="btn btn-primary" onclick="openPostVideoModal()" style="padding: 10px 22px; font-size: 13.5px;">
            <span>➕</span> <strong>Post Video Interview</strong>
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = videos.map((v) => renderVideoCard(v)).join("");
  } catch (err) {
    console.error("Error loading video interviews:", err);
    container.innerHTML = `
      <div class="video-error-state" style="grid-column: 1 / -1; text-align: center; padding: 36px 20px;">
        <p style="color: #f43f5e; font-size: 14px; margin-bottom: 12px;">⚠️ Unable to load video interviews right now.</p>
        <button type="button" class="btn btn-secondary" onclick="loadVideoInterviews()">Try Again</button>
      </div>
    `;
  }
}

function renderVideoCard(video) {
  const title = escapeHtml(video.title);
  const name = escapeHtml(video.interviewee_name);
  const tag = escapeHtml(video.identity_tag || "LGBTQ+ Community");
  const category = escapeHtml(video.category);
  const quote = video.key_quote ? escapeHtml(video.key_quote) : "";
  const desc = video.description ? escapeHtml(video.description) : "";
  const duration = escapeHtml(video.duration || "Phone Video");
  const location = video.location ? escapeHtml(video.location) : "";
  const extUrl = escapeHtml(video.video_url || "");
  const embedSrc = escapeHtml(video.embed_url || video.video_url || "");

  // Detect whether this is a direct uploaded phone video file or an external embed (YouTube/Vimeo)
  const rawUrl = (video.video_url || "").toLowerCase();
  const rawEmbed = (video.embed_url || "").toLowerCase();
  const isDirectPhoneVideo =
    rawUrl.startsWith("/static/") ||
    rawUrl.startsWith("blob:") ||
    rawEmbed.startsWith("/static/") ||
    /\.(mp4|mov|webm|m4v|3gp|avi|mkv)($|\?)/i.test(rawUrl) ||
    /\.(mp4|mov|webm|m4v|3gp|avi|mkv)($|\?)/i.test(rawEmbed) ||
    (!rawUrl.includes("youtube.com") && !rawUrl.includes("youtu.be") && !rawUrl.includes("vimeo.com") && rawUrl.includes("phone_video"));

  const playerMarkup = isDirectPhoneVideo
    ? `
      <div class="video-player-frame video-player-native-wrap">
        <video
          src="${embedSrc || extUrl}"
          controls
          playsinline
          preload="metadata"
          poster="${video.thumbnail_url && !video.thumbnail_url.includes('unsplash') ? escapeHtml(video.thumbnail_url) : ''}"
        >
          <source src="${embedSrc || extUrl}" type="video/mp4" />
          <source src="${embedSrc || extUrl}" type="video/webm" />
          <source src="${embedSrc || extUrl}" type="video/quicktime" />
          Your mobile browser does not support the video tag.
        </video>
      </div>
    `
    : `
      <div class="video-player-frame">
        <iframe
          src="${embedSrc}"
          title="${title}"
          frameborder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen
          loading="lazy"
        ></iframe>
      </div>
    `;

  return `
    <article class="video-interview-card" data-id="${video.id}">
      ${playerMarkup}
      <div class="video-card-body">
        <div class="video-card-chips">
          <span class="video-chip-category">${category}</span>
          ${isDirectPhoneVideo ? `<span class="video-chip-duration phone-video-badge">📱 Phone Video</span>` : ""}
          <span class="video-chip-duration">⏱️ ${duration}</span>
          ${location ? `<span class="video-chip-location">📍 ${location}</span>` : ""}
        </div>
        <h4 class="video-card-title">${title}</h4>
        <div class="video-interviewee-row">
          <div class="video-interviewee-avatar" title="${name}">👤</div>
          <div class="video-interviewee-details">
            <span class="video-interviewee-name">${name}</span>
            <span class="video-interviewee-tag">${tag}</span>
          </div>
        </div>
        ${quote ? `
          <blockquote class="video-card-quote">
            “${quote}”
          </blockquote>
        ` : ""}
        ${desc ? `<p class="video-card-description">${desc}</p>` : ""}
        <div class="video-card-footer">
          <span class="video-verified-badge">✓ Verified Voice</span>
          <a href="${extUrl}" target="_blank" rel="noopener noreferrer" class="video-open-external-btn" title="Open source video">
            <span>${isDirectPhoneVideo ? "Play / Download ↗" : "Watch External ↗"}</span>
          </a>
        </div>
      </div>
    </article>
  `;
}

let currentVideoSourceMode = "phone"; // "phone" | "link"

function resetPhoneVideoUploadState() {
  const fileInput = document.getElementById("vid-phone-file-input");
  const previewCard = document.getElementById("phone-video-preview-card");
  const previewPlayer = document.getElementById("phone-video-preview-player");
  const previewName = document.getElementById("phone-video-preview-name");
  const previewSize = document.getElementById("phone-video-preview-size");
  const dropzone = document.getElementById("phone-video-dropzone");

  if (fileInput) fileInput.value = "";
  if (previewPlayer) {
    if (previewPlayer.src && previewPlayer.src.startsWith("blob:")) {
      try { URL.revokeObjectURL(previewPlayer.src); } catch (e) {}
    }
    previewPlayer.src = "";
  }
  if (previewName) previewName.innerText = "video.mp4";
  if (previewSize) previewSize.innerText = "0 MB";
  if (previewCard) previewCard.style.display = "none";
  if (dropzone) dropzone.style.display = "block";
}

function setVideoSourceMode(mode) {
  currentVideoSourceMode = mode;
  const btnPhone = document.getElementById("btn-mode-phone-upload");
  const btnLink = document.getElementById("btn-mode-link-url");
  const phoneSection = document.getElementById("video-phone-upload-section");
  const linkSection = document.getElementById("video-link-section");

  if (mode === "phone") {
    if (btnPhone) {
      btnPhone.classList.add("active");
      btnPhone.style.background = "var(--bi-primary, #6366f1)";
      btnPhone.style.color = "#ffffff";
    }
    if (btnLink) {
      btnLink.classList.remove("active");
      btnLink.style.background = "transparent";
      btnLink.style.color = "var(--text-muted)";
    }
    if (phoneSection) phoneSection.style.display = "block";
    if (linkSection) linkSection.style.display = "none";
  } else {
    if (btnLink) {
      btnLink.classList.add("active");
      btnLink.style.background = "var(--bi-primary, #6366f1)";
      btnLink.style.color = "#ffffff";
    }
    if (btnPhone) {
      btnPhone.classList.remove("active");
      btnPhone.style.background = "transparent";
      btnPhone.style.color = "var(--text-muted)";
    }
    if (phoneSection) phoneSection.style.display = "none";
    if (linkSection) linkSection.style.display = "block";
  }
}

function handleSelectedVideoFile(file) {
  if (!file) return;

  const validExts = [".mp4", ".mov", ".webm", ".m4v", ".3gp", ".avi", ".mkv"];
  const fileName = (file.name || "").toLowerCase();
  const hasValidExt = validExts.some(ext => fileName.endsWith(ext));
  const isVideoMime = file.type && file.type.startsWith("video/");

  if (!hasValidExt && !isVideoMime) {
    showToast("Please choose a valid video format (MP4, MOV, WebM, 3GP)", "error");
    return;
  }

  const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
  const previewCard = document.getElementById("phone-video-preview-card");
  const previewPlayer = document.getElementById("phone-video-preview-player");
  const previewName = document.getElementById("phone-video-preview-name");
  const previewSize = document.getElementById("phone-video-preview-size");
  const dropzone = document.getElementById("phone-video-dropzone");

  if (previewPlayer) {
    if (previewPlayer.src && previewPlayer.src.startsWith("blob:")) {
      try { URL.revokeObjectURL(previewPlayer.src); } catch (e) {}
    }
    try {
      previewPlayer.src = URL.createObjectURL(file);
      previewPlayer.load();
    } catch (e) {
      console.warn("Could not create object URL for preview:", e);
    }
  }

  if (previewName) previewName.innerText = file.name || "phone_video.mp4";
  if (previewSize) previewSize.innerText = `${sizeMb} MB`;
  if (previewCard) previewCard.style.display = "flex";
  if (dropzone) dropzone.style.display = "none";

  showToast(`📱 Phone video ready: ${file.name || "video"} (${sizeMb} MB)`, "info");
}

function openPostVideoModal() {
  const modal = document.getElementById("post-video-modal");
  if (modal) {
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
    // Default to phone upload mode
    setVideoSourceMode("phone");
    const titleInput = document.getElementById("vid-title");
    if (titleInput) setTimeout(() => titleInput.focus(), 100);
  }
}

function closePostVideoModal() {
  const modal = document.getElementById("post-video-modal");
  if (modal) {
    modal.style.display = "none";
    document.body.style.overflow = "";
    resetPhoneVideoUploadState();
  }
}

function initVideoInterviews() {
  // Bind Open Modal Button
  const openBtn = document.getElementById("open-post-video-modal-btn");
  if (openBtn) {
    openBtn.addEventListener("click", openPostVideoModal);
  }

  // Bind Close Modal Buttons
  const closeBtn = document.getElementById("close-post-video-modal-btn");
  if (closeBtn) closeBtn.addEventListener("click", closePostVideoModal);
  const cancelBtn = document.getElementById("cancel-post-video-btn");
  if (cancelBtn) cancelBtn.addEventListener("click", closePostVideoModal);

  const modal = document.getElementById("post-video-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closePostVideoModal();
    });
  }

  // Source Mode Switcher Buttons
  const btnPhone = document.getElementById("btn-mode-phone-upload");
  if (btnPhone) {
    btnPhone.addEventListener("click", () => setVideoSourceMode("phone"));
  }
  const btnLink = document.getElementById("btn-mode-link-url");
  if (btnLink) {
    btnLink.addEventListener("click", () => setVideoSourceMode("link"));
  }

  // Phone Video File Input & Dropzone
  const phoneFileInput = document.getElementById("vid-phone-file-input");
  const phoneDropzone = document.getElementById("phone-video-dropzone");
  const removeVideoBtn = document.getElementById("remove-phone-video-btn");

  if (phoneDropzone && phoneFileInput) {
    phoneDropzone.addEventListener("click", () => {
      phoneFileInput.click();
    });

    phoneDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      phoneDropzone.classList.add("drag-over");
    });
    phoneDropzone.addEventListener("dragleave", () => {
      phoneDropzone.classList.remove("drag-over");
    });
    phoneDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      phoneDropzone.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        phoneFileInput.files = e.dataTransfer.files;
        handleSelectedVideoFile(e.dataTransfer.files[0]);
      }
    });
  }

  if (phoneFileInput) {
    phoneFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleSelectedVideoFile(e.target.files[0]);
      }
    });
  }

  if (removeVideoBtn) {
    removeVideoBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      resetPhoneVideoUploadState();
    });
  }

  // Category Filter Pills
  const catPills = document.querySelectorAll("#video-category-filters .video-cat-pill");
  catPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      catPills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      const cat = pill.getAttribute("data-cat");
      currentVideoCategory = cat;
      loadVideoInterviews(cat, currentVideoSearchQuery);
    });
  });

  // Search Input with Debounce
  const searchInput = document.getElementById("video-search-input");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        currentVideoSearchQuery = e.target.value.trim();
        loadVideoInterviews(currentVideoCategory, currentVideoSearchQuery);
      }, 300);
    });
  }

  // Submit Video Interview Form
  const form = document.getElementById("post-video-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById("submit-post-video-btn");
      const originalText = submitBtn ? submitBtn.innerHTML : "";

      const title = document.getElementById("vid-title")?.value?.trim() || "";
      const interviewee_name = document.getElementById("vid-name")?.value?.trim() || "";
      const identity_tag = document.getElementById("vid-identity")?.value?.trim() || "LGBTQ+ Community";
      const category = document.getElementById("vid-category")?.value || "Personal Story";
      const key_quote = document.getElementById("vid-quote")?.value?.trim() || "";
      const location = document.getElementById("vid-location")?.value?.trim() || "India";
      const duration = document.getElementById("vid-duration")?.value?.trim() || "";
      const description = document.getElementById("vid-description")?.value?.trim() || "";

      if (!title || !interviewee_name) {
        showToast("Please fill in Interview Title and Interviewee Name.", "error");
        return;
      }

      // PHONE VIDEO UPLOAD MODE
      if (currentVideoSourceMode === "phone") {
        const fileInput = document.getElementById("vid-phone-file-input");
        const videoFile = fileInput && fileInput.files ? fileInput.files[0] : null;

        if (!videoFile) {
          showToast("📱 Please tap to select or record a video from your phone first.", "error");
          return;
        }

        const sizeMb = (videoFile.size / (1024 * 1024)).toFixed(1);
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<span>⏳</span> Uploading Phone Video (${sizeMb} MB)...`;
        }

        try {
          const formData = new FormData();
          formData.append("file", videoFile);
          formData.append("title", title);
          formData.append("interviewee_name", interviewee_name);
          formData.append("identity_tag", identity_tag);
          formData.append("category", category);
          formData.append("key_quote", key_quote);
          formData.append("location", location);
          formData.append("duration", duration || "Phone Video");
          formData.append("description", description);

          const headers = {};
          if (currentAuthToken) {
            headers["Authorization"] = `Bearer ${currentAuthToken}`;
          }

          const res = await fetch("/api/videos/upload", {
            method: "POST",
            headers,
            body: formData,
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Failed to upload phone video interview");
          }

          const createdVideo = await res.json();
          showToast(`🎉 Phone video published: "${createdVideo.title}"!`, "success");
          form.reset();
          resetPhoneVideoUploadState();
          closePostVideoModal();

          // Refresh feed and highlight All
          currentVideoCategory = "all";
          catPills.forEach((p) => {
            if (p.getAttribute("data-cat") === "all") p.classList.add("active");
            else p.classList.remove("active");
          });
          loadVideoInterviews("all", "");
        } catch (err) {
          console.error("Error uploading phone video:", err);
          showToast(err.message || "Failed to upload phone video. Please try again.", "error");
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        }
      } else {
        // LINK MODE (YouTube / Vimeo)
        const video_url = document.getElementById("vid-url")?.value?.trim() || "";
        if (!video_url) {
          showToast("Please enter a valid video link (YouTube, Vimeo, or web link).", "error");
          return;
        }

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerHTML = `<span>⏳</span> Publishing link...`;
        }

        try {
          const headers = { "Content-Type": "application/json" };
          if (currentAuthToken) {
            headers["Authorization"] = `Bearer ${currentAuthToken}`;
          }

          const res = await fetch("/api/videos", {
            method: "POST",
            headers,
            body: JSON.stringify({
              title,
              interviewee_name,
              identity_tag,
              category,
              video_url,
              key_quote,
              location,
              duration: duration || "10 mins",
              description,
            }),
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Failed to post video interview");
          }

          const createdVideo = await res.json();
          showToast(`🎉 Video interview published: "${createdVideo.title}"!`, "success");
          form.reset();
          resetPhoneVideoUploadState();
          closePostVideoModal();

          currentVideoCategory = "all";
          catPills.forEach((p) => {
            if (p.getAttribute("data-cat") === "all") p.classList.add("active");
            else p.classList.remove("active");
          });
          loadVideoInterviews("all", "");
        } catch (err) {
          console.error("Error posting video:", err);
          showToast(err.message || "Failed to post video interview. Please check the URL.", "error");
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        }
      }
    });
  }

  // Preload interviews so they are ready when navigated to
  loadVideoInterviews();
}

window.openPostVideoModal = openPostVideoModal;
window.closePostVideoModal = closePostVideoModal;
window.loadVideoInterviews = loadVideoInterviews;
