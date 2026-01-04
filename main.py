# =================================================================
# 🛰️ KAIA AI – THE ULTIMATE INSTITUTIONAL ANALYST ENGINE
# 🛡️ VERSION: 2025.12.31 - KAIA MASTER PLATINUM VISION (STEP 1)
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
# دالة تطهير النصوص: تحذف أي كود HTML أو تنسيقات خارجية لمنع تشوه الموقع
def clean_html_content(text: str):
    if not text:
        return ""
    # حذف كافة أوسمة HTML (مثل <div> و <span> و <button>)
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # تنظيف المسافات الزائدة لضمان مظهر احترافي
    return " ".join(text.split())
# دالة تثبيت المخرجات: تضمن استخدام القاموس السيادي وحماية الواجهة من الانهيار
def normalize_kaia_output(result: dict, timeframe: str):
    defaults = {
        "market": result.get("market", "Asset"),
        "timeframe": result.get("timeframe", timeframe),
        "market_state": {
            "directional_bias": "قيد الفحص",
            "notes": "",
            "economic_context": "لا توجد أحداث مؤثرة حالياً",
            "session_hint": "غير واضح",
            "validity_candles": f"≈ 6–18 شمعة على {timeframe}"
        },
        "zones": {"supply": [], "demand": []},
        "institutional_evidence": {"bos": [], "choch": [], "fvg": [], "liquidity": []},
        "key_levels": {"upside": [], "downside": []},
        "stop_hunt_risk_zones": [],
        "execution_blueprint": {
            "setup_name": "رؤية كايا الحالية",
            "bias": "قيد الفحص", 
            "نقطة_انطلاق_مناسبة": "تحت المراقبة", 
            "شرط_التغير_الهيكلي": "قيد الفحص",
            "مستوى_سعر_يبطل_التحليل": "غير محدد", 
            "سعر_مستهدف_تستهدفه_المؤسسات": [], 
            "صلاحية_الرؤية": f"Intraday ({timeframe})",
            "ملاحظة_المخاطر": "تنبيه: تحرك السيولة المؤسسية عالي المخاطر"
        },
        "confidence_score": 50
    }

    # دمج البيانات القادمة من الذكاء الاصطناعي مع القالب الافتراضي
    out = defaults
    for k, v in result.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v

    # تأمين قوائم العرض والطلب لضمان استقرار العرض
    if "zones" in out:
        for key in ["supply", "demand"]:
            if not isinstance(out["zones"].get(key), list):
                out["zones"][key] = []
            
    return out
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
def get_news(lang: str = "ar", db: Session = Depends(get_db)):
    # النظام يعمل فقط للنسخة العربية حالياً بناءً على طلب المدير
    if lang != "ar":
        return {"news": "KAIA AI: Monitoring global markets..."}

    global NEWS_CACHE
    now = datetime.now()
    cache_entry = NEWS_CACHE["ar"]
    
    # تحديث الكاش كل 10 دقائق لضمان السرعة وعدم الضغط على المصادر
    if cache_entry["timestamp"] and (now - cache_entry["timestamp"]).seconds < 600:
        return {"news": cache_entry["data"]}

    try:
        final_ticker_items = []

        # 1. جلب آخر 3 مقالات من تقاريرك الخاصة أولاً
        my_articles = db.query(Article).filter(Article.language == "ar").order_by(Article.id.desc()).limit(3).all()
        for art in my_articles:
            final_ticker_items.append(f"🔥 من تقارير المحلل: {art.title}")

        # 2. الكلمات المفتاحية الاستراتيجية المحددة من قبل المدير
        keywords = [
            "بطالة", "تضخم", "تداول", "بورصة", "بنك", "أسعار", "اتفاقيات", 
            "تجارة", "رجال أعمال", "رجل أعمال", "هبوط", "ارتفاع", "مؤشرات", 
            "صناديق استثمارية", "سيولة", "الفيدرالي", "الذهب", "النفط"
        ]

        # 3. مصادر الأخبار الكبرى (سكاي نيوز الاقتصادية و Investing)
        rss_sources = [
            "https://www.skynewsarabia.com/web/rss/business.xml", # سكاي نيوز اقتصاد
            "https://sa.investing.com/rss/news_1.rss"             # انفستنج أخبار عامة
        ]
            
        headers = {"User-Agent": "Mozilla/5.0"}
        
        for url in rss_sources:
            try:
                response = requests.get(url, timeout=5, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "xml")
                    items = soup.find_all("item")
                    for i in items[:15]:
                        title = i.title.text.strip()
                        # فلترة الخبر بناءً على الكلمات المفتاحية
                        if any(key in title for key in keywords):
                            clean_t = title.replace("'", "").replace('"', "")
                            # تمييز العاجل
                            if "عاجل" in clean_t:
                                clean_t = f"🚨 [عاجل] {clean_t.replace('عاجل', '').strip()}"
                            final_ticker_items.append(clean_t)
            except: continue

        if final_ticker_items:
            # دمج الأخبار بفاصل النجمة الفخمة
            final_text = " ★ ".join(final_ticker_items)
            NEWS_CACHE["ar"]["data"] = final_text
            NEWS_CACHE["ar"]["timestamp"] = now
            return {"news": final_text}
            
    except Exception as e:
        print(f"News Engine Error: {e}")
            
    return {"news": NEWS_CACHE["ar"]["data"]}


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
# 8. نظام التسجيل والحماية الذكي (Auth & IP Tracking) - النسخة المحدثة
# -----------------------------------------------------------------

