# 從 app.py 導入 app 實例
from app import app, db, User
from werkzeug.security import generate_password_hash

# 確保應用程式上下文
with app.app_context():
    # 檢查並創建/更新管理員
    user = User.query.filter_by(username='yukari17').first()
    if user:
        user.is_admin = True
        db.session.commit()
        print("User 'yukari17' set as admin successfully!")
    else:
        admin_user = User(username='yukari17', password_hash=generate_password_hash('admin123'), is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user 'yukari17' created and set successfully!")