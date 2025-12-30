# =================================================================
# 🛰️ KAIA AI – THE ULTIMATE INSTITUTIONAL ANALYST ENGINE
# 🛡️ VERSION: 2025.12.30 - RESTORED PROMPTS EDITION
# =================================================================

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import shutil
import os
import base64
import json
import requests
import uuid
import re
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# -----------------------------------------------------------------
# 1. إعدادات البيئة وقاعدة البيانات (Environment Setup)
# -----------------------------------------------------------------

load_dotenv()

from database import SessionLocal, User, Analysis, Article, Sponsor
import schemas

# -----------------------------------------------------------------
# 2. إعدادات الحماية والذكاء الاصطناعي (Security & AI)
# -----------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "KAIA_ULTIMATE_SEC_2025")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="KAIA AI – Institutional Analyst Engine")

# -----------------------------------------------------------------
# 3. إعداد مخزن الصور الدائم (Render Disk Persistent Storage)
# -----------------------------------------------------------------

STORAGE_PATH = os.getenv("RENDER_DISK_MOUNT_PATH", "images")

if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH, exist_ok=True)


# -----------------------------------------------------------------
# 4. إعدادات الوسيط والملفات الثابتة (CORS & Static Files)
# -----------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory=STORAGE_PATH), name="images")

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


# -----------------------------------------------------------------
# 5. دوال المساعدة الجوهرية (Core Helpers)
# -----------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email:
            email = email.lower().strip()
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="عذراً، المستخدم غير موجود")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="انتهت الجلسة، يرجى تسجيل الدخول مجدداً")


# -----------------------------------------------------------------
# 6. محرك الأخبار المؤسسي السريع (Institutional News Engine)
# -----------------------------------------------------------------

NEWS_CACHE = {
    "ar": {
        "data": "KAIA AI: نراقب تحركات السيولة والسياسة النقدية الحالية",
        "timestamp": None
    },
    "en": {
        "data": "KAIA AI: Monitoring current liquidity and monetary policy",
        "timestamp": None
    }
}

