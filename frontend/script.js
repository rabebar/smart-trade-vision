/* =========================================================
   MrTradeAI – script.js (FIXED LOGIN)
   ========================================================= */

let uploadedFilename = "";
let authToken = localStorage.getItem("token") || "";
let userCredits = 0;
let currentLang = "ar";

/* =========================================
   3. نظام الدخول (Login) ✅ FIXED
   ========================================= */
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const msg = document.getElementById("auth-msg");

    msg.innerText = "جاري تسجيل الدخول...";

    try {
        const formData = new FormData();
        formData.append("username", email);   // OAuth2 requires "username"
        formData.append("password", password);

        const response = await fetch("/api/login", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.access_token) {
            msg.innerText = "فشل تسجيل الدخول";
            return;
        }

        authToken = data.access_token;
        userCredits = data.credits || 0;

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
   8. تسجيل الدخول التلقائي (Auto Login)
   ========================================= */
if (authToken) {
    fetch("/api/me", {
       
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
   تسجيل الخروج
   ========================================= */
document.getElementById("logout-btn").addEventListener("click", () => {
    localStorage.removeItem("token");
    location.reload();
});
