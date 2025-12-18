/* =========================================================
   CANA AI – script.js (STABLE FULL - FAST NEWS)
   - TradingView is in index.html (no placeholders)
   - FAST News ticker (instant fallback + local cache + timeout + lazy load)
   - i18n
   - Auth + Credits + Portfolio + History + Share
   - Upload (click/drag) + Paste (Ctrl+V)
   - Analyze (upload + analyze) + Loading spinner
   - Pricing/Subscription modal + Terms/Privacy
   ========================================================= */

"use strict";

let uploadedFilename = "";
let authToken = localStorage.getItem("token") || "";
let userCredits = 0;

function $(id) { return document.getElementById(id); }

/* =========================
   Helpers & API
   ========================= */
function setAuthMsg(text) {
  const el = $("auth-msg");
  if (el) el.innerText = text || "";
}

function setToken(token) {
  authToken = token || "";
  if (authToken) localStorage.setItem("token", authToken);
  else localStorage.removeItem("token");
}

function showAuthOverlay(show) {
  const overlay = $("auth-overlay");
  if (!overlay) return;
  overlay.classList.toggle("hidden", !show);

  const userInfo = $("user-info");
  if (userInfo && show) userInfo.classList.add("hidden");
}

function setCreditsUI(credits) {
  userCredits = Number(credits ?? 0);
  const el = $("credits-count");
  if (el) el.innerText = String(userCredits);

  const portCreds = $("port-credits");
  if (portCreds) portCreds.innerText = String(userCredits);
}

async function safeJson(res) {
  try { return await res.json(); } catch { return null; }
}

async function apiFetch(url, options = {}, requireAuth = true) {
  const headers = new Headers(options.headers || {});
  if (requireAuth && authToken) headers.set("Authorization", "Bearer " + authToken);
  return fetch(url, { ...options, headers });
}

/* =========================
   I18N
   ========================= */
const I18N = {
  ar: {
    title_hero: "CANA AI ثورة التداول <br> بقدرات الذكاء الاصطناعي الفائق",
    subtitle: "تجاوز التحليل البشري. خوارزميات متخصصة تكشف لك ما لا تراه العين.",
    upload_header: "مركز تحليل CANA",
    drag_drop: "اضغط للرفع أو الصق الصورة (Ctrl+V)",
    analysis_label: "الاستراتيجية",
    timeframe_label: "الإطار الزمني",
    run_btn: "تحليل CANA الذكي",
    analyzing: "نظام CANA يعالج البيانات...",
    result_title: "نتائج التوصية",
    signal: "الإشارة", entry: "الدخول", sl: "الوقف (SL)", tp: "الهدف (TP)",
    chart_img: "الشارت المعالج:", close_btn: "إغلاق التقرير", notes_label: "منطق CANA",
    links_title: "روابط", link_pricing: "الباقات والأسعار", link_terms: "شروط الاستخدام", link_privacy: "سياسة الخصوصية",
    contact_title: "التواصل",
    terms_title: "شروط الاستخدام",
    privacy_title: "سياسة الخصوصية"
  },
  en: {
    title_hero: "CANA AI Trading Revolution <br> Powered by Super-Intelligence",
    subtitle: "Go beyond human analysis. Specialized algorithms that reveal hidden opportunities.",
    upload_header: "CANA Analysis Hub",
    drag_drop: "Click to Upload or Paste Image (Ctrl+V)",
    analysis_label: "Strategy", timeframe_label: "Timeframe", run_btn: "Run CANA Analysis",
    analyzing: "CANA System Processing...",
    result_title: "Trade Recommendation",
    signal: "Signal", entry: "Entry", sl: "Stop Loss", tp: "Target",
    chart_img: "Chart Overview:", close_btn: "Close Report", notes_label: "CANA Logic",
    links_title: "Links", link_pricing: "Pricing", link_terms: "Terms of Use", link_privacy: "Privacy Policy",
    contact_title: "Contact",
    terms_title: "Terms of Use",
    privacy_title: "Privacy Policy"
  }
};

