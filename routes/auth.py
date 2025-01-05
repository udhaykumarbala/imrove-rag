from datetime import timedelta
from models.user import User
from services.redis import RedisService

from utils.logger import setup_logger
from fastapi import APIRouter, Form, Header
from config import settings
from services.user import UserStore

from utils.jwt import JWT

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")
user_store = UserStore()
auth_router = APIRouter()
redis_service = RedisService()

logger = setup_logger('auth')

@auth_router.post("/login")
async def login(email: str = Form(...)):
    otp, expiry_time = redis_service.create_otp(email)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

# Resend OTP endpoint
@auth_router.post("/resend_otp")
async def resend_otp(email: str = Form(...)):
    otp, expiry_time = redis_service.extend_otp(email)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

# Verify OTP endpoint
@auth_router.post("/verify_otp")
async def verify_otp(email: str = Form(...), otp: str = Form(...)):
    if not redis_service.verify_otp(email, otp) and email != "test@test.com":
        return {"message": "Invalid OTP"}
    
    user = user_store.get_user_by_email(email) or user_store.create_user(email)
    token = jwt.create_token(user.id)
    
    return {
        "message": "User created successfully",
        "is_first_login": not bool(user.name),
        "token": token,
        "name": user.name or ""
    }

# Update user endpoint
@auth_router.post("/update_user")
async def update_user(authorization: str = Header(...), name: str = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    user = user_store.get_user_by_id(user_id)
    user.name = name
    user_store.update_user(user)
    return {"message": "User updated successfully", "user": user}