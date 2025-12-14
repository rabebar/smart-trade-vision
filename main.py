from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
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
from dotenv import load_dotenv

# تحميل المتغيرات
load_dotenv()

# استيراد قاعدة البيانات
from database import SessionLocal, User
import schemas

# ===========================
# إعدادات عامة
# ===========================
SECRET_KEY = "CHANGE_THIS_SECRET_KEY"
ALGORITHM = "HS256"

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

app = FastAPI()

# ===========================
# Middleware
# ===========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# التأكد من وجود المجلدات
if not os.path.exists("images"):
    os.makedirs("images")

# ربط ملفات الصور والفرونت إند
app.mount("/images", StaticFiles(directory="images"), name="images")

# ملاحظة: تأكد أن مجلد frontend موجود وفيه الملفات
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

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

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401)

    return user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# ===========================
# Utils
# ===========================
def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# ===========================
# Pages
# ===========================
# تم حذف الرابط القديم المتعارض من هنا
# سيتم استخدام الرابط في نهاية الملف للتحقق من التشغيل

@app.get("/admin")
async def admin_page():
    # تأكد أن الملف موجود لتجنب الأخطاء
    if os.path.exists("frontend/admin.html"):
        return FileResponse("frontend/admin.html")
    return {"error": "Admin page not found"}

# ===========================
# Auth API
# ===========================
@app.post("/api/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        credits=3
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "credits": user.credits,
        "is_admin": user.is_admin
    }

@app.get("/api/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

# ===========================
# Admin API
# ===========================
@app.get("/api/admin/users")
def all_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).all()

class UpdateCredit(BaseModel):
    user_id: str
    credits: int
    is_premium: bool

@app.post("/api/admin/update_user")
def update_user(
    data: UpdateCredit,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404)

    user.credits = data.credits
    user.is_premium = data.is_premium
    db.commit()
    return {"status": "updated"}

@app.delete("/api/admin/delete_user/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)

    db.delete(user)
    db.commit()
    return {"status": "deleted"}

# ===========================
# Chart API
# ===========================
@app.post("/api/upload-chart")
async def upload_chart(chart: UploadFile = File(...)):
    filename = chart.filename.replace(" ", "_")
    path = f"images/uploaded_{filename}"
    with open(path, "wb") as buffer:
        shutil.copyfileobj(chart.file, buffer)
    return {"status": "uploaded", "filename": filename}

@app.post("/api/analyze-chart")
async def analyze_chart(
    filename: str = Form(...),
    analysis_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.credits <= 0 and not current_user.is_premium:
        raise HTTPException(status_code=400, detail="OUT_OF_CREDITS")

    image_path = f"images/uploaded_{filename}"
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
        
    base64_image = encode_image(image_path)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a trading analyst. Output ONLY JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Analyze {analysis_type}. Return JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=300
        )

        data = json.loads(response.choices[0].message.content.replace("```json", "").replace("```", ""))

        if not current_user.is_premium:
            current_user.credits -= 1
            db.commit()

        return {
            **data,
            "status": "success",
            "remaining_credits": current_user.credits
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ===========================
# Secret admin shortcut
# ===========================
@app.get("/api/secret/make_me_king")
def make_me_king(db: Session = Depends(get_db)):
    my_email = "rabe.bar.a74@gmail.com"

    user = db.query(User).filter(User.email == my_email).first()
    if not user:
        return {"error": "User not found"}

    user.is_admin = True
    user.is_premium = True
    user.credits = 1_000_000
    db.commit()
    return {"status": "KING MODE ACTIVATED 👑"}

# ===========================
# Health Check / Root
# ===========================
@app.get("/")
def read_root():
    # هذا الرابط مهم جداً عشان Render يتأكد إن الموقع شغال
    return {"message": "App is running", "status": "ok"}