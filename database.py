from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# ===========================
# DATABASE CONFIG
# ===========================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# إصلاح postgres:// القديمة
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ===========================
# ENGINE (SSL via connect_args فقط)
# ===========================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ===========================
# USER MODEL
# ===========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    credits = Column(Integer, default=3)
    is_premium = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

# ===========================
# CREATE TABLES
# ===========================
Base.metadata.create_all(bind=engine)