function getLang() { return localStorage.getItem("lang") || "ar"; }
function setLang(lang) { localStorage.setItem("lang", lang); }

function translateStaticText(lang) {
  const dict = I18N[lang] || I18N.ar;
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === "ar") ? "rtl" : "ltr";

  const langText = $("lang-text");
  if (langText) langText.innerText = (lang === "ar") ? "English" : "العربية";

  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key] != null) el.innerHTML = dict[key];
  });
}

function initLanguage() {
  translateStaticText(getLang());
  initNewsTicker();

  const btn = $("lang-btn");
  if (btn) btn.addEventListener("click", () => {
    const next = (getLang() === "ar") ? "en" : "ar";
    setLang(next);
    translateStaticText(next);
    initNewsTicker();
  });
}

/* =========================
   News Ticker (FAST)
   - Instant fallback
   - localStorage cache (10 min)
   - timeout so it never “hangs”
   - lazy load so page renders first
   ========================= */
function withTimeoutFetch(url, ms = 3500) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { signal: ctrl.signal }).finally(() => clearTimeout(t));
}

function getCache(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj?.ts || !obj?.html) return null;
    return obj;
  } catch { return null; }
}

function setCache(key, html) {
  try { localStorage.setItem(key, JSON.stringify({ ts: Date.now(), html })); } catch {}
}

