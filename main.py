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

# =========================================================
# ENV + DB
# =========================================================
load_dotenv()

from database import SessionLocal, User, Analysis, Article, Sponsor
import schemas

# =========================================================
# Security & AI
# =========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "KAIA_ULTIMATE_SEC_2025")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="KAIA AI – Institutional Analyst Engine")

# =========================================================
# CORS + Static
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("images", exist_ok=True)
app.mount("/images", StaticFiles(directory="images"), name="images")

# ربط المجلد لضمان ظهور اللوجو والملفات الثابتة
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# =========================================================
# Helpers
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
# News Engine (With High-Performance Caching)
# =========================================================

# مستودع البيانات المؤقتة لمنع تأخير شريط الأخبار
NEWS_CACHE = {
    "ar": {"data": "KAIA AI: نراقب تحركات السيولة والسياسة النقدية الحالية", "timestamp": None},
    "en": {"data": "KAIA AI: Monitoring current liquidity and monetary policy", "timestamp": None}
}

@app.get("/api/news")
def get_news(lang: str = "ar"):
    global NEWS_CACHE
    lang_key = "en" if lang == "en" else "ar"
    
    # التحقق إذا كانت البيانات المخزنة حديثة (أقل من 10 دقائق)
    now = datetime.now()
    cache_entry = NEWS_CACHE[lang_key]
    
    if cache_entry["timestamp"] and (now - cache_entry["timestamp"]).seconds < 600:
        return {"news": cache_entry["data"]}

    try:
        # تحديد الرابط بناءً على اللغة
        if lang_key == "en":
            rss = "https://www.investing.com/rss/news_285.rss" 
        else:
            rss = "https://sa.investing.com/rss/news_1.rss"
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/xml, text/xml, */*"
        }
        
        # طلب خارجي سريع مع مهلة انتظار قصيرة جداً لضمان عدم تعليق السيرفر
        res = requests.get(rss, timeout=5, headers=headers)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "xml")
            items = soup.find_all("item")
            
            titles = []
            for i in items[:15]:
                if i.title:
                    clean_title = i.title.text.strip().replace("'", "").replace('"', "")
                    titles.append(clean_title)
            
            if titles:
                # تحديث الذاكرة المؤقتة بالبيانات الجديدة
                NEWS_CACHE[lang_key]["data"] = " ★ ".join(titles)
                NEWS_CACHE[lang_key]["timestamp"] = now
                return {"news": NEWS_CACHE[lang_key]["data"]}
                
    except Exception as e:
        print(f"News Refresh Silent Error: {e}")
        # في حال حدوث أي خطأ، سنعيد البيانات القديمة المخزنة فوراً ليبقى الشريط يعمل
    
    return {"news": NEWS_CACHE[lang_key]["data"]}

# =========================================================
# جلب المقالات والإعلانات للجمهور (Media API)
# =========================================================
@app.get("/api/articles")
def get_articles(lang: str = "ar", db: Session = Depends(get_db)):
    return db.query(Article).filter(Article.language == lang).order_by(Article.id.desc()).limit(6).all()

@app.get("/api/sponsors")
def get_sponsors(location: str = "main", db: Session = Depends(get_db)):
    return db.query(Sponsor).filter(Sponsor.location == location, Sponsor.is_active == True).all()

# =========================================================
# Auth System
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
# Admin Operations (Users)
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
# أوامر غرفة التحرير السيادية (Editor API)
# =========================================================

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

# =========================================================
# KAIA Descriptive Analysis Engine
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

    path = f"images/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="الصورة غير موجودة")

    try:
        with open(path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode()

        lang_map = {
            "ar": "Arabic (العربية)",
            "en": "English",
            "fr": "French (Français)",
            "es": "Spanish (Español)",
            "it": "Italiano"
        }
        target_lang = lang_map.get(lang, "Arabic")

        system_prompt = f"""
أنت محلل أسواق مؤسسي محترف. مهمتك هي قراءة الشارت بصريًا وبدقة عالية، ثم اتخاذ قرارات تحليلية واضحة.
JSON ONLY: market_bias, market_phase, opportunity_context, analysis_text, risk_note, confidence
Language: {target_lang}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze this chart on {timeframe} using {analysis_type}."},
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
        if os.path.exists(path):
            os.remove(path)

# =========================================================
# Upload & History
# =========================================================
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    name = f"{uuid.uuid4()}.{chart.filename.split('.')[-1]}"
    with open(f"images/{name}", "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"filename": name}

@app.post("/api/admin/upload-article-image")
async def upload_article_image(image: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin: 
        raise HTTPException(status_code=403)
    name = f"art_{uuid.uuid4()}.png"
    save_path = os.path.join("frontend", name) 
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    return {"image_url": f"/static/{name}"}

@app.get("/api/history")
def get_user_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.id.desc()).all()

# =========================================================
# PWA & Service Worker Support
# =========================================================
@app.get("/manifest.json")
def get_manifest(): return FileResponse("frontend/manifest.json")

@app.get("/sw.js")
def get_sw(): return FileResponse("frontend/sw.js")

# =========================================================
# Pages & Logic Control
# =========================================================
@app.get("/")
def home(request: Request): 
    user_agent = request.headers.get("user-agent", "").lower()
    if "iphone" in user_agent or "android" in user_agent:
        return FileResponse("frontend/mobile.html")
    return FileResponse("frontend/index.html")

@app.get("/dashboard")
def dashboard(): return FileResponse("frontend/dashboard.html")

@app.get("/mobile")
def mobile(): return FileResponse("frontend/mobile.html")

@app.get("/editor")
def editor_page(): return FileResponse("frontend/editor.html")

@app.get("/admin")
def admin(): return FileResponse("frontend/admin.html")

@app.get("/upgrade")
def upgrade_page(): return FileResponse("frontend/index.html")

@app.get("/history")
def history(): return FileResponse("frontend/history.html")

# =========================================================
# Emergency Tools
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