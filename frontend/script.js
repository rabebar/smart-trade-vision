"use strict";

/* ============================================================
   KAIA AI - MASTER FRONTEND ENGINE (Final Integrated)
   Version: 7.6 - Exact Line Match & Password Shield
   ============================================================ */

// --- 1. الثوابت والمتغيرات العامة ---
const $ = (id) => document.getElementById(id);
let authToken = localStorage.getItem("token");
let currentLang = localStorage.getItem("kaia_lang") || "ar";
let currentUserData = null;
let isRegisterMode = false;
let selectedPlan = { name: "Trial", price: "0" };

/* ------------------------------------------------------------
   2. محرك الترجمة واللغات (I18n)
   ------------------------------------------------------------ */
function applyTranslations(lang) {
    try {
        const dictionary = (typeof translations !== 'undefined') ? translations[lang] : null;
        if (!dictionary) return;

        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            if (dictionary[key]) el.innerText = dictionary[key];
        });

        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.getAttribute("data-i18n-placeholder");
            if (dictionary[key]) el.setAttribute("placeholder", dictionary[key]);
        });

        document.body.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
        document.body.classList.toggle("ltr", lang !== "ar");
        
        localStorage.setItem("kaia_lang", lang);
        currentLang = lang;
        if ($("language-select")) $("language-select").value = lang;
    } catch (e) { 
        console.error("Translation Engine Error:", e); 
    }
}

/* ------------------------------------------------------------
   3. إدارة شاشات التحميل والافتتاحية
   ------------------------------------------------------------ */
function hidePreloader() {
    if (sessionStorage.getItem("kaia_intro_seen")) {
        const intro = $("kaia-intro-overlay");
        if (intro) intro.style.display = "none";
    }
    const loaders = document.querySelectorAll('.preloader, .loader-wrapper, #preloader');
    loaders.forEach(l => l.style.display = "none");
}

function runIntroSequence() {
    const overlay = $("kaia-intro-overlay");
    if (!overlay || sessionStorage.getItem("kaia_intro_seen")) return;

    applyTranslations(currentLang);

    setTimeout(() => {
        if ($("intro-loader")) $("intro-loader").style.display = "none";
        if ($("intro-reveal")) $("intro-reveal").style.display = "block";
    }, 3000);

    const igniteBtn = $("ignite-system-btn");
    if (igniteBtn) {
        igniteBtn.onclick = () => {
            overlay.style.transition = "opacity 0.8s ease";
            overlay.style.opacity = "0";
            setTimeout(() => {
                overlay.style.display = "none";
                sessionStorage.setItem("kaia_intro_seen", "true");
            }, 800);
        };
    }
}

/* ------------------------------------------------------------
   4. التحقق من الهوية وزر الإدارة (Admin & Security Core)
   ------------------------------------------------------------ */
