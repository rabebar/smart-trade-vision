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
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv  # 1. استدعاء مكتبة الإخفاء

# 2. تحميل المفاتيح من الملف السري (.env)
load_dotenv()

# استيراد ملفاتنا
from database import create_db, SessionLocal, User
import schemas

# ===========================
# إعدادات (Settings)
# ===========================

# 👇👇👇 هنا السحر! هذا السطر يبحث عن المفتاح داخل ملف .env تلقائياً 👇👇👇
openai_api_key = os.getenv("OPENAI_API_KEY")
# 👆👆👆 لا تكتب مفتاحك هنا، اتركه كما هو ليقرأ من الملف السري 👆👆👆

SECRET_KEY = "my_super_secret_key_change_this"
ALGORITHM = "HS256"

# تمرير المفتاح للعميل
client = OpenAI(api_key=openai_api_key)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

app = FastAPI()
create_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("images"): os.makedirs("images")
app.mount("/images", StaticFiles(directory="images"), name="images")
# تأكد أن مجلد frontend موجود
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ===========================
# دوال مساعدة (Helpers)
# ===========================
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_password_hash(password): return pwd_context.hash(password)
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    
    user = db.query(User).filter(User.email == email).first()
    if user is None: raise HTTPException(status_code=401)
    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# ===========================
# Endpoints (الروابط)
# ===========================
@app.get("/")
async def read_index(): return FileResponse("frontend/index.html")

@app.get("/admin")
async def admin_panel(): return FileResponse("frontend/admin.html")

@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email exists")
    new_user = User(email=user.email, hashed_password=get_password_hash(user.password), credits=3)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "credits": user.credits, "is_admin": user.is_admin}

@app.get("/api/me", response_model=schemas.UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- ADMIN API (لوحة التحكم) ---
@app.get("/api/admin/users")
def get_all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).all()

class UpdateCredit(BaseModel):
    user_id: int
    credits: int
    is_premium: bool

@app.post("/api/admin/update_user")
def update_user_credits(data: UpdateCredit, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user: raise HTTPException(status_code=404)
    user.credits = data.credits
    user.is_premium = data.is_premium
    db.commit()
    return {"status": "updated"}

@app.delete("/api/admin/delete_user/{user_id}")
def delete_user_endpoint(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الشخصي!")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    db.delete(user)
    db.commit()
    return {"status": "deleted", "message": f"تم حذف المستخدم {user.email} بنجاح"}

# --- CHART API (التحليل) ---
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    clean_filename = chart.filename.replace(" ", "_")
    with open(f"images/uploaded_{clean_filename}", "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"status": "uploaded", "filename": clean_filename}

@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...), analysis_type: str = Form(...),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.credits <= 0 and not current_user.is_premium:
        raise HTTPException(status_code=400, detail="OUT_OF_CREDITS")
    
    uploaded_path = f"images/uploaded_{filename}"
    base64_image = encode_image(uploaded_path)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a trading analyst. Output ONLY JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Analyze ({analysis_type}). Return JSON: {{'signal': 'BUY/SELL', 'entry': '', 'stop_loss': '', 'take_profit': ''}}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ], max_tokens=300
        )
        data = json.loads(response.choices[0].message.content.replace("```json", "").replace("```", "").strip())
        
        if not current_user.is_premium:
            current_user.credits -= 1
            db.commit()
            
        return {**data, "status": "success", "file": f"images/uploaded_{filename}", "remaining_credits": current_user.credits}
    except Exception as e:
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)
    # ===========================
# الرابط السحري (مؤقت)
# ===========================
@app.get("/api/secret/make_me_king")
def make_me_king(db: Session = Depends(get_db)):
    # 🔴 ضع إيميلك الذي سجلت به في الموقع هنا
    my_email = "rabe.bar.a74@gmail.com" 
    
    user = db.query(User).filter(User.email == my_email).first()
    if not user:
        return {"status": "error", "message": "المستخدم غير موجود! سجل حساباً أولاً"}
    
    user.is_admin = True
    user.credits = 1000000
    user.is_premium = True
    db.commit()
    return {"status": "success", "message": f"مبروك! {user.email} أصبح الآن المدير والرصيد مليون! 👑"}
# UPDATE ADMIN ACCESS NOW
# ===========================
# الرابط السحري (مؤقت)
# ===========================
@app.get("/api/secret/make_me_king")
def make_me_king(db: Session = Depends(get_db)):
    # 🔴 ضع إيميلك الحقيقي هنا بدلاً من الايميل الوهمي
    my_email = "rabe.bar.a74@gmail.com" 
    
    user = db.query(User).filter(User.email == my_email).first()
    if not user:
        return {"status": "error", "message": "المستخدم غير موجود! سجل حساباً أولاً"}
    
    user.is_admin = True
    user.credits = 1000000
    user.is_premium = True
    db.commit()
    return {"status": "success", "message": f"مبروك! {user.email} أصبح الآن المدير والرصيد مليون! 👑"}
# ===========================
# الرابط السحري (مؤقت)
# ===========================
@app.get("/api/secret/make_me_king")
def make_me_king(db: Session = Depends(get_db)):
    # 👇 ضع إيميلك الحقيقي هنا
    my_email = "rabe.bar.a74@gmail.com" 
    
    user = db.query(User).filter(User.email == my_email).first()
    if not user:
        return {"status": "error", "message": "المستخدم غير موجود! سجل حساباً أولاً"}
    
    user.is_admin = True
    user.credits = 1000000
    user.is_premium = True
    db.commit()
    return {"status": "success", "message": f"مبروك! {user.email} أصبح الآن المدير والرصيد مليون! 👑"}