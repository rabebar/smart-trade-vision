# هذا هو ملف set_admin.py كاملاً
from database import SessionLocal, User

def make_admin():
    db = SessionLocal()
    print("--- نظام تفعيل رتبة الملك (CANA King Mode) ---")
    
    # اطلب الإيميل من المستخدم
    email_input = input("اكتب الإيميل الذي سجلت به في الموقع: ").lower().strip()
    
    # البحث عن المستخدم في قاعدة البيانات
    user = db.query(User).filter(User.email == email_input).first()
    
    if user:
        # تفعيل كل الصلاحيات
        user.is_admin = True
        user.is_premium = True
        user.is_whale = True
        user.tier = "Platinum"
        user.credits = 9999  # رصيد ضخم جداً
        
        db.commit() # حفظ التغييرات في قاعدة البيانات
        print(f"\n✅ نجاح! الحساب {email_input} أصبح الآن مديراً للنظام (Admin) ولديه رصيد كامل 👑.")
    else:
        print("\n❌ خطأ: هذا الإيميل غير موجود. تأكد أنك أنشأت الحساب أولاً من صفحة التسجيل في الموقع.")
    
    db.close()

if __name__ == "__main__":
    make_admin()