async function updateUIBasedOnAuth() {
    const authZone = $("auth-zone");
    const accessArea = $("access-control-area");
    const demoArea = $("demo-analysis-area");

    if (!authZone) return;

    const dict = (typeof translations !== 'undefined' && translations[currentLang]) ? translations[currentLang] : {};

    if (authToken) {
        try {
            const res = await fetch("/api/me", { 
                headers: { "Authorization": "Bearer " + authToken } 
            });
            
            if (res.ok) {
                currentUserData = await res.json();
                // --- نظام كشف التفعيل الذكي (الصفحة الرئيسية) ---
                const banner = document.getElementById("activation-banner");
                if (banner) {
                    if (!currentUserData.is_verified) {
                        // 1. إظهار التنبيه فوراً
                        banner.style.display = "block";
                        document.body.classList.add("has-banner");
                        
                        // 2. تحديث رابط الواتساب
                        const waLink = document.getElementById("whatsapp-verify-link");
                        if (waLink) {
                            waLink.href = `https://wa.me/970594060648?text=مرحباً KAIA، لقد سجلت وأريد تفعيل حسابي: ${currentUserData.email}`;
                        }

                        // 3. حماية إضافية: تعطيل زر تجربة المحرك (Demo) في الصفحة الرئيسية
                        const demoBtn = document.getElementById("run-btn");
                        if (demoBtn) {
                            demoBtn.innerText = "بانتظار تفعيل الحساب ⏳";
                            demoBtn.style.opacity = "0.5";
                            demoBtn.style.pointerEvents = "none";
                        }
                    } else {
                        // إذا كان الحساب مفعلاً، نخفي التنبيه تماماً
                        banner.style.display = "none";
                        document.body.classList.remove("has-banner");
                    }
                }
                // -----------------------------------------------
                
                if (demoArea) {
                    if (currentUserData.tier === "Trial") {
                        demoArea.style.display = "block";
                    } else {
                        demoArea.style.display = "none";
                    }
                }

                let adminBtn = "";
                if (currentUserData.is_admin === true) {
                    adminBtn = `
                        <button class="wallet-btn" onclick="window.location.href='/admin'" 
                                style="background: #ff3131; color: white; border: 1px solid white; font-weight:900; box-shadow: 0 0 15px rgba(255,49,49,0.4);">
                            <i class="fa-solid fa-user-shield"></i> ${currentLang === 'ar' ? 'لوحة السيطرة' : 'Admin'}
                        </button>
                    `;
                }

                authZone.innerHTML = `
                    <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                        <button id="logout-btn" class="nav-btn-logout" title="${dict.nav_logout || 'Logout'}">
                            <i class="fa-solid fa-power-off"></i>
                        </button>
                        ${adminBtn}
                        <button class="wallet-btn" onclick="location.href='/dashboard'">
                            <i class="fa-solid fa-gauge-high"></i> ${dict.nav_dashboard || 'Dashboard'}
                        </button>
                        <span style="font-weight:800; color:white;">
                            ${dict.nav_welcome || 'Welcome'}, <span style="color:var(--primary)">${currentUserData.full_name}</span>
                        </span>
                        <span style="color:var(--platinum-color); font-weight:900; border: 1px solid var(--platinum-color); padding: 4px 8px; border-radius: 8px; background: rgba(255,215,0,0.05);">
                            <i class="fa-solid fa-coins"></i> ${currentUserData.credits}
                        </span>
                    </div>
                `;

                if (accessArea) {
                    if (currentUserData.tier !== "Trial" || currentUserData.is_admin === true) {
                        accessArea.style.display = "block";
                    } else {
                        accessArea.style.display = "none";
                    }
                }

                $("logout-btn").onclick = () => { 
                    localStorage.removeItem("token"); 
                    location.reload(); 
                };
                return;
            }
        } catch (e) { 
            console.error("Auth UI Sync Error:", e);
            localStorage.removeItem("token"); 
        }
    }

    authZone.innerHTML = `<button class="wallet-btn" id="open-auth-btn"><i class="fa-solid fa-user-circle"></i> ${dict.nav_login || 'Login'}</button>`;
    if (accessArea) accessArea.style.display = "none";
    if (demoArea) demoArea.style.display = "none";
    
    if ($("open-auth-btn")) {
        $("open-auth-btn").onclick = () => { 
            isRegisterMode = false; 
            updateAuthModalState(); 
            $("auth-modal").style.display = "flex"; 
        };
    }
}

function toggleAuthMode() {
    isRegisterMode = !isRegisterMode;
    updateAuthModalState();
}

