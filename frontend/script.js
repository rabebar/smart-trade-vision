/* =========================================================
   SmartTrade Vision – script.js (مع نظام الاشتراكات والدفع)
   ========================================================= */

let uploadedFilename = "";
let authToken = localStorage.getItem("token") || "";
let userCredits = 0;
let currentLang = "ar";

/* =========================================
   1. القاموس (عربي / إنجليزي)
   ========================================= */
const translations = {
    ar: {
        title: "تحليل الشارت الذكي",
        subtitle: "ارفع صورة الشارت ودع الذكاء الاصطناعي يكتشف الفرص",
        drag_drop: "اضغط هنا لاختيار الصورة",
        upload_btn: "رفع الصورة",
        analysis_label: "نوع التحليل المطلوب",
        run_btn: "بدء التحليل",
        analyzing: "جاري التحليل بواسطة AI...",
        result_title: "نتائج التوصية",
        signal: "الإشارة",
        entry: "الدخول",
        sl: "الوقف (SL)",
        tp: "الهدف (TP)",
        chart_img: "الشارت المعالج:",
        close_btn: "إغلاق النتيجة",
        ad_space: "مساحة إعلانية",
        lang_btn_text: "English"
    },
    en: {
        title: "Smart Chart Analysis",
        subtitle: "Upload your chart and let AI detect opportunities",
        drag_drop: "Click here to select an image",
        upload_btn: "Upload Image",
        analysis_label: "Analysis Strategy",
        run_btn: "Run Analysis",
        analyzing: "Analyzing with AI...",
        result_title: "Trade Recommendation",
        signal: "Signal",
        entry: "Entry",
        sl: "Stop Loss",
        tp: "Take Profit",
        chart_img: "Processed Chart:",
        close_btn: "Close Result",
        ad_space: "Advertisement Space",
        lang_btn_text: "العربية"
    }
};

/* =========================================
   2. تغيير اللغة
   ========================================= */
document.getElementById("lang-btn").addEventListener("click", () => {
    currentLang = currentLang === "ar" ? "en" : "ar";
    updateLanguage();
});

function updateLanguage() {
    const t = translations[currentLang];
    document.documentElement.dir = currentLang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = currentLang;

    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.getAttribute("data-i18n");
        if (t[key]) el.innerText = t[key];
    });

    document.getElementById("lang-text").innerText = t.lang_btn_text;
}

/* =========================================
   3. نظام الدخول (Login)
   ========================================= */
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const msg = document.getElementById("auth-msg");

    msg.innerText = "جاري تسجيل الدخول...";

    try {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const response = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            msg.innerText = data.detail || "فشل تسجيل الدخول";
            return;
        }

        authToken = data.access_token;
        userCredits = data.credits;

        localStorage.setItem("token", authToken);

        document.getElementById("credits-count").innerText = userCredits;
        document.getElementById("auth-overlay").classList.add("hidden");
        document.getElementById("user-info").classList.remove("hidden");
        msg.innerText = "";

    } catch (err) {
        msg.innerText = "خطأ في الاتصال بالسيرفر";
    }
});

/* =========================================
   4. تسجيل الخروج
   ========================================= */
document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    location.reload();
});

/* =========================================
   5. رفع الصورة (Upload)
   ========================================= */
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("chartUpload");

dropZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        dropZone.querySelector("p").innerText = "✅ " + fileInput.files[0].name;
        dropZone.style.borderColor = "#10b981";
    }
});

document.getElementById("uploadBtn").addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) {
        alert(currentLang === "ar" ? "يرجى اختيار ملف!" : "Please select a file!");
        return;
    }

    const formData = new FormData();
    formData.append("chart", file);

    try {
        const response = await fetch("/api/upload-chart", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (data.status === "uploaded") {
            uploadedFilename = data.filename;
            alert(currentLang === "ar" ? "تم الرفع بنجاح!" : "Uploaded Successfully!");
        }
    } catch (err) {
        alert("Upload error");
    }
});

/* =========================================
   6. تشغيل التحليل (Analysis)
   ========================================= */