async function initNewsTicker() {
  const tickerContent = $("news-ticker-content");
  const tickerLabel = $("ticker-label-text");
  if (!tickerContent) return;

  const lang = getLang();
  if (tickerLabel) tickerLabel.innerText = (lang === "ar") ? "أخبار الاقتصاد" : "Economic News";

  const cacheKey = `news_cache_${lang}`;
  const cached = getCache(cacheKey);
  const TTL = 10 * 60 * 1000;

  if (cached && (Date.now() - cached.ts) < TTL) {
    tickerContent.innerHTML = cached.html;
  } else {
    const fallbackNews = (lang === "ar")
      ? "الذهب يتذبذب قرب المقاومة | ترقب بيانات التضخم | الدولار يتحرك بقوة | تقلبات الكريبتو"
      : "Gold fluctuates near resistance | Markets watch inflation | USD moves | Crypto volatility";
    tickerContent.innerHTML = `<div class="ticker-item">${fallbackNews}</div>`;
  }

  // lazy refresh
  setTimeout(async () => {
    try {
      // DailyForex RSS (as you provided)
      const rssUrl = (lang === "ar")
        ? "https://arab.dailyforex.com/forex-rss"
        : "https://www.dailyforex.com/forex-rss";

      const apiUrl = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(rssUrl)}`;
      const res = await withTimeoutFetch(apiUrl, 3500);
      if (!res.ok) return;

      const data = await res.json();
      if (data?.status !== "ok" || !Array.isArray(data.items) || data.items.length === 0) return;

      const items = data.items.slice(0, 7);
      const dir = (lang === "ar") ? "rtl" : "ltr";

      let html = "";
      for (const item of items) {
        const title = String(item.title || "")
          .replace(/&quot;/g, '"')
          .replace(/&#039;/g, "'");

        html += `<div class="ticker-item" style="direction:${dir}">
          <span style="color:#666; font-size:0.8em">●</span>
          <a href="${item.link}" target="_blank" rel="noreferrer">${title}</a>
        </div>`;
      }

      tickerContent.innerHTML = html;
      setCache(cacheKey, html);
    } catch {
      // keep fallback/cached
    }
  }, 900);
}

/* =========================
   Modals
   ========================= */
function setupLegalModal(btnId, modalId, closeId) {
  const btn = $(btnId);
  const modal = $(modalId);
  const close = $(closeId);

  if (btn && modal) {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      modal.classList.remove("hidden");
    });
  }

  if (close && modal) close.addEventListener("click", () => modal.classList.add("hidden"));

  window.addEventListener("click", (e) => {
    if (modal && e.target === modal) modal.classList.add("hidden");
  });
}

function initModals() {
  const closeAuth = $("close-auth");
  if (closeAuth) closeAuth.addEventListener("click", () => $("auth-overlay")?.classList.add("hidden"));

  const openSubNav = $("open-subscription");
  const openSubFooter = $("open-pricing-footer");
  const subModal = $("subscription-modal");
  const closeSub = $("close-sub");

  function openSubscription(e){
    if (e) e.preventDefault();
    if (subModal) subModal.classList.remove("hidden");
  }

  if (openSubNav) openSubNav.addEventListener("click", openSubscription);
  if (openSubFooter) openSubFooter.addEventListener("click", openSubscription);
  if (closeSub) closeSub.addEventListener("click", () => subModal?.classList.add("hidden"));

  setupLegalModal("open-terms", "terms-modal", "close-terms");
  setupLegalModal("open-privacy", "privacy-modal", "close-privacy");

  const portBtn = $("portfolio-btn");
  const portModal = $("portfolio-modal");
  const portClose = $("close-portfolio");

  if (portBtn && portModal) {
    portBtn.addEventListener("click", (e) => {
      e.preventDefault();

      const pc = $("port-credits");
      if (pc) pc.innerText = String(userCredits);

      const email = localStorage.getItem("user_email") || "User";
      const pu = $("port-username");
      if (pu) pu.innerText = email.split("@")[0];

      const isVip = localStorage.getItem("is_whale") === "true";
      const badge = $("port-plan-badge");
      if (badge) {
        badge.innerText = isVip ? "VIP WHALE 🐋" : "Trader Plan";
        badge.style.background = isVip ? "#d946ef" : "#f59e0b";
        badge.style.color = isVip ? "#fff" : "#000";
      }

      loadHistory();
      portModal.classList.remove("hidden");
    });
  }

  if (portClose && portModal) portClose.addEventListener("click", () => portModal.classList.add("hidden"));
}

/* =========================
   Pricing UI
   ========================= */
function initPricingLogic() {
  document.querySelectorAll(".plan-card button").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".plan-card").forEach(c => c.classList.remove("active-plan"));
      document.querySelectorAll(".plan-card button").forEach(b => b.innerText = "Select");

      const card = e.target.closest(".plan-card");
      if (!card) return;

      card.classList.add("active-plan");
      e.target.innerText = "Selected ✅";

      const planName = card.querySelector("h3")?.innerText || "Plan";
      const planPrice = card.querySelector(".price")?.innerText || "";
      const whatsappLink = document.querySelector(".whatsapp-link");

      if (whatsappLink) {
        const lang = getLang();
        const msg = (lang === "ar")
          ? `مرحباً، أود الاشتراك في باقة ${planName} بسعر ${planPrice}. لقد قمت بالتحويل.`
          : `Hello, I'd like to subscribe to ${planName} plan for ${planPrice}. I have paid.`;

        whatsappLink.href = `https://wa.me/970594060648?text=${encodeURIComponent(msg)}`;
      }
    });
  });
}
// ✅ حماية من أي كود قديم يناديها
function initSubscriptionUI(){ initPricingLogic(); }

/* =========================
   Upload (click/drag) + Paste
   ========================= */