function updateAuthModalState() {
    const dict = (typeof translations !== 'undefined') ? translations[currentLang] : {};
    
    const fields = ["name-field-wrap", "whatsapp-field-wrap", "country-field-wrap", "pass-confirm-field-wrap"];
    fields.forEach(id => { 
        if($(id)) $(id).style.display = isRegisterMode ? "block" : "none"; 
    });

    if ($("modal-title")) $("modal-title").innerText = isRegisterMode ? (dict.auth_toggle_reg || "Register") : (dict.auth_title || "Login");
    if ($("auth-submit-btn")) $("auth-submit-btn").innerText = isRegisterMode ? (dict.auth_submit || "Confirm") : (dict.nav_login || "Login");
    if ($("auth-toggle-text")) $("auth-toggle-text").innerText = isRegisterMode ? (dict.auth_toggle_login || "Login") : (dict.auth_toggle_reg || "Register");

    const paymentSection = $("payment-info-section");
    const authSide = $("auth-side-container");

    if (paymentSection) {
        if (authToken && selectedPlan.name !== "Trial") {
            if (authSide) authSide.style.display = "none"; 
            paymentSection.style.display = "block";
            let bankText = (dict.bank_desc || "You selected {plan} for ${price}")
                           .replace("{plan}", selectedPlan.name)
                           .replace("{price}", selectedPlan.price);

            paymentSection.innerHTML = `
                <h3 style="color:var(--primary); font-weight:900; margin-bottom:15px;">${dict.bank_title || 'Payment Info'}</h3>
                <p style="font-size:14px; line-height:1.6; color:#fff; margin-bottom:20px;">${bankText}</p>
                <a href="https://wa.me/970594060648?text=Hello, I want to activate ${selectedPlan.name} plan" 
                   target="_blank" class="btn-glow-access" style="font-size:16px; padding:15px 25px; width:100%; text-align:center; display:block; text-decoration:none;">
                   <i class="fa-brands fa-whatsapp"></i> ${dict.bank_whatsapp_btn || 'Send Receipt'}
                </a>
                <p style="font-size:12px; color:var(--muted); margin-top:15px;">${dict.bank_notice || 'Activation after review.'}</p>
            `;
        } else if (isRegisterMode && selectedPlan.name !== "Trial") {
            if (authSide) authSide.style.display = "block";
            paymentSection.style.display = "block";
            let bankText = (dict.bank_desc || "You selected {plan} for ${price}")
                           .replace("{plan}", selectedPlan.name)
                           .replace("{price}", selectedPlan.price);

            paymentSection.innerHTML = `
                <h3 style="color:var(--primary); font-weight:900; margin-bottom:15px;">${dict.bank_title || 'Payment Info'}</h3>
                <p style="font-size:14px; line-height:1.6; color:#fff; margin-bottom:20px;">${bankText}</p>
                <p style="font-size:12px; color:var(--muted); margin-top:15px;">${dict.bank_notice || 'Activation after review.'}</p>
            `;
        } else {
            if (authSide) authSide.style.display = "block";
            paymentSection.style.display = "none";
        }
    }
}

async function handleAuthSubmit() {
    const rawEmail = $("auth-email")?.value || "";
    const email = rawEmail.trim().toLowerCase();
    const pass = $("auth-pass")?.value;
    const passConfirm = $("auth-pass-confirm")?.value; // جلب قيمة تأكيد كلمة المرور
    
    if (!email || !pass) {
        alert(currentLang === "ar" ? "يرجى إدخال كافة البيانات المطلوبة" : "Please fill all required data");
        return;
    }

    try {
        if (isRegisterMode) {
            // [حماية المتصفح] التحقق من تطابق كلمتي المرور قبل الإرسال
            if (pass !== passConfirm) {
                alert(currentLang === "ar" ? "عذراً، كلمتا المرور غير متطابقتين" : "Passwords do not match");
                return;
            }

            const res = await fetch("/api/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: email,
                    password: pass,
                    confirm_password: passConfirm, // إرسال حقل التأكيد للسيرفر
                    full_name: $("auth-fullname").value || "Trader",
                    phone: "000",
                    whatsapp: $("auth-whatsapp").value || "",
                    country: $("auth-country").value || "Global",
                    tier: selectedPlan.name 
                })
            });
            
            const data = await res.json();
            
            if (res.ok) {
                alert(currentLang === "ar" ? "تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول." : "Success! Please login now.");
                isRegisterMode = false;
                updateAuthModalState();
            } else { 
                alert(data.detail || "Error"); 
            }
            
        } else {
            const fd = new FormData();
            fd.append("username", email);
            fd.append("password", pass);
            
            const res = await fetch("/api/login", { method: "POST", body: fd });
            const data = await res.json();
            
            if (res.ok) {
                localStorage.setItem("token", data.access_token);
                location.reload();
            } else { 
                alert(data.detail || "Login Failed"); 
            }
        }
    } catch (e) { 
        alert("Server Connection Error. Please check your internet."); 
    }
}

