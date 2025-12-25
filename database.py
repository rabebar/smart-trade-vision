import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

# =========================================================
# إعداد قاعدة البيانات
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = DATABASE_URL or "sqlite:///./sql_app.db"

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================================================
# 1. جدول المستخدمين
# =========================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String, default="Trader")
    phone = Column(String, default="")
    whatsapp = Column(String, default="")
    country = Column(String, default="Global")
    trader_level = Column(String, default="Beginner")
    markets = Column(String, default="Forex")
    tier = Column(String, default="Trial")
    status = Column(String, default="Active")
    credits = Column(Integer, default=3)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    is_whale = Column(Boolean, default=False) 

    analyses = relationship("Analysis", back_populates="owner", cascade="all, delete-orphan")

# =========================================================
# 2. جدول التحليلات
# =========================================================
class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, default="Chart") 
    signal = Column(String) 
    entry_data = Column(String) 
    tp_data = Column(String)
    sl_data = Column(String)
    timeframe = Column(String, default="---")
    reason = Column(Text, default="") 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="analyses")

# =========================================================
# 3. محرك الإصلاح والتهجير التلقائي
# =========================================================
def migrate_database():
    with engine.begin() as conn:
        # 1. تفعيل جميع الحسابات فوراً
        conn.execute(text("UPDATE users SET is_verified = TRUE"))
        
        # 2. تنظيف الإيميلات: تحويلها لأحرف صغيرة وإزالة المسافات المخفية
        # هذا يحل مشكلة "العمى" بحيث يرى السيرفر الإيميلات بشكل صحيح
        if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
            conn.execute(text("UPDATE users SET email = LOWER(TRIM(email))"))
        
        print("✅ تم تنظيف قاعدة البيانات وفتح كافة الأقفال بنجاح")

# بناء الجداول
Base.metadata.create_all(bind=engine)

# تشغيل الإصلاح
migrate_database()