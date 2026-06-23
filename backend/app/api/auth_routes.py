from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.database.session import get_db_session
from app.models.models import User
from app.core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

import os

router = APIRouter(prefix="/auth", tags=["认证授权"])

@router.get("/config")
async def get_config():
    return {"mode": os.getenv("CRONADMIN_MODE", "prod")}


@router.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)):
    """
    用户登录接口。前端应发送 SHA256 处理后的密码作为 password 字段。
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    import asyncio
    is_password_correct = False
    if user:
        is_password_correct = await asyncio.to_thread(verify_password, form_data.password, user.hashed_password)
        
    if not user or not is_password_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
