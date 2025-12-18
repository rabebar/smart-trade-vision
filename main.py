from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import shutil
import os
import base64
import json
import re
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# استيراد قاعدة البيانات والجداول
from database import SessionLocal, User, Analysis
import schemas

# ===========================
# إعدادات عامة
# ===========================
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
ALGORITHM = "HS256"

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

app = FastAPI()

# ===========================
# Middleware (CORS)
# ===========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# التأكد من وجود مجلد الصور
if not os.path.exists("images"):
    os.makedirs("images")

# ربط الملفات
app.mount("/images", StaticFiles(directory="images"), name="images")
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/favicon.ico")
def favicon():
    if os.path.exists("images/logo.png"):
        return FileResponse("images/logo.png")
    return JSONResponse(status_code=404, content={"detail": "No favicon"})

# ===========================
# DB Dependency
# ===========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===========================
# Auth helpers
# ===========================
def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
    except JWTError:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# ===========================
# Utils
# ===========================
def safe_filename(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9.\-_]+", "_", name)
    if not name:
        name = "chart.png"
    return name

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _normalize_timeframe(tf: str) -> str:
    tf = (tf or "").strip()
    tf = tf.replace(" ", "").replace("minute", "m").replace("hour", "H")
    mapping = {"1": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "D": "Daily"}
    if tf in mapping:
        return mapping[tf]
    return tf or "Not Specified"

def _to_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        s = re.sub(r"[^0-9.\-]+", "", s)
        return float(s) if s else None
    except:
        return None

def _calc_rr(signal: str, entry, sl, tp):
    sig = (signal or "").upper().strip()
    e = _to_float(entry)
    s = _to_float(sl)
    t = _to_float(tp)
    if e is None or s is None or t is None:
        return 0.0

    if sig == "BUY":
        risk = e - s
        reward = t - e
    elif sig == "SELL":
        risk = s - e
        reward = e - t
    else:
        return 0.0

    if risk <= 0:
        return 0.0
    rr = reward / risk
    try:
        return float(rr)
    except:
        return 0.0

def _ensure_trade_keys(data: dict, tf_default: str = "Not Specified"):
    if not isinstance(data, dict):
        data = {}

    signal = (data.get("signal") or "WAIT").strip().upper()
    if signal not in ["BUY", "SELL", "WAIT"]:
        signal = "WAIT"

    data["signal"] = str(signal)
    data["entry"] = str(data.get("entry") or "N/A")
    data["sl"] = str(data.get("sl") or "N/A")
    data["tp"] = str(data.get("tp") or "N/A")

    try:
        data["confidence"] = float(data.get("confidence") or 0)
    except:
        data["confidence"] = 0.0

    if "levels_available" not in data:
        data["levels_available"] = True if signal in ["BUY", "SELL"] else False
    else:
        data["levels_available"] = bool(data.get("levels_available"))

    data["timeframe"] = str(data.get("timeframe") or tf_default)
    data["session"] = str(data.get("session") or "Not specified")
    data["validity"] = str(data.get("validity") or "Not specified")

    data["notes_ar"] = str(data.get("notes_ar") or "")
    data["notes_en"] = str(data.get("notes_en") or "")
    data["reason_ar"] = str(data.get("reason_ar") or "")
    data["reason_en"] = str(data.get("reason_en") or "")

    if "notes" not in data:
        data["notes"] = ""
    if "reason" not in data:
        data["reason"] = ""

    # ✅ New optional analytics
    try:
        data["rr"] = float(data.get("rr") or 0)
    except:
        data["rr"] = 0.0

    data["setup_type"] = str(data.get("setup_type") or "")
    if not isinstance(data.get("key_levels"), dict):
        data["key_levels"] = {}

    return data

# ===========================
# Admin API & Pages
# ===========================
class UpdateUserReq(BaseModel):
    user_id: int
    credits: int
    is_premium: bool
    is_whale: bool

@app.get("/admin")
async def admin_page():
    if os.path.exists("frontend/admin.html"):
        return FileResponse("frontend/admin.html")
    return {"error": "Admin page not found"}

@app.get("/api/admin/users")
def all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id, "email": u.email, "credits": u.credits,
            "is_premium": u.is_premium, "is_whale": u.is_whale, "is_admin": u.is_admin
        }
        for u in users
    ]

@app.post("/api/admin/update_user")
def update_user(data: UpdateUserReq, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits = data.credits
    user.is_premium = data.is_premium
    user.is_whale = data.is_whale
    db.commit()
    return {"status": "updated"}

@app.delete("/api/admin/delete_user/{user_id}")
def delete_user(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}

# ===========================
# Auth API
# ===========================
@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(email=user.email, password_hash=get_password_hash(user.password), credits=3)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "credits": user.credits, "is_admin": user.is_admin}

@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

# ===========================
# Chart Analysis (Core)
# ===========================
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    filename = safe_filename(chart.filename or "chart.png")
    path = f"images/uploaded_{filename}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"status": "uploaded", "filename": filename}

