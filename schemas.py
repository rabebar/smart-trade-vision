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
    
    # حقول الأمان
    is_verified: bool
    registration_ip: Optional[str] = "0.0.0.0"
    is_flagged: Optional[bool] = False
    verified_at: Optional[datetime] = None
    verification_method: Optional[str] = "None"
    
    # [حقن المرحلة الثانية] حقول الاشتراكات
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None

    class Config:
        from_attributes = True

# ==========================================
# 4. نموذج تحديث بيانات المستخدم من قبل الإدارة
# ==========================================
class AdminUpdateUser(BaseModel):
    user_id: int
    credits: Optional[int] = None
    tier: Optional[str] = None
    is_premium: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_flagged: Optional[bool] = None
    
    # [حقن المرحلة الثانية] زر التجديد
    renew_subscription: Optional[bool] = None 

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