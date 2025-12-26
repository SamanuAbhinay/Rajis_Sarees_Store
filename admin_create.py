from app import app, db, User

with app.app_context():
    admin = User.query.filter_by(email="admin@gmail.com").first()
    if admin:
        admin.is_admin = True
        db.session.commit()
        print("Admin created successfully")
    else:
        print("User not found")
