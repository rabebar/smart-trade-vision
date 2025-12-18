from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    email: str
    credits: int
    is_premium: bool

    class Config:
        from_attributes = True

# ✅ للـ Admin فقط (بدون password_hash)
class AdminUserOut(BaseModel):
    id: int
    email: str
    credits: int
    is_premium: bool
    is_admin: bool

    class Config:
        from_attributes = True


# ✅ Analyze Response (AR + EN) without extra credit charges
class AnalyzeResponse(BaseModel):
    signal: str
    entry: str
    tp: str
    sl: str
    timeframe: str
    session: str
    validity: str

    notes_ar: str
    notes_en: str
    reason_ar: str
    reason_en: str

    remaining_credits: int
