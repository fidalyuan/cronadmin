from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db_session
from app.models.models import RuntimeEnvironment
from app.schemas.env_schema import RuntimeEnvRead, RuntimeEnvCreate
from typing import List
from loguru import logger

from app.core.security import get_current_user

router = APIRouter(prefix="/environments", tags=["环境配置"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=List[RuntimeEnvRead])
async def read_environments(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(RuntimeEnvironment))
    return result.scalars().all()

@router.post("/", response_model=RuntimeEnvRead)
async def create_environment(env: RuntimeEnvCreate, db: AsyncSession = Depends(get_db_session)):
    db_env = RuntimeEnvironment(**env.model_dump())
    db.add(db_env)
    await db.commit()
    await db.refresh(db_env)
    logger.success(f"运行环境 [{env.name}] 已保存。")
    return db_env

@router.delete("/{env_id}")
async def delete_environment(env_id: int, db: AsyncSession = Depends(get_db_session)):
    db_env = await db.get(RuntimeEnvironment, env_id)
    if not db_env:
        raise HTTPException(status_code=404, detail="环境不存在")
    await db.delete(db_env)
    await db.commit()
    return {"message": "success"}
