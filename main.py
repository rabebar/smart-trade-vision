from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
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

from database import SessionLocal, User, Analysis
import schemas

# =========================================================
# Security & AI
# =========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "CANA_ULTIMATE_SEC_2025")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="CANA AI – KAIA Core (Descriptive Analyst Engine)")

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
        user = db.query(User).filter(User.email == payload.get("sub")).first()
        if not user:
            raise HTTPException(status_code=401, detail="المستخدم غير موجود")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="انتهت الجلسة")

# =========================================================
# News
# =========================================================
@app.get("/api/news")
def get_news():
    try:
        rss = "https://sa.investing.com/rss/news_1.rss"
        res = requests.get(rss, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")[:12]
        titles = [i.title.text.strip() for i in items if i.title]
        return {"news": " ★ ".join(titles)} if titles else {"news": "نبض السوق هادئ"}
    except:
        return {"news": "تعذر جلب الأخبار"}

# =========================================================
# Auth
# =========================================================
@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="البريد مستخدم")

    credits_map = {"Trial": 3, "Basic": 20, "Pro": 40, "Platinum": 200}
    new_user = User(
        email=user.email,
        password_hash=pwd_context.hash(user.password),
        full_name=user.full_name,
        phone=user.phone,
        whatsapp=user.whatsapp,
        country=user.country,
        tier=user.tier,
        credits=credits_map.get(user.tier, 3),
        status="Active",
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
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="بيانات غير صحيحة")
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer"}

@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

# =========================================================
# KAIA Descriptive Analysis Engine (FIXED & CLEANED)
# =========================================================
@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...),
    timeframe: str = Form(...),
    analysis_type: str = Form(...),
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

        # PROMPT النهائي الصارم (التعديل الوحيد هنا)
        system_prompt = """
أنت محلل أسواق مؤسسي محترف.

مهمتك هي قراءة الشارت بصريًا وبدقة عالية، ثم اتخاذ قرارات تحليلية واضحة
قبل كتابة الشرح، دون تقديم أي توصيات تداول أو أرقام أو مستويات.

التزم بالخطوات التالية بالتسلسل المنطقي:

1) حدد التحيّز العام للسوق (market_bias):
- صاعد
- هابط
- محايد

2) حدد مرحلة السوق (market_phase):
- اتجاه
- تذبذب
- انتقال

3) قيّم سياق الفرصة (opportunity_context):
- بيئة واضحة
- بيئة مختلطة
- بيئة ضعيفة

4) اكتب التحليل النصي (analysis_text) بما يبرر القرارات أعلاه فقط.

5) أضف ملاحظة مخاطر (risk_note).

6) حدّد مستوى الثقة (confidence) بين 0.0 و 1.0.

قواعد صارمة:
- لا توصيات
- لا أرقام
- لا مستويات
- JSON فقط وبالمفاتيح التالية:

market_bias,
market_phase,
opportunity_context,
analysis_text,
risk_note,
confidence
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"حلل هذا الشارت على الإطار {timeframe} باستخدام {analysis_type}."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
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
# Upload
# =========================================================
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    name = f"{uuid.uuid4()}.{chart.filename.split('.')[-1]}"
    with open(f"images/{name}", "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"filename": name}

# =========================================================
# Pages
# =========================================================
@app.get("/")
def home(): return FileResponse("frontend/index.html")

@app.get("/dashboard")
def dashboard(): return FileResponse("frontend/dashboard.html")

@app.get("/history")
def history(): return FileResponse("frontend/history.html")
