# =========================================================
# KAIA AI – INSTITUTIONAL ANALYST ENGINE
# VERSION: 2025.12.29 - FULL EXPANDED EDITION
# =========================================================

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
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. وتحميل الإعدادات وقاعدة البيانات
# ---------------------------------------------------------
load_dotenv()

from database import SessionLocal, User, Analysis, Article, Sponsor
import schemas

# ---------------------------------------------------------
# 2. إعدادات الحماية والذكاء الاصطناعي
# ---------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "KAIA_ULTIMATE_SEC_2025")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="KAIA AI – Institutional Analyst Engine")

# ---------------------------------------------------------
# 3. إعداد مخزن الصور الدائم (Render Disk)
# ---------------------------------------------------------
# المجلد images سيتم ربطه بالقرص الصلب لضمان عدم ضياع الصور عند التحديث
STORAGE_PATH = os.getenv("RENDER_DISK_MOUNT_PATH", "images")

if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH, exist_ok=True)


# ---------------------------------------------------------
# 4. إعدادات الـ CORS والملفات الثابتة
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط رابط /images بالمجلد الدائم (للشارتات والمقالات)
app.mount("/images", StaticFiles(directory=STORAGE_PATH), name="images")

# ربط مجلد الفرونتيند للملفات الثابتة (css, js, logo)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ---------------------------------------------------------
# 5. دوال المساعدة (Helpers)
# ---------------------------------------------------------

def get_db():
    """فتح اتصال مع قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict):
    """إنشاء توكن دخول صالح لمدة 30 يوماً"""
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """التحقق من هوية المستخدم الحالي عبر التوكن"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email:
            email = email.lower().strip()
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="انتهت الجلسة، يرجى تسجيل الدخول")