@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    clean_email = user.email.lower().strip()
    client_ip = request.client.host or "0.0.0.0"

    # [نقطة التفتيش] التحقق من تطابق الباسوورد (الخانة الأولى مع الخانة الثانية)
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="عذراً، كلمتا المرور غير متطابقتين")

    # التحقق من وجود الحساب مسبقاً
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل لدينا بالفعل")

    # تحديد الرصيد بناءً على الباقة
    credits_map = {"Trial": 3, "Basic": 20, "Pro": 40, "Platinum": 200}
    
    # إنشاء المستخدم الجديد
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
    
    # خريطة الرصيد المعتمدة
    credits_map = {"Trial": 3, "Basic": 20, "Pro": 40, "Platinum": 200}
    
    # إذا تغيرت الباقة، قم بتحديث الرصيد تلقائياً حسب الخريطة
    new_tier = data.get("tier", user.tier)
    if new_tier != user.tier:
        user.tier = new_tier
        user.credits = credits_map.get(new_tier, user.credits)
    else:
        # إذا لم تتغير الباقة، اسمح بتعديل الرصيد يدوياً كما هو
        user.credits = data.get("credits", user.credits)

    user.is_premium = (user.tier != "Trial")
    user.is_whale = (user.tier == "Platinum")

    # --- إضافة حفظ البيانات المالية الجديدة (CRM) ---
    if "subscription_fee" in data:
        user.subscription_fee = float(data.get("subscription_fee", 0.0))
    if "payment_status" in data:
        user.payment_status = data.get("payment_status", "Unpaid")
    
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
        # تنظيف الملخص والمحتوى من أي أكواد خارجية قبل الحفظ
        summary=clean_html_content(data.get("summary")), 
        content=clean_html_content(data.get("content")), 
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
        "summary": clean_html_content(data.get("summary")), 
        "content": clean_html_content(data.get("content")), 
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

    if analysis_type == "KAIA Master" and current_user.tier != "Platinum":
        msg = "عذراً، استراتيجية KAIA Master Vision مخصصة حصرياً لمشتركي الباقة البلاتينية." if lang == "ar" else "Sorry, KAIA Master is for Platinum members."
        return {"status": "upgrade_required", "detail": msg}

    img_path = os.path.join(STORAGE_PATH, filename)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="الصورة غير موجودة")

    try:
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

 # --- البرومبت الاحترافي: إجبار ملء الخانات (Force Fill) ---
        if analysis_type == "KAIA Master":
            system_prompt = f"""
أنت "KAIA SMART Platinum" — محلل سوق خوارزمي (SMC).
هدفك: تقديم خطة تداول واضحة وملء جميع حقول JSON بدقة وتفصيل.

القواعد اللغوية (إلزامي):
- لغة الرد: ({lang}).
- المصطلحات التقنية: اشرحها باختصار.

قواعد المنطق (Decision Logic):
1. إذا الشارت غير واضح: اكتب "NO TRADE".
2. الهدف (TP) يجب أن يكون أكبر من الوقف (SL).

تعليمات تعبئة JSON (ممنوع ترك أي حقل فارغ أو وضع نقاط ...):

1) market_state.notes (الواجهة الرئيسية):
   - التنسيق الإجباري (مع الحفاظ على الأسطر):
     "🔴 القرار: [SHORT / LONG / NO TRADE]
      ⚡ المنطقة: [Zone X to Y]
      🛑 الوقف: [Price]
      🎯 الأهداف: [TP1, TP2]
      📝 الخلاصة: [شرح مبسط في سطرين]"

2) institutional_evidence:
   - صف حالة BOS, CHOCH, FVG.
   - إذا لم يوجد، اكتب: "لا يوجد نموذج حالياً" (ممنوع تركها فارغة).

3) key_levels (ربط البيانات):
   - يجب أن تحتوي القوائم (upside/downside) على نفس الأرقام المذكورة في "الأهداف" و"الوقف".
   - الصيغة داخل القائمة: "السعر - الوصف (هدف/وقف/دعم) - الأكشن".

4) scenarios (التفصيل):
   - السيناريو 1: اشرح خطة الدخول المذكورة في القرار (لماذا دخلنا هنا؟).
   - السيناريو 2: اشرح سيناريو الإلغاء (Invalidation).
   - *تحذير: ممنوع كتابة "..." نهائياً.*

5) stop_hunt_risk_zones:
   - حدد مناطق تجميع السيولة القريبة.

صيغة الإخراج JSON فقط:
(market, timeframe, market_state, institutional_evidence, key_levels, stop_hunt_risk_zones, scenarios, confidence_score)
"""

        else:
            system_prompt = f"أنت خبير تحليل فني. حلل الشارت بأسلوب {analysis_type} باللغة ({lang}). أعد JSON حصراً بمفاتيح: (market_bias, analysis_text, market, timeframe)."

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": [{"type": "text", "text": f"Analyze this {analysis_type} chart on {timeframe}"},
                                                 {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}] } ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        # 1. تحويل الرد إلى JSON وتمريره عبر "فلتر التثبيت" لضمان القاموس السيادي
        raw_result = json.loads(response.choices[0].message.content)
        result = normalize_kaia_output(raw_result, timeframe)
        
        # 2. تحضير "الخلاصة المدمجة" للسجل (تجمع الخلاصة مع نقطة الانطلاق)
        bp = result.get("execution_blueprint", {})
        notes = result.get("market_state", {}).get("notes", "")
        compact_reason = f"{notes}\n★ نقطة الانطلاق: {bp.get('نقطة_انطلاق_مناسبة')}\n★ الإبطال: {bp.get('مستوى_سعر_يبطل_التحليل')}"
        
        # 3. حفظ التحليل في قاعدة البيانات
        db.add(Analysis(
            user_id=current_user.id, 
            symbol=result.get("market", "Asset"), 
            signal=result.get("market_state", {}).get("directional_bias", bp.get("bias", "Neutral")),
            reason=compact_reason[:500], 
            timeframe=timeframe
        ))
        
        # 4. تحديث إحصائيات الاستهلاك والنشاط (CRM)
        current_user.total_used_analyzes += 1
        current_user.last_active = datetime.now(timezone.utc)

        # 5. خصم الرصيد (إلا إذا كان ملكاً بلاتينياً)
        if not current_user.is_whale: 
            current_user.credits -= 1
            
        db.commit()

        return {
            "status": "success", 
            "analysis": result, 
            "tier_mode": "Platinum" if analysis_type == "KAIA Master" else "Standard"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(img_path): os.remove(img_path)
        
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
def nuclear_wipe(email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # القفل: التأكد أن من يطلب المسح هو أدمن مسجل دخوله
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="غير مسموح لك بالوصول لهذا الأمر السيادي")
    
    target = email.lower().strip()
    user = db.query(User).filter(User.email == target).first()
    if user:
        db.query(Analysis).filter(Analysis.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        return {"message": f"تم مسح الحساب {target} بنجاح"}
    return {"message": "المستخدم غير موجود"}

@app.get("/api/fix-my-account")
def fix_my_account(email: str, new_password: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # القفل: التأكد أن من يطلب الترقية هو أدمن مسجل دخوله
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية للقيام بهذا الإجراء")
    
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

# -----------------------------------------------------------------
# 14. وكيل الذكاء الاصطناعي (KAIA - مدير أعمالك الاستراتيجي)
# -----------------------------------------------------------------

@app.post("/api/chat")
async def chat_with_kaia(data: dict, current_user: User = Depends(get_current_user)):
    # التحقق من الرصيد
    if current_user.credits <= 0 and not current_user.is_whale:
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ للدردشة")

    user_message = data.get("message", "")
    lang = data.get("lang", "ar")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""
        أنت الآن 'KAIA - كبير المخططين الاستراتيجيين والمدير السيادي'. 
        وظيفتك هي العمل كشريك تنفيذي ومحلل مؤسسي عالي المستوى للمتداول الذي يخاطبك (المدير).

        قواعد الشخصية والأداء:
        1. الأسلوب: واثق، مؤسسي، وفخم. خاطب المستخدم بـ (يا مدير، شريكي الاستراتيجي).
        2. التخصص العميق: خبير في سيولة الحيتان (SMC)، مناطق العرض والطلب، والتحليل الزمني لـ KAIA Master.
        3. تحويل التحليل إلى فعل: إذا طلب منك "المدير" صفقة أو توصية أو سألك "ماذا أفعل الآن؟"، قم فوراً بتحويل معطيات 'KAIA Master' إلى (مخطط تنفيذ مؤسسي - Institutional Execution Blueprint).

        هيكل مخطط التنفيذ (يجب الالتزام به عند طلب فرصة):
        - منطقة الاهتمام (Entry Interest): حدد النطاق السعري الأمثل للدخول بناءً على الأوردر بلوك أو سحب السيولة.
        - درع الحماية (Invalidation Point): حدد مستوى إبطال الرؤية الفنية (وقف الخسارة) بدقة.
        - الأهداف السيادية (Target Zones): حدد مستويات جني الأرباح بناءً على مناطق السيولة المستهدفة.
        - إدارة المخاطر: انصح دائماً بإدارة مخاطر صارمة وبأن العائد للمخاطرة يجب أن يكون متفوقاً.

        4. الفلسفة القانونية المحدثة: لا تقل (أنا ممنوع من التوصية)، بل قل: 'بصفتي مدير أعمالك، وظيفتي هي هندسة الصفقة تقنياً بناءً على بصمة المؤسسات، والقرار النهائي للضغط على الزناد هو سيادتك'.
        5. الذكاء الاصطناعي: ادمج دائماً بين "السعر" و"الزمن" في ردودك لإظهار قوة محرك كايا ماستر.
        6. اللغة: الرد حصراً باللغة ({lang}).
        """},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=600
        )

        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================================================================
# 🚀 END OF KAIA MASTER ENGINE - VERSION 2025.12.31 (STEP 1)
# =================================================================