@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...),
    analysis_type: str = Form(...),
    timeframe: str = Form(default="Not Specified"),
    session_in: str = Form(default="Not specified"),
    validity_in: str = Form(default="Not specified"),
    lang: str = Form(default="en"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    timeframe = _normalize_timeframe(timeframe)

    if current_user.credits <= 0 and not current_user.is_premium:
        raise HTTPException(status_code=400, detail="OUT_OF_CREDITS")

    image_path = f"images/uploaded_{safe_filename(filename)}"
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    if not client:
        return JSONResponse(status_code=500, content={"error": "OPENAI_API_KEY missing"})

    base64_image = encode_image(image_path)
    mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

    # ✅ Updated schema
    trade_schema = {
        "name": "mrtrade_signal_bilingual",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "signal": {"type": "string", "enum": ["BUY", "SELL", "WAIT"]},
                "entry": {"type": "string"},
                "sl": {"type": "string"},
                "tp": {"type": "string"},
                "confidence": {"type": "number"},
                "levels_available": {"type": "boolean"},

                "notes_ar": {"type": "string"},
                "notes_en": {"type": "string"},
                "reason_ar": {"type": "string"},
                "reason_en": {"type": "string"},

                "timeframe": {"type": "string"},
                "session": {"type": "string"},
                "validity": {"type": "string"},

                "rr": {"type": "number"},
                "setup_type": {"type": "string"},
                "key_levels": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "support": {"type": "number"},
                        "resistance": {"type": "number"},
                    }
                }
            },
            "required": [
                "signal", "entry", "sl", "tp",
                "confidence", "levels_available",
                "notes_ar", "notes_en",
                "reason_ar", "reason_en",
                "timeframe", "session", "validity"
            ]
        }
    }

    lang_instruction = (
        "CRITICAL LANGUAGE RULES:\n"
        "1) 'notes_ar' and 'reason_ar' MUST be written in ARABIC only.\n"
        "2) 'notes_en' and 'reason_en' MUST be written in ENGLISH only.\n"
        "3) Do NOT mix languages inside the same field.\n"
    )

    system_msg = (
        "You are a professional Trader (Scalper).\n"
        "Your goal is to find a trading opportunity (BUY or SELL) on this chart.\n\n"
        f"{lang_instruction}\n"
        "STRICT TRADING RULES:\n"
        "1) DO NOT RETURN 'WAIT' unless the image is completely blank/unreadable.\n"
        "2) If the market is choppy, find the nearest support/resistance and trade the bounce.\n"
        "3) ESTIMATE prices from the Y-axis even if blurry. Use your best guess.\n"
        "4) Return 'levels_available': true whenever you give BUY/SELL.\n"
        "5) Provide specific numbers for entry, sl, tp.\n"
    )

    user_msg = (
        f"Strategy: {analysis_type}. Timeframe: {timeframe}. "
        f"User session preference: {session_in}. Validity preference: {validity_in}. "
        f"Find the best setup NOW."
    )

    fallback = {
        "signal": "WAIT",
        "entry": "N/A",
        "sl": "N/A",
        "tp": "N/A",
        "confidence": 0,
        "levels_available": False,
        "notes_ar": "تعذّر التحليل",
        "notes_en": "Analysis failed",
        "reason_ar": "AI_ERROR",
        "reason_en": "AI_ERROR",
        "timeframe": timeframe,
        "session": session_in,
        "validity": validity_in,
        "rr": 0.0,
        "setup_type": "",
        "key_levels": {}
    }

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
            temperature=0.4,
            response_format={"type": "json_schema", "json_schema": trade_schema},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]}
            ],
            max_tokens=900
        )

        raw = response.choices[0].message.content or ""
        print(f"DEBUG AI RAW: {raw}")

        data = json.loads(raw) if raw.strip() else fallback
        data = _ensure_trade_keys(data, tf_default=timeframe)

        if (session_in or "").strip() and session_in != "Not specified":
            data["session"] = session_in
        if (validity_in or "").strip() and validity_in != "Not specified":
            data["validity"] = validity_in
        data["timeframe"] = timeframe

        rr_val = _calc_rr(data.get("signal"), data.get("entry"), data.get("sl"), data.get("tp"))
        if rr_val and rr_val > 0:
            data["rr"] = rr_val
        else:
            try:
                data["rr"] = float(data.get("rr") or 0)
            except:
                data["rr"] = 0.0

        if (lang or "en").lower() == "ar":
            data["notes"] = data.get("notes_ar", "")
            data["reason"] = data.get("reason_ar", "")
        else:
            data["notes"] = data.get("notes_en", "")
            data["reason"] = data.get("reason_en", "")

        if data.get("signal") in ["BUY", "SELL"]:
            new_analysis = Analysis(
                user_id=current_user.id,
                symbol="Chart",
                signal=data["signal"],
                entry=str(data["entry"]),
                tp=str(data["tp"]),
                sl=str(data["sl"]),
                result="Pending",
                created_at=datetime.utcnow()
            )
            db.add(new_analysis)

            if not current_user.is_premium:
                current_user.credits -= 1

            db.commit()

        is_vip = current_user.is_whale

        return {
            **data,
            "status": "success",
            "remaining_credits": current_user.credits,
            "is_vip": is_vip
        }

    except Exception as e:
        print(f"Error analyzing chart: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/history")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.created_at.desc()).limit(20).all()
    return history

# ===========================
# Pages & Frontend Routes
# ===========================

# 1. الصفحة الرئيسية (Root)
@app.get("/")
async def read_index():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "CANA AI API is Running 🚀 (frontend not found)"}

# 2. صفحة الداشبورد (الجديدة) 🚀
@app.get("/dashboard")
async def dashboard_page():
    if os.path.exists("frontend/dashboard.html"):
        return FileResponse("frontend/dashboard.html")
    return JSONResponse(status_code=404, content={"detail": "Dashboard page not found in frontend folder"})

# 3. الرابط السحري (بالإيميل الصحيح) 👑
@app.get("/api/secret/make_me_king")
def make_me_king(db: Session = Depends(get_db)):
    target_email = "rabe.bar.a74@gmail.com"  # ✅ إيميلك الحقيقي
    user = db.query(User).filter(User.email == target_email).first()
    if user:
        user.is_admin = True
        user.is_premium = True
        user.is_whale = True
        user.credits = 1000
        db.commit()
        return {"status": f"King Mode ACTIVATED for {target_email} 👑"}
    return {"error": f"User {target_email} not found. Register first!"}