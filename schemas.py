from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ==========================================
# 1. بيانات تسجيل الدخول (Login)
# ==========================================
class UserLogin(BaseModel):
    email: str
    password: str

# ==========================================
# 2. إنشاء مستخدم جديد (Registration)
# ==========================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    whatsapp: Optional[str] = ""
    country: Optional[str] = "Global"
    trader_level: Optional[str] = "Beginner"
    markets: Optional[str] = "Forex"
    tier: Optional[str] = "Trial"

# ==========================================
# 3. البيانات العائدة للمتصفح (User Profile Response)
# هذا النموذج هو المحرك الأساسي لإظهار أزرار الإدارة في الواجهة
# ==========================================
class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str
    whatsapp: Optional[str] = ""
    country: str
    trader_level: str
    markets: str
    tier: str
    status: str
    credits: int
    is_admin: bool
    is_premium: bool
    is_whale: bool

    class Config:
        from_attributes = True

# ==========================================
# 4. نموذج تحديث بيانات المستخدم من قبل الإدارة
# يستخدم في لوحة التحكم (Admin Panel)
# ==========================================
class AdminUpdateUser(BaseModel):
    user_id: int
    credits: Optional[int] = None
    tier: Optional[str] = None
    is_premium: Optional[bool] = None
    is_admin: Optional[bool] = None

# ==========================================
# 5. هيكل سجل التحليلات (Analysis History Response)
# ==========================================
class AnalysisOut(BaseModel):
    id: int
    symbol: str
    signal: str
    entry_data: Optional[str] = "N/A"
    tp_data: Optional[str] = "N/A"
    sl_data: Optional[str] = "N/A"
    timeframe: Optional[str] = "---"
    reason: Optional[str] = ""
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# 6. نموذج ردود الفعل السريعة (Status/Messages)
# ==========================================
class StatusMessage(BaseModel):
    status: str
    message: str