function initUploadAndPaste() {
  const dropZone = $("drop-zone");
  const fileInput = $("chartUpload");

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("drag");
    });

    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag"));

    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag");
      if (e.dataTransfer.files?.[0]) {
        fileInput.files = e.dataTransfer.files;
        const h3 = dropZone.querySelector("h3");
        if (h3) h3.innerText = "📸 File Selected: " + e.dataTransfer.files[0].name;
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files?.[0]) {
        const h3 = dropZone.querySelector("h3");
        if (h3) h3.innerText = "📸 File Selected: " + fileInput.files[0].name;
      }
    });
  }

  document.addEventListener("paste", (e) => {
    const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
    if (!items || !fileInput || !dropZone) return;

    for (const item of items) {
      if (item.kind === "file" && item.type.includes("image/")) {
        const blob = item.getAsFile();
        if (!blob) continue;

        const dt = new DataTransfer();
        dt.items.add(blob);
        fileInput.files = dt.files;

        uploadedFilename = "";
        const h3 = dropZone.querySelector("h3");
        if (h3) h3.innerText = "📸 Image Pasted! Ready.";

        dropZone.style.borderColor = "#10b981";
        dropZone.style.background = "rgba(16, 185, 129, 0.1)";
        setTimeout(() => {
          dropZone.style.borderColor = "";
          dropZone.style.background = "";
        }, 1500);

        e.preventDefault();
        return;
      }
    }
  });
}

/* =========================
   Analysis (upload + analyze)
   ========================= */
function initAnalysis() {
  const runBtn = $("run-btn");
  const closeRes = $("close-result");

  const loadingBox = $("loading-box");
  const resultBox = $("result-box");

  function showLoading(show){
    if (!loadingBox) return;
    loadingBox.classList.toggle("hidden", !show);
  }

  function showResult(show){
    if (!resultBox) return;
    resultBox.classList.toggle("hidden", !show);
  }

  function setText(id, val){
    const el = $(id);
    if (el) el.innerText = (val == null ? "---" : String(val));
  }

  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      if (!authToken) { showAuthOverlay(true); return; }

      const fileInput = $("chartUpload");
      const dropZone = $("drop-zone");

      if (!fileInput?.files?.length) {
        alert(getLang()==="ar" ? "يرجى رفع صورة أو لصقها أولاً" : "Please upload or paste an image first.");
        return;
      }

      showLoading(true);
      showResult(false);

      // 1) Upload
      const uploadForm = new FormData();
      uploadForm.append("chart", fileInput.files[0]);

      try {
        const upRes = await apiFetch("/api/upload-chart", { method: "POST", body: uploadForm }, true);
        const upData = await safeJson(upRes);
        if (!upRes.ok) throw new Error(upData?.detail || "Upload Failed");
        uploadedFilename = upData?.filename || "";
      } catch (e) {
        showLoading(false);
        alert(String(e.message || "Upload Failed"));
        return;
      }

      // 2) Analyze
      const anForm = new FormData();
      anForm.append("filename", uploadedFilename);
      anForm.append("analysis_type", $("analysis-type")?.value || "smc");
      anForm.append("timeframe", $("timeframe-select")?.value || "Not Specified");
      anForm.append("lang", getLang());

      // optional inputs (if you added them in UI later)
      const sess = $("session-select")?.value;
      const val = $("validity-select")?.value;
      if (sess) anForm.append("session_in", sess);
      if (val) anForm.append("validity_in", val);

      try {
        const res = await apiFetch("/api/analyze-chart", { method: "POST", body: anForm }, true);
        const data = await safeJson(res);
        showLoading(false);

        if (!res.ok) {
          alert(data?.detail === "OUT_OF_CREDITS"
            ? (getLang()==="ar" ? "انتهى الرصيد!" : "Out of credits!")
            : (data?.detail || (getLang()==="ar" ? "فشل التحليل" : "Analysis failed")));
          return;
        }

        if (typeof data?.remaining_credits === "number") setCreditsUI(data.remaining_credits);

        setText("r-signal", data?.signal);
        setText("r-entry", data?.entry);
        setText("r-tp", data?.tp);
        setText("r-sl", data?.sl);
        setText("r-timeframe", data?.timeframe);
        setText("r-session", data?.session);
        setText("r-validity", data?.validity);
        setText("r-notes", data?.notes);
        setText("r-reason", data?.reason);

        const badge = $("signal-badge-display");
        if (badge) {
          badge.innerText = data?.signal || "WAIT";
          badge.style.background = (data?.signal === "BUY") ? "#10b981" : (data?.signal === "SELL" ? "#ef4444" : "#334155");
        }

        const img = $("processed-img");
        if (img && uploadedFilename) img.src = `/images/uploaded_${encodeURIComponent(uploadedFilename)}`;

        showResult(true);
        if (dropZone) dropZone.classList.remove("drag");

      } catch {
        showLoading(false);
        alert(getLang()==="ar" ? "مشكلة اتصال" : "Connection error");
      }
    });
  }

  if (closeRes) {
    closeRes.addEventListener("click", () => {
      showResult(false);

      ["r-signal","r-entry","r-sl","r-tp","r-timeframe","r-session","r-validity","r-notes","r-reason"]
        .forEach(id => setText(id, "---"));

      const badge = $("signal-badge-display");
      if (badge) { badge.innerText = "WAIT"; badge.style.background = "#334155"; }

      const img = $("processed-img");
      if (img) img.src = "";

      const fileInput = $("chartUpload");
      if (fileInput) fileInput.value = "";

      uploadedFilename = "";

      const dropZone = $("drop-zone");
      const h3 = dropZone?.querySelector("h3");
      if (h3) {
        h3.innerText = (getLang()==="ar")
          ? "اضغط للرفع أو الصق الصورة (Ctrl+V)"
          : "Click to Upload or Paste Image (Ctrl+V)";
      }
    });
  }
}

