from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.schema import User

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role
        }
    finally:
        db.close()
