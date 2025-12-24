"use strict";

/* ============================================================
   KAIA AI × CANA - COMMAND CENTER ENGINE (Version 6.3 FIXED)
   ============================================================ */

const $ = (id) => document.getElementById(id);
const token = localStorage.getItem("token");
let currentLang = localStorage.getItem("kaia_lang") || "ar";
let currentUserData = null;

/* =======================
   ACCESS CONTROL
   ======================= */
async function checkAccessAndInit() {
    if (!token) {
        window.location.href = "/";
        return;
    }

    try {
        const res = await fetch("/api/me", {
            headers: { "Authorization": "Bearer " + token }
        });

        if (!res.ok) throw new Error("Auth failed");

        currentUserData = await res.json();

        if (currentUserData.tier === "Trial" && !currentUserData.is_admin) {
            alert("⚠️ يرجى الترقية للوصول إلى لوحة التحليل.");
            window.location.href = "/";
            return;
        }

        document.body.style.visibility = "visible";
        syncUserData();
        applyDashboardTranslations(currentLang);

    } catch (e) {
        console.error("Auth Error:", e);
        localStorage.removeItem("token");
        window.location.href = "/";
    }
}

function syncUserData() {
    if ($("dash-user")) $("dash-user").innerText = currentUserData.full_name;
    if ($("dash-credits")) $("dash-credits").innerText = currentUserData.credits;
}

/* =======================
   I18N
   ======================= */
function applyDashboardTranslations(lang) {
    const dict = translations?.[lang];
    if (!dict) return;

    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (dict[key]) el.innerText = dict[key];
    });

    document.body.dir = lang === "ar" ? "rtl" : "ltr";
    currentLang = lang;
    localStorage.setItem("kaia_lang", lang);
}

/* =======================
   ANALYSIS ENGINE (FIXED)
   ======================= */
async function runInstitutionalAnalysis() {
    const strategy = $("strategy")?.value || "SMC";
    const timeframe = $("timeframe")?.value || "15m";
    const fileInput = $("chartUpload");

    if (!fileInput || !fileInput.files.length) {
        alert("الرجاء اختيار أو لصق صورة الشارت أولاً");
        return;
    }

    const btn = $("run-btn");
    const resBox = $("result-box");

    btn.innerText = "KAIA ANALYZING...";
    btn.disabled = true;

    try {
        /* Upload image */
        const uploadFd = new FormData();
        uploadFd.append("chart", fileInput.files[0]);

        const uploadRes = await fetch("/api/upload-chart", {
            method: "POST",
            body: uploadFd
        });

        const uploadData = await uploadRes.json();
        if (!uploadData.filename) throw new Error("Upload failed");

        /* Analyze */
        const analyzeFd = new FormData();
        analyzeFd.append("filename", uploadData.filename);
        analyzeFd.append("timeframe", timeframe);
        analyzeFd.append("analysis_type", strategy);

        const analyzeRes = await fetch("/api/analyze-chart", {
            method: "POST",
            headers: { "Authorization": "Bearer " + token },
            body: analyzeFd
        });

        const data = await analyzeRes.json();
        if (!analyzeRes.ok) throw new Error(data.detail || "Analysis error");

        const analysis = data.analysis;

        resBox.style.display = "block";
        $("res-data-content").innerHTML = `
            <div class="analysis-result-card">
                <h3 style="text-align:center;font-weight:900;">KAIA LIVE REPORT</h3>

                <div class="res-data-grid">
                    <div class="res-data-item">
                        <small>Market Bias</small>
                        <span>${analysis.market_bias}</span>
                    </div>
                    <div class="res-data-item">
                        <small>Market Phase</small>
                        <span>${analysis.market_phase}</span>
                    </div>
                    <div class="res-data-item">
                        <small>Confidence</small>
                        <span>${analysis.confidence}</span>
                    </div>
                </div>

                <div class="analysis-box">
                    <strong>Institutional Analysis</strong>
                    <p>${analysis.analysis_text}</p>
                </div>

                <div class="risk-note">
                    <strong>Risk Note:</strong> ${analysis.risk_note}
                </div>
            </div>
        `;

        currentUserData.credits = data.remaining_credits;
        syncUserData();

    } catch (e) {
        console.error("Analysis Core Error:", e);
        alert("Engine Connection Timeout");
    } finally {
        btn.innerText = "Analyze";
        btn.disabled = false;
    }
}

/* =======================
   UTILITIES
   ======================= */
function setupWorkspaceUtilities() {
    document.addEventListener("paste", (e) => {
        const item = [...e.clipboardData.items].find(x => x.type.includes("image"));
        if (item) {
            const blob = item.getAsFile();
            const dt = new DataTransfer();
            dt.items.add(blob);
            $("chartUpload").files = dt.files;
            if ($("status-text")) {
                $("status-text").innerText = "Image pasted ✅";
            }
        }
    });

    if ($("logout-btn")) {
        $("logout-btn").onclick = () => {
            localStorage.removeItem("token");
            window.location.href = "/";
        };
    }
}

/* =======================
   INIT
   ======================= */
window.onload = () => {
    checkAccessAndInit();
    setupWorkspaceUtilities();

    if ($("run-btn")) $("run-btn").onclick = runInstitutionalAnalysis;
    if ($("drop-zone")) $("drop-zone").onclick = () => $("chartUpload").click();
};