/* =========================
   History + Share + Calculators
   ========================= */
async function loadHistory() {
  const list = $("history-list");
  if (!list) return;

  list.innerHTML = "<tr><td colspan='5'>Loading...</td></tr>";
  try {
    const res = await apiFetch("/api/history", { method: "GET" }, true);
    const data = await safeJson(res);

    if (!Array.isArray(data) || data.length === 0) {
      list.innerHTML = "<tr><td colspan='5'>No trades yet.</td></tr>";
      return;
    }

    list.innerHTML = "";
    data.forEach(item => {
      const color = item.signal === "BUY" ? "#10b981" : "#ef4444";
      const date = new Date(item.created_at).toLocaleDateString();
      list.innerHTML += `
        <tr>
          <td>${date}</td>
          <td style="color:${color}; font-weight:bold">${item.signal}</td>
          <td>${item.entry}</td>
          <td>${item.tp}</td>
          <td>
            <button class="btn-outline small" onclick='shareTrade(${JSON.stringify(item)})'>
              <i class="fa-solid fa-share-nodes"></i>
            </button>
          </td>
        </tr>`;
    });
  } catch {
    list.innerHTML = "<tr><td colspan='5'>Error</td></tr>";
  }
}

window.shareTrade = function(item) {
  const scSig = $("sc-signal");
  if (scSig) {
    scSig.innerText = item.signal;
    scSig.style.color = item.signal === "BUY" ? "#10b981" : "#ef4444";
  }
  const scEntry = $("sc-entry"); if (scEntry) scEntry.innerText = item.entry;
  const scTp = $("sc-tp"); if (scTp) scTp.innerText = item.tp;
  const scSl = $("sc-sl"); if (scSl) scSl.innerText = item.sl;

  const tpl = $("share-card-template");
  if (!tpl) return;

  html2canvas(tpl).then(canvas => {
    const link = document.createElement("a");
    link.download = `CANA-Trade-${item.id}.png`;
    link.href = canvas.toDataURL();
    link.click();
  });
};

window.calculateRisk = function() {
  const bal = parseFloat($("calc-balance")?.value);
  const risk = parseFloat($("calc-risk")?.value);
  const sl = parseFloat($("calc-sl")?.value);
  if (!bal || !risk || !sl) return;

  const lot = (bal * (risk/100)) / (sl * 10);
  const out = $("res-lot");
  if (out) out.innerText = lot.toFixed(2) + " Lot";
  $("risk-res")?.classList.remove("hidden");
};

