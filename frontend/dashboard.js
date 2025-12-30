"use strict";

/* ============================================================
   KAIA AI × KAIA - COMMAND CENTER ENGINE (Version 7.6 - RESTORED)
   ============================================================ */

const $ = (id) => document.getElementById(id);
const token = localStorage.getItem("token");
let currentLang = localStorage.getItem("kaia_lang") || "ar";
let currentUserData = null;

/* =======================
   1. ACCESS CONTROL (أصلي)
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
   2. محرك اللغات (أصلي)
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
   3. الآلة الحاسبة (أصلي)
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
        calcExpression = eval(calcExpression).toString();
        $("calc-display").innerText = calcExpression;
    } catch (e) {
        $("calc-display").innerText = "Error";
        calcExpression = "";
    }
};

/* =======================
   4. إدارة المخاطر (أصلي)
   ======================= */
window.calculateRiskPercent = () => {
    const balance = parseFloat($("balance").value);
    const lot = parseFloat($("risk-lot").value);
    const slPips = parseFloat($("sl-pips-input").value);

    if (!balance || !lot || !slPips) {
        alert(currentLang === 'ar' ? "يرجى ملء جميع الخانات أولاً" : "Please fill all fields first");
        return;
    }

    const riskAmount = lot * slPips * 10;
    const riskPercent = (riskAmount / balance) * 100;

    const resultDiv = $("risk-result");
    if (currentLang === 'ar') {
        resultDiv.innerHTML = `مبلغ المخاطرة: $${riskAmount.toFixed(2)} <br> نسبة المخاطرة: ${riskPercent.toFixed(2)}%`;
    } else {
        resultDiv.innerHTML = `Risk Amount: $${riskAmount.toFixed(2)} <br> Risk Percent: ${riskPercent.toFixed(2)}%`;
    }
};

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
   5. نظام المساعدة والتعليمات (أصلي)
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
   6. التصفير البصري (المعدل للإصلاح الفوري)
   ======================= */
window.resetWorkspace = function() {
    // 1. إخفاء صندوق النتائج وتصفير مدخلات الملفات
    if ($("result-box")) $("result-box").style.display = "none";
    if ($("chartUpload")) $("chartUpload").value = ""; 

    // 2. إصلاح الممحاة: مسح خلفية الصورة بصرياً وبالقوة (إزالة Inline Styles)
    const dropZone = $("drop-zone");
    if (dropZone) {
        dropZone.style.backgroundImage = "none";
        dropZone.style.backgroundColor = "";
        dropZone.style.removeProperty("background-image");
        dropZone.classList.remove("has-image"); // إزالة أي كلاس قد يكون مضافاً
    }

    // 3. إعادة النص التوضيحي الأصلي
    const statusText = $("status-text");
    if (statusText) {
        const dict = translations?.[currentLang];
        statusText.innerText = dict?.drop_zone_text || (currentLang === 'ar' ? "إلصق الشارت هنا 📸" : "Paste Chart Here 📸");
        statusText.style.color = ""; 
    }
    
    console.log("🧹 Workspace Reset Successfully");
};

/* =======================
   7. منطق الجلسات والعطلات (أصلي)
   ======================= */