document.getElementById("run-btn").addEventListener("click", async () => {
    if (!authToken) {
        alert("يجب تسجيل الدخول أولاً");
        return;
    }

    if (!uploadedFilename) {
        alert(currentLang === "ar" ? "يجب رفع الصورة أولاً!" : "Please upload first!");
        return;
    }

    const analysisType = document.getElementById("analysis-type").value;
    document.getElementById("loading-box").classList.remove("hidden");
    document.getElementById("result-box").classList.add("hidden");

    const formData = new FormData();
    formData.append("filename", uploadedFilename);
    formData.append("analysis_type", analysisType);

    try {
        const response = await fetch("/api/analyze-chart", {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + authToken
            },
            body: formData
        });

        const data = await response.json();
        document.getElementById("loading-box").classList.add("hidden");

        // 👈👈 التعديل هنا: إذا انتهى الرصيد نفتح نافذة الدفع فوراً
        if (data.detail === "OUT_OF_CREDITS") {
            document.getElementById("subscription-modal").classList.remove("hidden");
            return;
        }

        if (data.status === "success") {
            document.getElementById("r-signal").innerText = data.signal;
            document.getElementById("r-entry").innerText = data.entry;
            document.getElementById("r-sl").innerText = data.stop_loss;
            document.getElementById("r-tp").innerText = data.take_profit;

            if (data.remaining_credits !== undefined) {
                userCredits = data.remaining_credits;
                document.getElementById("credits-count").innerText = userCredits;
            }

            document.getElementById("processed-img").src =
                "/" + data.file + "?t=" + Date.now();

            document.getElementById("result-box").classList.remove("hidden");
        }

    } catch (err) {
        document.getElementById("loading-box").classList.add("hidden");
        alert("Analysis error");
    }
});

/* =========================================
   7. إغلاق النتيجة
   ========================================= */
document.getElementById("close-result").addEventListener("click", () => {
    document.getElementById("result-box").classList.add("hidden");
});

/* =========================================
   8. تسجيل الدخول التلقائي
   ========================================= */
if (authToken) {
    fetch("/api/me", {
        headers: { "Authorization": "Bearer " + authToken }
    })
    .then(res => res.ok ? res.json() : null)
    .then(user => {
        if (user) {
            userCredits = user.credits;
            document.getElementById("credits-count").innerText = userCredits;
            document.getElementById("auth-overlay").classList.add("hidden");
            document.getElementById("user-info").classList.remove("hidden");
        } else {
            localStorage.removeItem("token");
        }
    });
}

/* =========================================
   9. نظام التسجيل (Register)
   ========================================= */
const toggleBtn = document.getElementById("toggle-auth-btn");
const loginForm = document.getElementById("login-form");
const regForm = document.getElementById("register-form");
const authTitle = document.getElementById("auth-title");

toggleBtn.addEventListener("click", () => {
    loginForm.classList.toggle("hidden");
    regForm.classList.toggle("hidden");
    
    if (loginForm.classList.contains("hidden")) {
        authTitle.innerText = currentLang === "ar" ? "إنشاء حساب جديد" : "Create Account";
        toggleBtn.innerText = currentLang === "ar" ? "تسجيل الدخول" : "Login";
    } else {
        authTitle.innerText = currentLang === "ar" ? "تسجيل الدخول" : "Login";
        toggleBtn.innerText = currentLang === "ar" ? "أنشئ حساباً مجاناً" : "Create Account";
    }
});

regForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const msg = document.getElementById("auth-msg");

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, password: password })
        });

        if (response.ok) {
            alert("تم إنشاء الحساب بنجاح! قم بتسجيل الدخول الآن.");
            toggleBtn.click();
        } else {
            const data = await response.json();
            msg.innerText = data.detail || "فشل إنشاء الحساب";
        }
    } catch (err) {
        msg.innerText = "خطأ في الاتصال";
    }
});

/* =========================================
   10. منطق نافذة الاشتراك والدفع (جديد 💰)
   ========================================= */
const subModal = document.getElementById("subscription-modal");
const upgradeBtn = document.getElementById("upgrade-btn");
const closeSubBtn = document.getElementById("close-sub");
const copyIbanBtn = document.getElementById("copy-iban-btn");

// فتح النافذة عند الضغط على زر الترقية
upgradeBtn.addEventListener("click", () => {
    subModal.classList.remove("hidden");
});

// إغلاق النافذة
closeSubBtn.addEventListener("click", () => {
    subModal.classList.add("hidden");
});

// إغلاق النافذة عند الضغط خارج المربع
window.addEventListener("click", (e) => {
    if (e.target === subModal) {
        subModal.classList.add("hidden");
    }
});

// نسخ الآيبان
copyIbanBtn.addEventListener("click", () => {
    const ibanInput = document.getElementById("iban-addr");
    ibanInput.select();
    ibanInput.setSelectionRange(0, 99999); // للهواتف
    
    navigator.clipboard.writeText(ibanInput.value).then(() => {
        const originalText = copyIbanBtn.innerHTML;
        copyIbanBtn.innerHTML = '<i class="fa-solid fa-check"></i> تم النسخ';
        setTimeout(() => {
            copyIbanBtn.innerHTML = originalText;
        }, 2000);
    });
});