window.calculatePipVal = function() {
  const lot = parseFloat($("calc-lot-size")?.value);
  const pips = parseFloat($("calc-pips-num")?.value);
  if (!lot || !pips) return;

  const profit = (lot * pips * 10);
  const out = $("res-profit");
  if (out) out.innerText = profit.toFixed(2) + "$";
  $("pip-res")?.classList.remove("hidden");
};

/* =========================
   Auth
   ========================= */
function initAuth() {
  const tabLogin = $("tab-login");
  const tabRegister = $("tab-register");
  const loginForm = $("login-form");
  const registerForm = $("register-form");
  const authTitle = $("auth-title");

  if (tabLogin && tabRegister && loginForm && registerForm && authTitle) {
    tabLogin.addEventListener("click", () => {
      loginForm.classList.remove("hidden");
      registerForm.classList.add("hidden");
      tabLogin.classList.add("active");
      tabRegister.classList.remove("active");
      authTitle.innerText = "Welcome to CANA";
    });

    tabRegister.addEventListener("click", () => {
      loginForm.classList.add("hidden");
      registerForm.classList.remove("hidden");
      tabLogin.classList.remove("active");
      tabRegister.classList.add("active");
      authTitle.innerText = "Create Account";
    });
  }

  loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    setAuthMsg("Logging in...");

    try {
      const formData = new FormData();
      formData.append("username", $("login-email")?.value || "");
      formData.append("password", $("login-password")?.value || "");
      formData.append("grant_type", "password");

      const res = await apiFetch("/api/login", { method: "POST", body: formData }, false);
      const data = await safeJson(res);

      if (!res.ok || !data?.access_token) {
        setAuthMsg(data?.detail || "Invalid Credentials");
        return;
      }

      setToken(data.access_token);
      location.reload();
    } catch {
      setAuthMsg("Network Error");
    }
  });

  registerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    setAuthMsg("Creating account...");

    try {
      const email = $("reg-email")?.value?.trim() || "";
      const password = $("reg-password")?.value || "";
      const password2 = $("reg-password2")?.value || "";

      if (!email || !password) { setAuthMsg("Please fill all fields."); return; }
      if (password !== password2) { setAuthMsg("Passwords do not match."); return; }

      const payload = { email, password };
      const res = await apiFetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }, false);

      const data = await safeJson(res);
      if (!res.ok) { setAuthMsg(data?.detail || "Registration Failed"); return; }

      setAuthMsg("Account Created! Login now.");
      tabLogin?.click();
    } catch {
      setAuthMsg("Network Error");
    }
  });

  $("logout-btn")?.addEventListener("click", () => {
    setToken("");
    location.reload();
  });
}

async function checkLogin() {
  const userInfo = $("user-info");

  if (!authToken) {
    showAuthOverlay(true);
    userInfo?.classList.add("hidden");
    return;
  }

  try {
    const res = await apiFetch("/api/me", { method: "GET" }, true);
    if (!res.ok) {
      setToken("");
      showAuthOverlay(true);
      userInfo?.classList.add("hidden");
      return;
    }

    const user = await safeJson(res);
    setCreditsUI(user?.credits);

    localStorage.setItem("user_email", user?.email || "");
    localStorage.setItem("is_whale", String(user?.is_whale || false));

    const navUser = $("nav-username");
    if (navUser && user?.email) navUser.innerText = user.email.split("@")[0];

    userInfo?.classList.remove("hidden");
    showAuthOverlay(false);

  } catch {
    setToken("");
    showAuthOverlay(true);
    userInfo?.classList.add("hidden");
  }
}

/* =========================
   BOOTSTRAP
   ========================= */
window.addEventListener("load", () => {
  initLanguage();
  initAuth();
  checkLogin();

  initUploadAndPaste();
  initAnalysis();

  initModals();
  initPricingLogic();
});
