import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL من Render
DATABASE_URL = os.getenv("DATABASE_URL")

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

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)   # UUID مخزن كنص
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)

    credits = Column(Integer, default=3)
    is_premium = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

# ❌ لا تنشئ الجداول هنا
def create_db():
    pass
