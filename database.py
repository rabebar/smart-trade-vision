import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone

# =========================================================
# إعداد قاعدة البيانات (الربط الذكي بالسحابة)
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
    
    is_verified = Column(Boolean, default=False) 
    verified_at = Column(DateTime, nullable=True)        
    verification_method = Column(String, default="None") 
    registration_ip = Column(String, default="0.0.0.0")  
    is_flagged = Column(Boolean, default=False)          
    
    # [حقن المرحلة الأولى] - تعريف حقول الاشتراك في الجدول
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)

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
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns("users")]
    
    try:
        with engine.begin() as conn:
            # 1. إضافة أعمدة الحماية
            if "registration_ip" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN registration_ip VARCHAR DEFAULT '0.0.0.0'"))
            if "is_flagged" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_flagged BOOLEAN DEFAULT FALSE"))
            if "verified_at" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verified_at TIMESTAMP NULL"))
            if "verification_method" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_method VARCHAR DEFAULT 'None'"))

            # 2. [حقن المرحلة الأولى] إضافة حقول تاريخ الاشتراك لقاعدة البيانات
            if "subscription_start" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_start TIMESTAMP NULL"))
            if "subscription_end" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_end TIMESTAMP NULL"))

            # 3. توحيد الإيميلات
            if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
                conn.execute(text("UPDATE users SET email = LOWER(TRIM(email))"))
                
            print("✅ تم تحديث بنية قاعدة البيانات وإضافة حقول الحماية والاشتراكات بنجاح")
    except Exception as e:
        print(f"⚠️ تنبيه أثناء التحديث: {e}")

# تشغيل المهاجر
Base.metadata.create_all(bind=engine)
migrate_database()