# ---------------------------------------------------------
# 6. محرك الأخبار المؤسسي (News Engine with Cache)
# ---------------------------------------------------------

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
    """جلب الأخبار العالمية مع نظام كاش لضمان السرعة القصوى"""
    global NEWS_CACHE
    lang_key = "en" if lang == "en" else "ar"
    
    now = datetime.now()
    cache_entry = NEWS_CACHE[lang_key]
    
    # إذا كانت البيانات في الكاش حديثة (أقل من 10 دقائق)، نرسلها فوراً
    if cache_entry["timestamp"]:
        time_diff = (now - cache_entry["timestamp"]).seconds
        if time_diff < 600:
            return {"news": cache_entry["data"]}

    # إذا كانت قديمة، نقوم بجلب بيانات جديدة من Investing
    try:
        if lang_key == "en":
            rss_url = "https://www.investing.com/rss/news_285.rss" 
        else:
            rss_url = "https://sa.investing.com/rss/news_1.rss"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(rss_url, timeout=5, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            
            titles_list = []
            for item in items[:15]:
                if item.title:
                    clean_t = item.title.text.strip().replace("'", "").replace('"', "")
                    titles_list.append(clean_t)
            
            if titles_list:
                final_news = " ★ ".join(titles_list)
                NEWS_CACHE[lang_key]["data"] = final_news
                NEWS_CACHE[lang_key]["timestamp"] = now
                return {"news": final_news}
                
    except Exception as e:
        print(f"Log: News Fetch Error: {e}")
            
    # في حالة الفشل نرسل آخر بيانات ناجحة مخزنة
    return {"news": NEWS_CACHE[lang_key]["data"]}


# ---------------------------------------------------------
# 7. نظام جلب المقالات والإعلانات (Media API)
# ---------------------------------------------------------

@app.get("/api/articles")
def get_articles(lang: str = "ar", db: Session = Depends(get_db)):
    """جلب أحدث 6 مقالات حسب اللغة"""
    return db.query(Article).filter(Article.language == lang).order_by(Article.id.desc()).limit(6).all()


@app.get("/api/sponsors")
def get_sponsors(location: str = "main", db: Session = Depends(get_db)):
    """جلب الإعلانات النشطة بناءً على مكان الظهور"""
    return db.query(Sponsor).filter(Sponsor.location == location, Sponsor.is_active == True).all()


# ---------------------------------------------------------
# 8. نظام الحماية والتسجيل (Auth & IP Tracking)
# ---------------------------------------------------------

@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    """إنشاء مستخدم جديد مع تسجيل بصمة الـ IP وحماية التفعيل"""
    
    clean_email = user.email.lower().strip()
    
    # التقاط عنوان الـ IP الخاص بالمشترك
    client_ip = request.client.host or "0.0.0.0"
    
    # التأكد من عدم تكرار البريد
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="هذا البريد الإلكتروني مسجل مسبقاً")

    # تحديد الرصيد بناءً على الباقة المختارة
    credits_map = {
        "Trial": 3,
        "Basic": 20,
        "Pro": 40,
        "Platinum": 200
    }
    
    user_credits = credits_map.get(user.tier, 3)
    
    # إنشاء كائن المستخدم الجديد
    new_user = User(
        email=clean_email,
        password_hash=pwd_context.hash(user.password),
        full_name=user.full_name,
        phone=user.phone,
        whatsapp=user.whatsapp,
        country=user.country,
        tier=user.tier,
        credits=user_credits,
        status="Active",
        is_verified=False,      # يبقى غير مفعل حتى مراجعة الأدمن
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
    """عملية تسجيل الدخول وإصدار التوكن"""
    
    user_email = form.username.lower().strip()
    user = db.query(User).filter(User.email == user_email).first()
    
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    """جلب بيانات المستخدم المسجل حالياً"""
    return current_user


# ---------------------------------------------------------
# 9. مركز قيادة الأدمن (Admin Operations)
# ---------------------------------------------------------

@app.get("/api/admin/users")
def admin_get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """عرض قائمة كافة المستخدمين للأدمن فقط"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    return db.query(User).all()


@app.post("/api/admin/update_user")
def admin_update_user(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """تحديث بيانات المستخدم (رصيد، باقة، تفعيل، تجديد اشتراك)"""
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    
    target_user = db.query(User).filter(User.id == data.get("user_id")).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # تحديث القيم الأساسية
    if "credits" in data:
        target_user.credits = data["credits"]
        
    if "tier" in data:
        target_user.tier = data["tier"]
        target_user.is_premium = (data["tier"] != "Trial")
        target_user.is_whale = (data["tier"] == "Platinum")
    
    # منطق التفعيل وحساب التواريخ
    if "is_verified" in data:
        target_user.is_verified = data["is_verified"]
        if target_user.is_verified:
            target_user.verified_at = datetime.now(timezone.utc)
            target_user.verification_method = "Manual Admin"
            # إذا كان أول تفعيل، نعطيه 30 يوماً
            if not target_user.subscription_start:
                target_user.subscription_start = datetime.now(timezone.utc)
                target_user.subscription_end = datetime.now(timezone.utc) + timedelta(days=30)

    # منطق التجديد التراكمي (إضافة 30 يوماً إضافية)
    if data.get("renew_subscription") == True:
        now_utc = datetime.now(timezone.utc)
        # إذا كان الاشتراك لا يزال سارياً، نضيف فوقه
        if target_user.subscription_end and target_user.subscription_end > now_utc:
            target_user.subscription_end = target_user.subscription_end + timedelta(days=30)
        else:
            # إذا كان منتهياً، نبدأ الـ 30 يوماً من اليوم
            target_user.subscription_end = now_utc + timedelta(days=30)
    
    # منطق الوسم (Flag) للحسابات المشبوهة
    if "is_flagged" in data:
        target_user.is_flagged = data["is_flagged"]
    
    db.commit()
    return {"status": "success"}


@app.delete("/api/admin/delete_user/{user_id}")
def admin_delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """حذف مستخدم نهائياً مع كافة تحليلاته"""
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="صلاحيات غير كافية")
    
    user_to_del = db.query(User).filter(User.id == user_id).first()
    if user_to_del:
        # حذف التحليلات المرتبطة أولاً
        db.query(Analysis).filter(Analysis.user_id == user_id).delete()
        db.delete(user_to_del)
        db.commit()
        
    return {"status": "success"}


# ---------------------------------------------------------
# 10. غرفة التحرير (Editorial Room)
# ---------------------------------------------------------

@app.post("/api/admin/add_article")
def admin_add_article(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """إضافة مقال جديد من قبل الأدمن"""
    
    if not current_user.is_admin: 
        raise HTTPException(status_code=403, detail="غير مسموح")
        
    new_article = Article(
        title=data.get("title"), 
        summary=data.get("summary"), 
        content=data.get("content"), 
        image_url=data.get("image_url"), 
        language=data.get("language", "ar")
    )
    
    db.add(new_article)
    db.commit()
    
    return {"status": "success", "message": "تم نشر المقال بنجاح"}


@app.post("/api/admin/upload-article-image")
async def upload_article_image(image: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """رفع صورة المقال وحفظها في الخزنة الدائمة (Render Disk)"""
    
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    
    # اسم فريد للصورة لضمان عدم التكرار
    file_name = f"art_{uuid.uuid4()}.png"
    
    # المسار النهائي في القرص الدائم
    final_path = os.path.join(STORAGE_PATH, file_name) 
    
    # عملية الحفظ الفيزيائي للملف
    with open(final_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    # إعادة رابط الصورة ليتم استخدامه في المتصفح
    return {"image_url": f"/images/{file_name}"}


# ---------------------------------------------------------
# 11. محرك تحليل الشارت (KAIA Analysis Engine)
# ---------------------------------------------------------

@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...),
    timeframe: str = Form(...),
    analysis_type: str = Form(...),
    lang: str = Form("ar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """المحرك الرئيسي لتحليل صورة الشارت عبر OpenAI GPT-4o-mini"""
    
    if current_user.credits <= 0 and not current_user.is_whale:
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ، يرجى الترقية")

    # تحديد مسار الصورة في القرص الدائم
    img_path = os.path.join(STORAGE_PATH, filename)
    
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="الصورة لم تعد موجودة في السيرفر")

    try:
        # تحويل الصورة إلى Base64 لإرسالها للذكاء الاصطناعي
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

        # تجهيز الأوامر للذكاء الاصطناعي
        sys_prompt = f"You are a professional Institutional Analyst. Analyze the chart and return JSON ONLY. Lang: {lang}"
        
        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Task: Analyze {analysis_type} on {timeframe} timeframe."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        # استخراج النتيجة النهائية
        analysis_result = json.loads(ai_response.choices[0].message.content)

        # تسجيل العملية في سجل التحليلات
        new_record = Analysis(
            user_id=current_user.id,
            symbol=analysis_type,
            signal=analysis_result.get("market_bias"),
            reason=analysis_result.get("analysis_text"),
            timeframe=timeframe
        )
        db.add(new_record)

        # خصم رصيد إذا لم يكن المشترك "حوت"
        if not current_user.is_whale:
            current_user.credits -= 1

        db.commit()

        return {
            "status": "success",
            "analysis": analysis_result,
            "remaining_credits": current_user.credits
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(e)}")
        
    finally:
        # حذف صورة الشارت بعد التحليل للحفاظ على مساحة القرص
        if os.path.exists(img_path):
            os.remove(img_path)


@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    """رفع صورة الشارت تمهيداً لتحليلها"""
    
    ext = chart.filename.split('.')[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"
    
    target_path = os.path.join(STORAGE_PATH, unique_name)
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
        
    return {"filename": unique_name}


@app.get("/api/history")
def get_user_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """جلب سجل تحليلات المستخدم السابق"""
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.id.desc()).all()


# ---------------------------------------------------------
# 12. مسارات الصفحات ودعم PWA
# ---------------------------------------------------------

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("frontend/manifest.json")

@app.get("/sw.js")
def get_sw():
    return FileResponse("frontend/sw.js")

@app.get("/")
def home(request: Request): 
    # توجيه تلقائي لمستخدمي الجوال
    u_agent = request.headers.get("user-agent", "").lower()
    if "iphone" in u_agent or "android" in u_agent:
        return FileResponse("frontend/mobile.html")
    return FileResponse("frontend/index.html")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse("frontend/dashboard.html")

@app.get("/admin")
def admin_page():
    return FileResponse("frontend/admin.html")

@app.get("/editor")
def editor_page():
    return FileResponse("frontend/editor.html")

@app.get("/history")
def history_page():
    return FileResponse("frontend/history.html")


# ---------------------------------------------------------
# 13. أدوات الطوارئ والصيانة (Emergency)
# ---------------------------------------------------------

@app.get("/api/nuclear-wipe")
def nuclear_wipe(email: str, db: Session = Depends(get_db)):
    """حذف حساب مستخدم بالكامل (للمواقف الطارئة)"""
    
    target_email = email.lower().strip()
    user_found = db.query(User).filter(User.email == target_email).first()
    
    if user_found:
        db.query(Analysis).filter(Analysis.user_id == user_found.id).delete()
        db.delete(user_found)
        db.commit()
        return {"message": f"تم مسح الحساب {target_email} بنجاح"}
    
    return {"message": "المستخدم غير موجود"}


@app.get("/api/fix-my-account")
def fix_my_account(email: str, new_password: str, db: Session = Depends(get_db)):
    """إصلاح حساب الأدمن أو استعادة الوصول"""
    
    target_email = email.lower().strip()
    user_found = db.query(User).filter(User.email == target_email).first()
    
    if user_found:
        user_found.password_hash = pwd_context.hash(new_password)
        user_found.is_verified = True
        user_found.is_admin = True
        user_found.is_whale = True
        user_found.credits = 9999
        db.commit()
        return {"message": f"تم تحديث وإصلاح حساب الملك: {target_email}"}
    
    return {"error": "لم يتم العثور على الحساب المذكور"}

# =========================================================
# END OF KAIA MAIN ENGINE
# =========================================================