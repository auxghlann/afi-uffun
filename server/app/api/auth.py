from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4

from app.services.database import get_user_by_email

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: str
    user_id: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = await get_user_by_email(request.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In a real app, use password hashing (bcrypt/argon2)
    if user.get("password_hash") != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = str(uuid4())
    return LoginResponse(
        token=token, 
        role=user.get("role", "caller"), 
        user_id=str(user.get("id"))
    )
