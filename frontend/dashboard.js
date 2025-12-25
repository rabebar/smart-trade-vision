"use strict";

/* ============================================================
   KAIA AI × CANA - COMMAND CENTER ENGINE (Version 7.0 UPDATED)
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
            alert(currentLang === 'ar' ? "⚠️ باقة التجربة (Trial) متاحة فقط في الصفحة الرئيسية. يرجى الترقية للوصول لغرفة القيادة." : "⚠️ Trial plan is only available on the Home page. Please upgrade to access the Command Center.");
            window.location.href = "/";
            return;
        }

        document.body.style.visibility = "visible";
        document.body.style.opacity = "1";
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
   محرك اللغات والترجمة الشامل
   ======================= */
function applyDashboardTranslations(lang) {
    const dict = translations?.[lang];
    if (!dict) return;

    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (dict[key]) el.innerText = dict[key];
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (dict[key]) el.placeholder = dict[key];
    });

    document.body.dir = lang === "ar" ? "rtl" : "ltr";
    if (lang === "ar") {
        document.body.classList.remove("ltr");
    } else {
        document.body.classList.add("ltr");
    }

    if ($("language-select")) {
        $("language-select").value = lang;
    }

    currentLang = lang;
    localStorage.setItem("kaia_lang", lang);
}

/* =======================
   برمجة الآلة الحاسبة الجانبية (Calculator)
   ======================= */
let calcExpression = "";

window.inputCalc = (val) => {
    calcExpression += val;
    $("calc-display").innerText = calcExpression;
};

window.clearCalc = () => {
    calcExpression = "";
    $("calc-display").innerText = "0";
};

window.deleteCalc = () => {
    calcExpression = calcExpression.slice(0, -1);
    $("calc-display").innerText = calcExpression || "0";
};

window.resultCalc = () => {
    try {
        // حساب المعادلة وتحويل النتيجة لنص
        calcExpression = eval(calcExpression).toString();
        $("calc-display").innerText = calcExpression;
    } catch (e) {
        $("calc-display").innerText = "Error";
        calcExpression = "";
    }
};

/* =======================
   برمجة إدارة المخاطر (Risk Management)
   ======================= */
window.calculateRiskPercent = () => {
    const balance = parseFloat($("balance").value);
    const lot = parseFloat($("risk-lot").value);
    const slPips = parseFloat($("sl-pips-input").value);

    if (!balance || !lot || !slPips) {
        alert(currentLang === 'ar' ? "يرجى ملء جميع الخانات أولاً" : "Please fill all fields first");
        return;
    }

    // المخاطرة بالدولار = حجم اللوت * عدد النقاط * 10 (لأزواج الدولار الأساسية)
    const riskAmount = lot * slPips * 10;
    // نسبة المخاطرة = (المبلغ المخاطر به / رأس المال) * 100
    const riskPercent = (riskAmount / balance) * 100;

    const resultDiv = $("risk-result");
    if (currentLang === 'ar') {
        resultDiv.innerHTML = `مبلغ المخاطرة: $${riskAmount.toFixed(2)} <br> نسبة المخاطرة: ${riskPercent.toFixed(2)}%`;
    } else {
        resultDiv.innerHTML = `Risk Amount: $${riskAmount.toFixed(2)} <br> Risk Percent: ${riskPercent.toFixed(2)}%`;
    }
};

/* =======================
   برمجة حاسبة النقاط (Pip Calculator)
   ======================= */
window.calculatePipProfit = () => {
    const lot = parseFloat($("pip-lot-size").value);
    const pips = parseFloat($("pip-count").value);

    if (!lot || !pips) {
        alert(currentLang === 'ar' ? "يرجى إدخال اللوت وعدد النقاط" : "Please enter lot and pip count");
        return;
    }

    const profit = lot * pips * 10;
    const resultDiv = $("pip-result");

    if (currentLang === 'ar') {
        resultDiv.innerText = `الربح المتوقع: $${profit.toFixed(2)}`;
    } else {
        resultDiv.innerText = `Expected Profit: $${profit.toFixed(2)}`;
    }
};

/* =======================
   نظام المساعدة والتعليمات
   ======================= */
function setupHelpSystem() {
    const helpIcon = $("help-icon");
    const helpBox = $("help-box");

    if (helpIcon && helpBox) {
        helpIcon.onclick = (e) => {
            e.stopPropagation();
            const isVisible = helpBox.style.display === "block";
            helpBox.style.display = isVisible ? "none" : "block";
        };

        document.addEventListener("click", (e) => {
            if (helpBox.style.display === "block" && !helpBox.contains(e.target) && e.target !== helpIcon) {
                helpBox.style.display = "none";
            }
        });
    }
}

/* =======================
   تصفير بيئة العمل (Cleanup Logic)
   ======================= */
window.resetWorkspace = function() {
    if ($("result-box")) $("result-box").style.display = "none";
    if ($("chartUpload")) $("chartUpload").value = ""; 

    if ($("status-text")) {
        const dict = translations?.[currentLang];
        $("status-text").innerText = dict?.drop_zone_text || "إلصق الشارت هنا 📸";
        $("status-text").style.color = ""; 
    }
};