/* ------------------------------------------------------------
   5. محرك تحليل الشارت (Demo Experience)
   ------------------------------------------------------------ */
function initUploadEngine() {
    const dropZone = $("drop-zone");
    const fileInput = $("chartUpload");
    if (!dropZone || !fileInput) return;

    dropZone.onclick = () => fileInput.click();
    
    dropZone.ondragover = (e) => { e.preventDefault(); dropZone.style.borderColor = "var(--primary)"; };
    dropZone.ondragleave = () => { dropZone.style.borderColor = "var(--border)"; };
    dropZone.ondrop = (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length) { 
            fileInput.files = e.dataTransfer.files; 
            updateStatus(fileInput.files[0].name); 
        }
    };

    document.addEventListener('paste', (e) => {
        const item = Array.from(e.clipboardData.items).find(x => x.type.indexOf("image") !== -1);
        if (item) {
            const blob = item.getAsFile();
            const reader = new FileReader();
            reader.onload = (event) => {
                if (dropZone) {
                    dropZone.style.backgroundImage = `url(${event.target.result})`;
                    dropZone.style.backgroundSize = "contain";
                    dropZone.style.backgroundRepeat = "no-repeat";
                    dropZone.style.backgroundPosition = "center";
                }
            };
            reader.readAsDataURL(blob);
            const dt = new DataTransfer(); 
            dt.items.add(blob);
            fileInput.files = dt.files; 
            updateStatus("Image Pasted ✅");
        }
    });

    fileInput.onchange = () => {
        if(fileInput.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (dropZone) {
                    dropZone.style.backgroundImage = `url(${e.target.result})`;
                    dropZone.style.backgroundSize = "contain";
                    dropZone.style.backgroundRepeat = "no-repeat";
                    dropZone.style.backgroundPosition = "center";
                }
            };
            reader.readAsDataURL(fileInput.files[0]);
            updateStatus(fileInput.files[0].name);
        }
    };

    function updateStatus(n) { 
        if($("status-text")) { 
            $("status-text").innerText = n; 
            $("status-text").style.color = "var(--success)"; 
        } 
    }
}

