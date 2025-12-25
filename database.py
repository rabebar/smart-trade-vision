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
    
    is_verified = Column(Boolean, default=False) # حالة تفعيل الإيميل
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
# 3. محرك الهجرة التلقائية (Auto-Migration Engine)
# =========================================================
def migrate_database():
    inspector = inspect(engine)
    
    if "users" in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns("users")]
        
        expected_columns = {
            "is_admin": "BOOLEAN DEFAULT FALSE",
            "is_premium": "BOOLEAN DEFAULT FALSE",
            "is_whale": "BOOLEAN DEFAULT FALSE",
            "full_name": "VARCHAR DEFAULT 'Trader'",
            "whatsapp": "VARCHAR DEFAULT ''",
            "tier": "VARCHAR DEFAULT 'Trial'",
            "credits": "INTEGER DEFAULT 3",
            "is_verified": "BOOLEAN DEFAULT FALSE"
        }

        # استخدام engine.begin() يضمن فتح "ترانزكشن" واحد وإغلاقه بنجاح (حل مشكلة ريندر)
        with engine.begin() as conn:
            for column, col_type in expected_columns.items():
                if column not in columns:
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {col_type}"))
                        print(f"✅ تم تحديث قاعدة البيانات: إضافة عمود {column}")
                    except Exception as e:
                        print(f"⚠️ تنبيه أثناء إضافة عمود {column}: {e}")

            # [حقن الأمان] تفعيل الحسابات الحالية باستخدام TRUE المتوافقة مع PostgreSQL
            conn.execute(text("UPDATE users SET is_verified = TRUE"))
            print("✅ تم تفعيل كافة الحسابات بنجاح.")

# بناء الجداول الأساسية
Base.metadata.create_all(bind=engine)

# تشغيل المهاجر التلقائي
migrate_database()