/* =======================
   منطق جلسات التداول
   ======================= */
function updateMarketSessions() {
    const now = new Date();
    const utcHour = now.getUTCHours();
    const utcDay = now.getUTCDay(); // 0=Sunday, 6=Saturday

    const sessions = [
        { id: "session-sydney", start: 22, end: 7 },
        { id: "session-tokyo", start: 0, end: 9 },
        { id: "session-london", start: 8, end: 17 },
        { id: "session-newyork", start: 13, end: 22 }
    ];

    sessions.forEach(s => {
        const el = $(s.id);
        if (!el) return;

        let isOpen = false;
        
        // [حقن تصحيح] التحقق من العطلة الأسبوعية (السبت والأحد)
        const isWeekend = (utcDay === 6) || (utcDay === 0 && utcHour < 22) || (utcDay === 5 && utcHour >= 22);

        if (!isWeekend) {
            if (s.start < s.end) {
                isOpen = utcHour >= s.start && utcHour < s.end;
            } else {
                isOpen = utcHour >= s.start || utcHour < s.end;
            }
        }

        if (isOpen) {
            el.classList.add("session-active");
        } else {
            el.classList.remove("session-active");
        }
    });
}

/* =======================
   ANALYSIS ENGINE (FIXED)
   ======================= */
async function runInstitutionalAnalysis() {
    const strategy = $("strategy")?.value || "SMC";
    const timeframe = $("timeframe")?.value || "15m";
    const fileInput = $("chartUpload");

    if (!fileInput || !fileInput.files.length) {
        alert(currentLang === 'ar' ? "الرجاء اختيار أو لصق صورة الشارت أولاً" : "Please upload or paste chart first");
        return;
    }

    const btn = $("run-btn");
    const resBox = $("result-box");

    btn.innerText = "KAIA ANALYZING...";
    btn.disabled = true;

    try {
        const uploadFd = new FormData();
        uploadFd.append("chart", fileInput.files[0]);

        const uploadRes = await fetch("/api/upload-chart", {
            method: "POST",
            body: uploadFd
        });

        const uploadData = await uploadRes.json();
        if (!uploadData.filename) throw new Error("Upload failed");

        const analyzeFd = new FormData();
        analyzeFd.append("filename", uploadData.filename);
        analyzeFd.append("timeframe", timeframe);
        analyzeFd.append("analysis_type", strategy);
        analyzeFd.append("lang", currentLang);

        const analyzeRes = await fetch("/api/analyze-chart", {
            method: "POST",
            headers: { "Authorization": "Bearer " + token },
            body: analyzeFd
        });

        const data = await analyzeRes.json();
        if (!analyzeRes.ok) throw new Error(data.detail || "Analysis error");

        // [حقن تصحيح] ضمان قراءة البيانات بشكل صحيح من السيرفر
        const analysis = data.analysis;

        resBox.style.display = "block";
        $("res-data-content").innerHTML = `
            <div class="analysis-result-card">
                <h3 style="text-align:center;font-weight:900;">KAIA LIVE REPORT</h3>
                <div class="res-data-grid">
                    <div class="res-data-item"><small>Market Bias</small><span>${analysis.market_bias || '---'}</span></div>
                    <div class="res-data-item"><small>Market Phase</small><span>${analysis.market_phase || '---'}</span></div>
                    <div class="res-data-item"><small>Confidence</small><span>${analysis.confidence || '---'}</span></div>
                </div>
                <div class="analysis-box"><strong>Institutional Analysis</strong><p>${analysis.analysis_text || ''}</p></div>
                <div class="risk-note"><strong>Risk Note:</strong> ${analysis.risk_note || ''}</div>
            </div>
        `;

        currentUserData.credits = data.remaining_credits;
        syncUserData();

    } catch (e) {
        console.error("Analysis Core Error:", e);
        alert("Engine Connection Error");
    } finally {
        btn.innerText = currentLang === 'ar' ? "بدء التحليل" : "Analyze";
        btn.disabled = false;
    }
}

/* =======================
   UTILITIES & INIT
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
                $("status-text").style.color = "var(--success)";
            }
        }
    });

    const fileInput = $("chartUpload");
    if (fileInput) {
        fileInput.onchange = () => {
            if (fileInput.files[0] && $("status-text")) {
                $("status-text").innerText = fileInput.files[0].name;
                $("status-text").style.color = "var(--success)";
            }
        };
    }

    if ($("logout-btn")) {
        $("logout-btn").onclick = () => {
            localStorage.removeItem("token");
            window.location.href = "/";
        };
    }
}

window.onload = () => {
    checkAccessAndInit();
    setupWorkspaceUtilities();
    setupHelpSystem();
    
    if ($("language-select")) {
        $("language-select").onchange = (e) => {
            const newLang = e.target.value;
            localStorage.setItem("kaia_lang", newLang);
            location.reload(); 
        };
    }

    updateMarketSessions();
    setInterval(updateMarketSessions, 60000);

    if ($("run-btn")) $("run-btn").onclick = runInstitutionalAnalysis;
    if ($("drop-zone")) $("drop-zone").onclick = () => $("chartUpload").click();
};