async function runDemoAnalysis() {
    if (!authToken) { 
        alert(currentLang === 'ar' ? "يرجى تسجيل الدخول أو إنشاء حساب مجاني للتجربة" : "Please login or register to try"); 
        isRegisterMode = false;
        updateAuthModalState();
        return $("auth-modal").style.display="flex"; 
    }

    if (currentUserData && currentUserData.tier === "Trial" && currentUserData.credits <= 0 && !currentUserData.is_admin) {
        alert(currentLang === 'ar' ? "لقد استنفدت جميع التحليلات المجانية المتاحة لك (3/3). يرجى ترقية باقتك للاستمرار." : "You have exhausted all free analyses (3/3). Please upgrade your plan to continue.");
        return;
    }
    
    const fileInput = $("chartUpload");
    if (!fileInput.files.length) return alert("Please upload chart image first");

    const btn = $("run-btn");
    btn.disabled = true; 
    btn.innerText = "KAIA ANALYZING...";

    try {
        const upFd = new FormData(); 
        upFd.append("chart", fileInput.files[0]);
        const uploadRes = await fetch("/api/upload-chart", { method: "POST", body: upFd });
        const { filename } = await uploadRes.json();

        const anFd = new FormData();
        anFd.append("filename", filename);
        anFd.append("timeframe", $("timeframe").value);
        anFd.append("analysis_type", $("strategy").value);
        anFd.append("lang", currentLang);

        const res = await fetch("/api/analyze-chart", { 
            method: "POST", 
            headers: { "Authorization": "Bearer " + authToken }, 
            body: anFd 
        });
        
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.detail);

        if (currentUserData) currentUserData.credits = data.remaining_credits;

        $("result-box").style.display = "block";

        const analysis = (data && typeof data.analysis === "object" && data.analysis) ? data.analysis : null;

        const signalText = (analysis && typeof analysis.market_bias === "string")
            ? analysis.market_bias
            : ((typeof data.signal === "string") ? data.signal : "");

        const structureText = (analysis && typeof analysis.market_phase === "string")
            ? analysis.market_phase
            : ((typeof data.structure === "string") ? data.structure : "");

        const zonesText = (analysis && typeof analysis.opportunity_context === "string")
            ? analysis.opportunity_context
            : ((typeof data.key_zones === "string") ? data.key_zones : "");

        const reasonText = (analysis && typeof analysis.analysis_text === "string")
            ? analysis.analysis_text
            : ((typeof data.reason === "string") ? data.reason : "");

        const safeSignal = (typeof signalText === "string") ? signalText : "";
        const biasClass = safeSignal.toLowerCase().includes('buy')
            ? 'bullish-glow'
            : (safeSignal.toLowerCase().includes('sell') ? 'bearish-glow' : '');
        
        $("res-data-content").innerHTML = `
            <div class="analysis-result-card ${biasClass}">
                <button class="close-res-btn" onclick="document.getElementById('result-box').style.display='none'">×</button>
                <h3 style="color:var(--primary); text-align:center; font-weight:900; margin-bottom:15px; letter-spacing:1px;">KAIA AI REPORT</h3>
                <div class="res-data-grid">
                    <div class="res-data-item"><small>Bias/Signal</small><span>${signalText || 'N/A'}</span></div>
                    <div class="res-data-item"><small>Structure</small><span>${structureText || 'N/A'}</span></div>
                    <div class="res-data-item" style="grid-column: span 2;"><small>Zones</small><span>${zonesText || 'N/A'}</span></div>
                </div>
                <div style="background:rgba(2,6,23,0.7); padding:20px; border-radius:15px; margin-top:15px; border:1px solid var(--border);">
                    <strong style="color:var(--primary); display:block; margin-bottom:5px;">Institutional Narrative:</strong>
                    <p style="font-size:15px; line-height:1.7;">${reasonText || ''}</p>
                </div>
            </div>
        `;
        $("result-box").scrollIntoView({ behavior: "smooth" });
        
    } catch (e) { 
        alert(e.message); 
    } finally { 
        btn.disabled = false; 
        btn.innerText = "Analyze Now"; 
        updateUIBasedOnAuth();
    }
}

/* ------------------------------------------------------------
   6. التشغيل الابتدائي عند تحميل الصفحة
   ------------------------------------------------------------ */
window.onload = async () => {
    try {
        applyTranslations(currentLang);
        runIntroSequence();
        
        await updateUIBasedOnAuth();

        if ($("language-select")) {
            $("language-select").onchange = (e) => { 
                applyTranslations(e.target.value); 
                location.reload(); 
            };
        }
        
        if ($("auth-submit-btn")) $("auth-submit-btn").onclick = handleAuthSubmit;
        if ($("auth-toggle-text")) $("auth-toggle-text").onclick = toggleAuthMode;
        if ($("close-modal")) $("close-modal").onclick = () => $("auth-modal").style.display = "none";
        if ($("run-btn")) $("run-btn").onclick = runDemoAnalysis;

        document.querySelectorAll(".plan-btn").forEach(btn => {
            btn.onclick = () => {
                selectedPlan = { 
                    name: btn.getAttribute("data-plan"), 
                    price: btn.getAttribute("data-price") 
                };
                if (authToken) { 
                    isRegisterMode = false; 
                } else { 
                    isRegisterMode = true; 
                }
                updateAuthModalState();
                $("auth-modal").style.display = "flex";
            };
        });

        initUploadEngine();
        
    } catch (err) { 
        console.error("Critical Initialization Error:", err); 
    } finally { 
        setTimeout(hidePreloader, 800); 
    }
};

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(() => console.log("KAIA AI App Ready"))
    .catch((err) => console.log("PWA Error", err));
}