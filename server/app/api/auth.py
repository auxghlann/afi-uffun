from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4

from app.database import SessionLocal
from app.models.schema import User

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    user_id: int

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user or user.password_hash != request.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = str(uuid4())
        return LoginResponse(token=token, role=user.role, user_id=user.id)
    finally:
        db.close()
