from database import SessionLocal, User
db = SessionLocal()
email = input("اكتب إيميلك اللي سجلت فيه: ")
user = db.query(User).filter(User.email == email).first()
if user:
    user.is_admin = True
    user.credits = 1000
    db.commit()
    print("✅ مبروك! أصبحت مديراً للنظام (Admin).")
else:
    print("❌ الإيميل غير موجود.")