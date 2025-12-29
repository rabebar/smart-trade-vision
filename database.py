import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

# =========================================================
# إعداد قاعدة البيانات (الربط الذكي بالسحابة)
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

# تصحيح الرابط ليتوافق مع السيرفرات السحابية
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = DATABASE_URL or "sqlite:///./sql_app.db"

# إعداد المحرك (استخدام pool_pre_ping لضمان عدم انقطاع الاتصال في ريندر)
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================================================
# 1. جدول المستخدمين (Users Table)
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
    
    # حقول الحماية والتوثيق الجديدة
    is_verified = Column(Boolean, default=False) 
    verified_at = Column(DateTime, nullable=True)        # تاريخ التوثيق
    verification_method = Column(String, default="None") # (Manual / WhatsApp / System)
    registration_ip = Column(String, default="0.0.0.0")  # بصمة الجهاز لمنع البوتات
    is_flagged = Column(Boolean, default=False)          # وسم الحسابات المشبوهة
    
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    is_whale = Column(Boolean, default=False) 

    analyses = relationship("Analysis", back_populates="owner", cascade="all, delete-orphan")

# =========================================================
# 2. جدول التحليلات (Portfolio/Analysis Table)
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
# 3. جدول غرفة التحرير (Articles Table)
# =========================================================
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text)
    content = Column(Text)
    image_url = Column(String)
    language = Column(String, default="ar")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# =========================================================
# 4. جدول مساحات الإعلانات (Sponsors/Ads Table)
# =========================================================
class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    image_url = Column(String)
    link_url = Column(String)
    location = Column(String, default="main")
    is_active = Column(Boolean, default=True)

# =========================================================
# 3. محرك الهجرة التلقائية (Auto-Migration Engine)
# =========================================================
def migrate_database():
    """
    وظيفة ذكية: تضيف الأعمدة الجديدة لقاعدة البيانات إذا لم تكن موجودة
    لضمان عدم حدوث أخطاء عند تحديث السيرفر.
    """
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns("users")]
    
    try:
        with engine.begin() as conn:
            # 1. إضافة أعمدة الحماية إذا نقصت (متوافق مع PostgreSQL و SQLite)
            if "registration_ip" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN registration_ip VARCHAR DEFAULT '0.0.0.0'"))
            if "is_flagged" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_flagged BOOLEAN DEFAULT FALSE"))
            if "verified_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verified_at TIMESTAMP NULL"))
            if "verification_method" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_method VARCHAR DEFAULT 'None'"))

            # 2. توحيد الإيميلات لضمان الدقة
            if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
                conn.execute(text("UPDATE users SET email = LOWER(TRIM(email))"))
                
            print("✅ تم تحديث بنية قاعدة البيانات وإضافة حقول الحماية بنجاح")
    except Exception as e:
        print(f"⚠️ تنبيه أثناء التحديث: {e}")

# تشغيل المهاجر
Base.metadata.create_all(bind=engine)
migrate_database()