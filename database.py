from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# رابط قاعدة البيانات من Render
DATABASE_URL = os.getenv("DATABASE_URL")

# إنشاء الاتصال (Render-compatible SSL)
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

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    credits = Column(Integer, default=3)
    is_premium = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

def create_db():
    Base.metadata.create_all(bind=engine)
