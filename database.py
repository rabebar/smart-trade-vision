from sqlalchemy import create_engine, Column, Integer, String, Boolean, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# ===========================
# Load ENV
# ===========================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# ===========================
# Normalize DATABASE URL
# ===========================

# Fix old postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Force SQLAlchemy to use psycopg v3 explicitly
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )

# ===========================
# Engine
# ===========================
e# 🔴 إجبار psycopg v3 بدون الاعتماد على scheme من البيئة
engine = create_engine(
    "postgresql+psycopg://" + DATABASE_URL.split("://", 1)[1],
    pool_pre_ping=True,
    future=True,
    connect_args={"sslmode": "require"}
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True
)

Base = declarative_base()

# ===========================
# User Model
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
# Create tables
# ===========================
Base.metadata.create_all(bind=engine)

# ===========================
# DB Health Check
# ===========================
def test_db_connection():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()
    return True