@app.get("/api/news")
def get_news(lang: str = "ar"):
    global NEWS_CACHE
    lang_key = "en" if lang == "en" else "ar"
    now = datetime.now()
    cache_entry = NEWS_CACHE[lang_key]
    
    if cache_entry["timestamp"]:
        if (now - cache_entry["timestamp"]).seconds < 600:
            return {"news": cache_entry["data"]}

    try:
        if lang_key == "en":
            rss_url = "https://www.investing.com/rss/news_285.rss" 
        else:
            rss_url = "https://sa.investing.com/rss/news_1.rss"
            
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(rss_url, timeout=5, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            titles = []
            for i in items[:15]:
                if i.title:
                    clean_t = i.title.text.strip().replace("'", "").replace('"', "")
                    titles.append(clean_t)
            
            if titles:
                final_text = " ★ ".join(titles)
                NEWS_CACHE[lang_key]["data"] = final_text
                NEWS_CACHE[lang_key]["timestamp"] = now
                return {"news": final_text}
    except Exception:
        pass
            
    return {"news": NEWS_CACHE[lang_key]["data"]}


# -----------------------------------------------------------------
# 7. نظام جلب التقارير الفنية (Public Media API)
# -----------------------------------------------------------------

@app.get("/api/articles")
def get_articles(lang: str = "ar", db: Session = Depends(get_db)):
    return db.query(Article).filter(Article.language == lang).order_by(Article.id.desc()).limit(6).all()


@app.get("/api/sponsors")
def get_sponsors(location: str = "main", db: Session = Depends(get_db)):
    return db.query(Sponsor).filter(Sponsor.location == location, Sponsor.is_active == True).all()


# -----------------------------------------------------------------
# 8. نظام التسجيل والحماية الذكي (Auth & IP Tracking)
# -----------------------------------------------------------------

@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    clean_email = user.email.lower().strip()
    client_ip = request.client.host or "0.0.0.0"
    
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل لدينا بالفعل")

    credits_map = {"Trial": 3, "Basic": 20, "Pro": 40, "Platinum": 200}
    
    new_user = User(
        email=clean_email,
        password_hash=pwd_context.hash(user.password),
        full_name=user.full_name,
        phone=user.phone,
        whatsapp=user.whatsapp,
        country=user.country,
        tier=user.tier,
        credits=credits_map.get(user.tier, 3),
        status="Active",
        is_verified=False,
        registration_ip=client_ip,
        is_admin=False,
        is_premium=(user.tier != "Trial"),
        is_whale=(user.tier == "Platinum")
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@app.post("/api/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    clean_email = form.username.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    return {"access_token": create_access_token(data={"sub": user.email}), "token_type": "bearer"}


@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# -----------------------------------------------------------------
# 9. لوحة التحكم والاشتراكات (Admin Command Center)
# -----------------------------------------------------------------

@app.get("/api/admin/users")
def admin_get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    return db.query(User).all()


@app.post("/api/admin/update_user")
def admin_update_user(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    
    user = db.query(User).filter(User.id == data.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    user.credits = data.get("credits", user.credits)
    user.tier = data.get("tier", user.tier)
    user.is_premium = (data.get("tier") != "Trial")
    user.is_whale = (data.get("tier") == "Platinum")
    
    if "is_verified" in data:
        user.is_verified = data["is_verified"]
        if user.is_verified:
            user.verified_at = datetime.now(timezone.utc)
            user.verification_method = "Manual Admin"
            if not user.subscription_start:
                user.subscription_start = datetime.now(timezone.utc)
                user.subscription_end = datetime.now(timezone.utc) + timedelta(days=30)

    if data.get("renew_subscription") == True:
        now_utc = datetime.now(timezone.utc)
        if user.subscription_end and user.subscription_end > now_utc:
            user.subscription_end = user.subscription_end + timedelta(days=30)
        else:
            user.subscription_end = now_utc + timedelta(days=30)
    
    if "is_flagged" in data:
        user.is_flagged = data["is_flagged"]
    
    db.commit()
    return {"status": "success"}


@app.delete("/api/admin/delete_user/{user_id}")
def admin_delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.query(Analysis).filter(Analysis.user_id == user_id).delete()
        db.delete(user)
        db.commit()
    return {"status": "success"}


# -----------------------------------------------------------------
# 10. غرفة التحرير المؤسسية (Editorial Room)
# -----------------------------------------------------------------

@app.post("/api/admin/add_article")
def admin_add_article(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403, detail="غير مسموح")
    
    new_art = Article(
        title=data.get("title"), 
        summary=data.get("summary"), 
        content=data.get("content"), 
        image_url=data.get("image_url"), 
        language=data.get("language", "ar")
    )
    db.add(new_art)
    db.commit()
    return {"status": "success", "message": "تم نشر المقال بنجاح"}


@app.get("/api/admin/article/{art_id}")
def admin_get_article(art_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    return db.query(Article).filter(Article.id == art_id).first()


@app.put("/api/admin/update_article/{art_id}")
def admin_update_article(art_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    
    db.query(Article).filter(Article.id == art_id).update({
        "title": data.get("title"), 
        "summary": data.get("summary"), 
        "content": data.get("content"), 
        "image_url": data.get("image_url"), 
        "language": data.get("language")
    })
    db.commit()
    return {"status": "success"}


@app.delete("/api/admin/delete_article/{art_id}")
def admin_delete_article(art_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    
    db.query(Article).filter(Article.id == art_id).delete()
    db.commit()
    return {"status": "success"}


@app.post("/api/admin/upload-article-image")
async def upload_article_image(image: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    
    file_name = f"art_{uuid.uuid4()}.png"
    final_save_path = os.path.join(STORAGE_PATH, file_name) 
    
    with open(final_save_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    return {"image_url": f"/images/{file_name}"}


# -----------------------------------------------------------------
# 11. محرك التحليل الذكي المطور (KAIA AI Engine - Tiered Logic)
# -----------------------------------------------------------------

@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...),
    timeframe: str = Form(...),
    analysis_type: str = Form(...),
    lang: str = Form("ar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.credits <= 0 and not current_user.is_whale:
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ، يرجى الترقية")

    # --- حقن بوابة الترقية الذكية ---
    if analysis_type == "KAIA Master" and current_user.tier != "Platinum":
        msg = "عذراً، استراتيجية KAIA Master Vision مخصصة حصرياً لمشتركي الباقة البلاتينية. يرجى الترقية للاستمتاع بالميزات الملكية." if lang == "ar" else "Sorry, KAIA Master Vision is exclusive to Platinum subscribers. Please upgrade to enjoy royal features."
        return {
            "status": "upgrade_required",
            "detail": msg
        }
    img_path = os.path.join(STORAGE_PATH, filename)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="الصورة غير موجودة")

    try:
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

        # --- استعادة البرومبتات الأصلية حرفياً كما كانت في أول نسخة أرسلتها ---
        if analysis_type == "KAIA Master" and current_user.tier == "Platinum":
            system_prompt = f"""
أنت "KAIA AI Institutional Analyst" — مساعد تحليل سوق تعليمي (ليس نصيحة مالية).
حلّل صورة الشارت بأسلوب المؤسسات (SMC/ICT) عبر تتبّع السيولة وبنية السوق،
ثم قدّم مستويات رقمية واضحة للمراقبة صعودًا وهبوطًا + تحذيرات من مناطق محتملة لاصطياد السيولة (Stop-hunt risk).

قواعد صارمة (Legal-Safe):
- لغة الرد: يجب أن يكون الرد كاملاً باللغة ({lang}).
- ممنوع إعطاء توصيات تنفيذية مباشرة (اشترِ/بِع). استخدم لغة مراقبة: (يراقَب/قد يتفاعل).
- مسموح ذكر أرقام مستويات (Prices) كـ "Watch Levels" مع سبب واضح.

منهج التحليل المؤسّسي:
1) حدّد السوق والفريم {timeframe} + حالة السوق.
2) استخرج BOS/CHOCH.
3) حدّد تجمعات السيولة و Liquidity Sweep.
4) حدّد بصمات مؤسسية: Order Block / FVG / Breaker.
5) قدّم المستويات القادمة (Near/Mid/Far) بأرقام واضحة.
6) أضف قسم تحذير Stop-hunt risk zones.
7) قدم سيناريوهين (صعود/هبوط) مع مستوى الإلغاء (Invalidation level).

صيغة الإخراج: أعد ONLY JSON صالح وبنفس المفاتيح التالية حرفياً، وبدون أي نص خارجي:
(market, timeframe, session_context, market_state, institutional_evidence, key_levels, stop_hunt_risk_zones, scenarios, confidence_score, disclaimer)
"""
        elif analysis_type == "Elliott Waves":
            system_prompt = f"""
أنت خبير "KAIA AI Elliott Waves". حلل الشارت المرفق بناءً على نظرية موجات إليوت.
حدد الموجة الحالية (1-5 أو A-C) والأهداف المتوقعة.
يجب أن يكون الرد باللغة ({lang}) وبصيغة JSON حصراً.
المفاتيح المطلوبة: (market_bias, wave_count, analysis_text, risk_note, market, timeframe, confidence)
"""
        else:
            system_prompt = f"""
أنت "KAIA AI Institutional Analyst". حلّل الشارت بأسلوب (SMC/ICT).
يجب أن يكون الرد باللغة ({lang}) وبصيغة JSON حصراً وبالمفاتيح التالية حرفياً:
(market_bias, market_phase, confidence, analysis_text, risk_note, market, timeframe)
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this {analysis_type} chart on {timeframe} timeframe in {lang} language."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        raw_output = response.choices[0].message.content
        
        # --- نظام درع الحماية (Parsing Shield) المضاف فقط لإصلاح خطأ JSON ---
        try:
            # تنظيف أي نصوص زائدة خارج الـ JSON
            match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                result = json.loads(raw_output)
        except Exception as e:
            # إذا فشل التحويل رغم التنظيف، يتم رفع خطأ واضح للسيرفر
            raise HTTPException(status_code=500, detail=f"AI Output Format Error: {str(e)}")

        # --- استكمال منطق التزامن الأصلي لديك دون تغيير ---
        if "market_bias" not in result:
            m_state = result.get("market_state", {})
            if isinstance(m_state, dict):
                result["market_bias"] = m_state.get("directional_bias", "Neutral")
            else:
                result["market_bias"] = str(m_state) if m_state else "Neutral"

        if "analysis_text" not in result:
            m_state = result.get("market_state", {})
            if isinstance(m_state, dict):
                result["analysis_text"] = m_state.get("notes", "Analysis complete")
            else:
                result["analysis_text"] = str(m_state) if m_state else "Institutional view"

        final_market = result.get("market") or "Asset"
        final_bias = result.get("market_bias")
        final_notes = result.get("analysis_text")

        db.add(Analysis(
            user_id=current_user.id,
            symbol=str(final_market),
            signal=str(final_bias),
            reason=str(final_notes),
            timeframe=timeframe
        ))

        if not current_user.is_whale:
            current_user.credits -= 1

        db.commit()

        return {
            "status": "success",
            "analysis": result,
            "tier_mode": "Platinum" if analysis_type == "KAIA Master" else "Standard",
            "remaining_credits": current_user.credits
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(img_path):
            try: os.remove(img_path)
            except: pass

# -----------------------------------------------------------------
# 12. توجيه الصفحات ودعم PWA (المستعادة بالكامل)
# -----------------------------------------------------------------

@app.get("/api/history")
def get_user_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.id.desc()).all()

@app.get("/")
def home_page(): return FileResponse("frontend/index.html")

@app.get("/manifest.json")
def get_manifest(): return FileResponse("frontend/manifest.json")

@app.get("/sw.js")
def get_sw(): return FileResponse("frontend/sw.js")

@app.get("/.well-known/assetlinks.json")
async def get_assetlinks():
    return [{"relation": ["delegate_permission/common.handle_all_urls"],"target": {"namespace": "android_app","package_name": "com.onrender.kaia_ai_app.twa","sha256_cert_fingerprints": ["73:70:D7:27:14:0D:C7:A2:F9:FC:D1:A1:21:B4:1D:18:99:7D:27:38:14:85:E3:40:57:FD:8B:5B:AB:36:3A:0C"]}}]

@app.get("/mobile")
def mobile_page(): return FileResponse("frontend/mobile.html")

@app.get("/dashboard")
def dashboard_page(): return FileResponse("frontend/dashboard.html")

@app.get("/admin")
def admin_page(): return FileResponse("frontend/admin.html")

@app.get("/editor")
def editor_page(): return FileResponse("frontend/editor.html")

@app.get("/history")
def history_page(): return FileResponse("frontend/history.html")

@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    name = f"{uuid.uuid4()}.{chart.filename.split('.')[-1]}"
    save_path = os.path.join(STORAGE_PATH, name)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"filename": name}

# -----------------------------------------------------------------
# 13. أدوات الصيانة الطارئة
# -----------------------------------------------------------------

@app.get("/api/nuclear-wipe")
def nuclear_wipe(email: str, db: Session = Depends(get_db)):
    target = email.lower().strip()
    user = db.query(User).filter(User.email == target).first()
    if user:
        db.query(Analysis).filter(Analysis.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        return {"message": f"تم مسح الحساب {target} بنجاح"}
    return {"message": "المستخدم غير موجود"}

@app.get("/api/fix-my-account")
def fix_my_account(email: str, new_password: str, db: Session = Depends(get_db)):
    target = email.lower().strip()
    user = db.query(User).filter(User.email == target).first()
    if user:
        user.password_hash = pwd_context.hash(new_password)
        user.is_verified = True
        user.is_admin = True
        user.is_whale = True
        user.credits = 9999
        db.commit()
        return {"message": f"تم إصلاح وتفعيل حساب الملك: {target}"}
    return {"error": "لم يتم العثور على الحساب"}

# =================================================================
# 🚀 END OF KAIA MASTER ENGINE - VERSION 2025.12.30
# =================================================================