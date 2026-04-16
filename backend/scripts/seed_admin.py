"""Seed default admin user from environment variables."""
import sys
sys.path.insert(0, ".")

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if existing:
            print(f"Admin user already exists: {settings.ADMIN_EMAIL}")
            return

        user = User(
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            name="Admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {settings.ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
