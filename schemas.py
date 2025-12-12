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