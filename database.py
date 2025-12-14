from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# ===========================
# 1. إصلاح رابط الاتصال لـ Render
# ===========================
DATABASE_URL = os.getenv("DATABASE_URL")

# تأكد من وجود الرابط وإصلاح البادئة إذا لزم الأمر
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# إنشاء المحرك
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ===========================
# 2. تعريف جدول المستخدمين
# ===========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # تم تعديل الاسم هنا ليطابق ملف main.py
    password_hash = Column(String, nullable=False)

    credits = Column(Integer, default=3)
    is_premium = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

# ===========================
# 3. إنشاء الجداول تلقائياً
# ===========================
# هذا السطر مهم جداً: يبني الجداول فوراً عند تشغيل السيرفر
Base.metadata.create_all(bind=engine)