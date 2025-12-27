from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import shutil, os, base64, json, requests, uuid
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# =========================================================
# 1. الإعدادات والبيئة (Environment Setup)
# =========================================================
load_dotenv()

# تحديد المسار المطلق للمشروع لضمان عمل المجلدات على Render
BASE_DIR = Path(__file__).resolve().parent

from database import SessionLocal, User, Analysis
import schemas

# =========================================================
# 2. الأمن والذكاء الاصطناعي (Security & AI)
# =========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "KAIA_ULTIMATE_SEC_2025")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="KAIA AI – Institutional Analyst Engine")

# =========================================================
# 3. الربط والمجلدات الثابتة (Static Files & Paths)
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# إنشاء مجلد الصور المرفوعة
images_path = BASE_DIR / "images"
images_path.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_path)), name="images")

# [حل مشكلة الشعار والدمار البصري]
# نحدد مكان المجلد frontend/static بدقة مطلقة
static_path = BASE_DIR / "frontend" / "static"

# إذا لم يجد المجلد باسم static، يجرب المجلد باسم statics
if not static_path.exists():
    static_path = BASE_DIR / "frontend" / "statics"

# إذا لم يجد أياً منهما، يقوم بإنشاء المجلد الأصلي لمنع الخطأ
if not static_path.exists():
    static_path = BASE_DIR / "frontend" / "static"
    static_path.mkdir(parents=True, exist_ok=True)

# ربط المجلد المكتشف برابط /static الموحد
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# =========================================================
# 4. الدوال المساعدة (Helpers)
# =========================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub").lower().strip()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="انتهت الجلسة")

# =========================================================
# 5. محرك الأخبار (Market News Support)
# =========================================================
@app.get("/api/news")
def get_news(lang: str = "ar"):
    try:
        if lang == "en":
            rss = "https://www.investing.com/rss/news_285.rss" 
        else:
            rss = "https://sa.investing.com/rss/news_1.rss"
            
        res = requests.get(rss, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")[:15]
        titles = [i.title.text.strip() for i in items if i.title]
        
        if titles:
            return {"news": " ★ ".join(titles)}
        else:
            msg = "Market pulse is quiet" if lang == "en" else "نبض السوق هادئ"
            return {"news": msg}
    except:
        err_msg = "Market news currently unavailable" if lang == "en" else "تعذر جلب الأخبار حالياً"
        return {"news": err_msg}

# =========================================================
# 6. نظام المصادقة (Registration & Login)
# =========================================================
@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    clean_email = user.email.lower().strip()
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="البريد مستخدم")

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
        is_verified=True,  
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
        raise HTTPException(status_code=401, detail="بيانات غير صحيحة")
    
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer"}

@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
        return current_user

# =========================================================
# 7. عمليات المشرفين (Admin Operations)
# =========================================================
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
    user.is_premium = data.get("is_premium", user.is_premium)
    user.is_whale = data.get("is_whale", user.is_whale)
    
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

# =========================================================
# 8. محرك التحليل الذكي (Analysis Engine)
# =========================================================
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
        raise HTTPException(status_code=400, detail="الرصيد غير كافٍ")

    path = images_path / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="الصورة غير موجودة")

    try:
        with open(str(path), "rb") as f:
            base64_image = base64.b64encode(f.read()).decode()

        system_prompt = """
أنت محلل أسواق مؤسسي محترف. مهمتك هي قراءة الشارت بصريًا وبدقة عالية، ثم اتخاذ قرارات تحليلية واضحة.
JSON ONLY: market_bias, market_phase, opportunity_context, analysis_text, risk_note, confidence
"""
        # إضافة حماية Timeout لمدة دقيقة كاملة لمنع انقطاع الاتصال
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this chart on {timeframe} using {analysis_type}. Language: {lang}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            timeout=60.0
        )

        result = json.loads(response.choices[0].message.content)

        record = Analysis(
            user_id=current_user.id,
            symbol=analysis_type,
            signal=result.get("market_bias"),
            reason=result.get("analysis_text"),
            timeframe=timeframe
        )
        db.add(record)

        if not current_user.is_whale:
            current_user.credits -= 1

        db.commit()

        return {
            "status": "success",
            "analysis": result,
            "remaining_credits": current_user.credits
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if path.exists():
            os.remove(str(path))

# =========================================================
# 9. الرفع والسجلات (Upload & History)
# =========================================================
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    name = f"{uuid.uuid4()}.{chart.filename.split('.')[-1]}"
    with open(str(images_path / name), "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"filename": name}

@app.get("/api/history")
def get_user_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.id.desc()).all()

# =========================================================
# 10. دعم تطبيق الويب (PWA & Routes)
# =========================================================
@app.get("/manifest.json")
def get_manifest(): return FileResponse(str(BASE_DIR / "frontend" / "manifest.json"))

@app.get("/sw.js")
def get_sw(): return FileResponse(str(BASE_DIR / "frontend" / "sw.js"))

@app.get("/")
def home(request: Request): 
    user_agent = request.headers.get("user-agent", "").lower()
    page = "mobile.html" if "iphone" in user_agent or "android" in user_agent else "index.html"
    return FileResponse(str(BASE_DIR / "frontend" / page))

@app.get("/dashboard")
def dashboard(): return FileResponse(str(BASE_DIR / "frontend" / "dashboard.html"))

@app.get("/mobile")
def mobile(): return FileResponse(str(BASE_DIR / "frontend" / "mobile.html"))

@app.get("/history")
def history(): return FileResponse(str(BASE_DIR / "frontend" / "history.html"))

@app.get("/admin")
def admin(): return FileResponse(str(BASE_DIR / "frontend" / "admin.html"))

# =========================================================
# 11. أدوات الطوارئ (Emergency Tools)
# =========================================================
@app.get("/api/nuclear-wipe")
def nuclear_wipe(email: str, db: Session = Depends(get_db)):
    clean_email = email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        db.query(Analysis).filter(Analysis.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        return {"message": f"SUCCESS: {clean_email} wiped out!"}
    return {"message": "Not found"}

@app.get("/api/fix-my-account")
def fix_my_account(email: str, new_password: str, db: Session = Depends(get_db)):
    clean_email = email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if user:
        user.password_hash = pwd_context.hash(new_password)
        user.is_verified = True
        user.is_admin = True
        user.is_whale = True
        user.credits = 9999
        db.commit()
        return {"message": f"King {clean_email} is fixed!"}
    return {"error": "Not found"}