async function updateMarketSessions() {
    const now = new Date();
    const utcHour = now.getUTCHours();
    const utcDay = now.getUTCDay();
    const year = now.getFullYear();
    const todayISO = now.toISOString().split('T')[0];

    let holidays = JSON.parse(localStorage.getItem('kaia_holidays') || '[]');
    const lastFetch = localStorage.getItem('kaia_holiday_last_fetch');

    if (!lastFetch || lastFetch !== todayISO) {
        try {
            const countryCodes = ['AU', 'JP', 'GB', 'US'];
            let fetchedHolidays = [];

            for (let code of countryCodes) {
                const res = await fetch(`https://date.nager.at/api/v3/PublicHolidays/${year}/${code}`);
                const data = await res.json();
                fetchedHolidays.push(...data.map(h => ({ date: h.date, country: code })));
            }
            localStorage.setItem('kaia_holidays', JSON.stringify(fetchedHolidays));
            localStorage.setItem('kaia_holiday_last_fetch', todayISO);
            holidays = fetchedHolidays;
        } catch (e) { console.error("Holiday API Error"); }
    }

    const sessions = [
        { id: "session-sydney", start: 22, end: 7, country: 'AU' },
        { id: "session-tokyo", start: 0, end: 9, country: 'JP' },
        { id: "session-london", start: 8, end: 17, country: 'GB' },
        { id: "session-newyork", start: 13, end: 22, country: 'US' }
    ];

    const isWeekend = (utcDay === 6) || (utcDay === 0 && utcHour < 22) || (utcDay === 5 && utcHour >= 22);

    sessions.forEach(s => {
        const el = $(s.id);
        if (!el) return;

        const isTodayHoliday = holidays.some(h => h.date === todayISO && h.country === s.country);
        
        let isOpen = false;
        if (!isWeekend && !isTodayHoliday) {
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
   8. محرك التحليل (المعدل لدعم Whale Vision ودرع JSON)
   ======================= */
async function runInstitutionalAnalysis() {
    const strategy = $("strategy")?.value || "SMC";
    const timeframe = $("timeframe")?.value || "15m";
    const fileInput = $("chartUpload");

    if (!fileInput || !fileInput.files.length) {
        alert(currentLang === 'ar' ? "⚠️ يرجى إعادة رفع صورة الشارت مرة أخرى لبدء تحليل جديد." : "⚠️ Please re-upload chart image.");
        return;
    }

    const btn = $("run-btn");
    const resBox = $("result-box");
    const resContent = $("res-data-content");

    btn.innerText = currentLang === 'ar' ? "KAIA تدرس السيولة..." : "KAIA ANALYZING...";
    btn.disabled = true;

    try {
        const uploadFd = new FormData();
        uploadFd.append("chart", fileInput.files[0]);

        const uploadRes = await fetch("/api/upload-chart", { method: "POST", body: uploadFd });
        if (!uploadRes.ok) throw new Error("UPLOAD_FAIL");
        const uploadData = await uploadRes.json();

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

        if (!analyzeRes.ok) throw new Error("ANALYSIS_FAIL");
        const data = await analyzeRes.json();
        
        if (data.status === "error") throw new Error(data.detail);

        const analysis = data.analysis;
        resBox.style.display = "block";

        if (data.tier_mode === "Platinum") {
            // استعادة وعرض Whale Vision (رؤية الحيتان)
            resContent.innerHTML = `
                <div class="analysis-result-card" style="border:2px solid var(--gold); padding:25px; border-radius:20px; background:rgba(255,215,0,0.03);">
                    <h3 style="text-align:center; color:var(--gold); font-weight:900; margin-bottom:20px;">KAIA MASTER VISION</h3>
                    
                    <div style="background:rgba(239,68,68,0.1); padding:15px; border-radius:15px; margin:15px 0; border:1px dashed #ef4444;">
                        <strong style="color:#ef4444;"><i class="fa-solid fa-bullseye"></i> مناطق مصائد الحيتان (Stop-Hunt):</strong>
                        ${(analysis.stop_hunt_risk_zones || []).map(z => `
                            <div style="font-size:13px; margin-top:8px; border-bottom:1px solid rgba(239,68,68,0.2); padding-bottom:5px;">
                                <b style="color:#ef4444;">📍 ${z.zone_price_hint}:</b> ${z.why_risky}
                            </div>
                        `).join('') || (currentLang === 'ar' ? 'لا توجد مصائد واضحة حالياً' : 'No traps detected')}
                    </div>

                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:15px;">
                        <div style="background:#050b14; padding:15px; border-radius:15px; border-right:4px solid var(--success);">
                            <small style="color:var(--success)">Upside Watch</small>
                            ${(analysis.key_levels?.upside || []).map(l => `<div style="font-family:monospace; font-weight:900; font-size:16px; margin-top:5px;">${l.price}</div>`).join('') || '---'}
                        </div>
                        <div style="background:#050b14; padding:15px; border-radius:15px; border-right:4px solid #ef4444;">
                            <small style="color:#ef4444">Downside Watch</small>
                            ${(analysis.key_levels?.downside || []).map(l => `<div style="font-family:monospace; font-weight:900; font-size:16px; margin-top:5px;">${l.price}</div>`).join('') || '---'}
                        </div>
                    </div>

                    <div style="padding:15px; background:rgba(255,255,255,0.03); border-radius:15px; border:1px solid rgba(255,255,255,0.1);">
                        <strong>📝 البصمة المؤسسية:</strong> 
                        <p style="margin-top:8px; line-height:1.6; font-size:14px;">${analysis.analysis_text || analysis.market_state?.notes || 'Analysis complete.'}</p>
                    </div>
                </div>
            `;
        } else {
            // العرض العادي للباقات الأخرى
            const bias = analysis.market_bias || "Neutral";
            resContent.innerHTML = `
                <div class="analysis-result-card" style="padding:20px; border-right:5px solid var(--primary); background:rgba(255,255,255,0.02); border-radius:10px;">
                    <h3>KAIA ANALYSIS</h3>
                    <div style="font-size:18px; font-weight:900; color:var(--primary); margin:10px 0;">Bias: ${bias}</div>
                    <p style="margin-top:10px; line-height:1.6; font-size:15px;">${analysis.analysis_text || ''}</p>
                    ${analysis.risk_note ? `<div style="margin-top:15px; font-size:12px; color:#ef4444;">⚠️ ${analysis.risk_note}</div>` : ''}
                </div>
            `;
        }

        currentUserData.credits = data.remaining_credits;
        syncUserData();
        resBox.scrollIntoView({ behavior: 'smooth' });

    } catch (e) {
        console.error("Analysis Error:", e);
        alert(currentLang === 'ar' ? `⚠️ فشل التحليل: ${e.message}` : `⚠️ Analysis Failed: ${e.message}`);
        resetWorkspace();
    } finally {
        btn.innerText = currentLang === 'ar' ? "بدء التحليل" : "Analyze";
        btn.disabled = false;
    }
}

/* =======================
   9. UTILITIES & INIT (أصلي)
   ======================= */
function setupWorkspaceUtilities() {
    document.addEventListener("paste", (e) => {
        const item = [...e.clipboardData.items].find(x => x.type.includes("image"));
        if (item) {
            const blob = item.getAsFile();
            const reader = new FileReader();
            reader.onload = (event) => {
                if ($("drop-zone")) {
                    $("drop-zone").style.backgroundImage = `url(${event.target.result})`;
                    $("drop-zone").style.backgroundSize = "contain";
                    $("drop-zone").style.backgroundRepeat = "no-repeat";
                    $("drop-zone").style.backgroundPosition = "center";
                }
            };
            reader.readAsDataURL(blob);
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
            if (fileInput.files[0]) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    $("drop-zone").style.backgroundImage = `url(${e.target.result})`;
                    $("drop-zone").style.backgroundSize = "contain";
                    $("drop-zone").style.backgroundRepeat = "no-repeat";
                    $("drop-zone").style.backgroundPosition = "center";
                };
                reader.readAsDataURL(fileInput.files[0]);
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
            localStorage.setItem("kaia_lang", e.target.value);
            location.reload(); 
        };
    }
    updateMarketSessions();
    setInterval(updateMarketSessions, 60000);
    if ($("run-btn")) $("run-btn").onclick = runInstitutionalAnalysis;
    if ($("drop-zone")) $("drop-zone").onclick = () => $("chartUpload").click();
};