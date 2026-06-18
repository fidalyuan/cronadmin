from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db_session
from app.models.models import TaskDefinition, TaskLog
from app.schemas.task_schema import TaskRead, TaskCreate, TaskUpdate, TaskLogRead
from app.services.scheduler_service import scheduler_service
import asyncio
from typing import List
from loguru import logger

from app.core.security import get_current_user

router = APIRouter(prefix="/tasks", tags=["任务管理"], dependencies=[Depends(get_current_user)])

@router.get("/logs/{log_id}/file")
async def download_log_file(log_id: int, db: AsyncSession = Depends(get_db_session)):
    logger.debug(f"正在请求读取日志文件，日志 ID: {log_id}")
    log_db = await db.get(TaskLog, log_id)
    if not log_db or not log_db.log_file_path or not os.path.exists(log_db.log_file_path):
        logger.error(f"日志文件不存在或路径无效: {log_db.log_file_path if log_db else 'ID无效'}")
        raise HTTPException(status_code=404, detail="日志文件不存在")
    return FileResponse(log_db.log_file_path, media_type="text/plain")

@router.get("/", response_model=List[TaskRead])
async def read_tasks(db: AsyncSession = Depends(get_db_session)):
    logger.debug("正在查询所有任务列表...")
    result = await db.execute(select(TaskDefinition))
    tasks = result.scalars().all()
    logger.debug(f"成功获取 {len(tasks)} 个任务。")
    return tasks

@router.post("/", response_model=TaskRead)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db_session)):
    logger.info(f"正在创建新任务: {task.name}")
    db_task = TaskDefinition(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    
    # 尝试触发热重载
    try:
        await scheduler_service.reload_tasks()
        logger.success(f"任务 [{task.name}] 创建成功并已热加载到调度器。")
    except Exception as e:
        logger.warning(f"任务已保存，但调度器热加载失败: {e}")
        
    return db_task

@router.get("/{task_id}", response_model=TaskRead)
async def read_task(task_id: int, db: AsyncSession = Depends(get_db_session)):
    db_task = await db.get(TaskDefinition, task_id)
    if not db_task:
        logger.error(f"获取任务失败: ID {task_id} 不存在")
        raise HTTPException(status_code=404, detail="任务不存在")
    return db_task

@router.put("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, task: TaskUpdate, db: AsyncSession = Depends(get_db_session)):
    logger.info(f"正在更新任务 ID: {task_id}")
    db_task = await db.get(TaskDefinition, task_id)
    if not db_task:
        logger.error(f"更新失败: 任务 ID {task_id} 不存在")
        raise HTTPException(status_code=404, detail="任务不存在")
    
    update_data = task.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    await db.commit()
    await db.refresh(db_task)
    
    # 尝试触发热重载
    try:
        await scheduler_service.reload_tasks()
        logger.success(f"任务 ID: {task_id} 配置更新成功并已同步至调度器。")
    except Exception as e:
        logger.warning(f"任务配置已更新，但调度器同步失败: {e}")
        
    return db_task

@router.post("/{task_id}/toggle", response_model=TaskRead)
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db_session)):
    db_task = await db.get(TaskDefinition, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    db_task.is_active = not db_task.is_active
    logger.info(f"切换任务 ID: {task_id} 状态至: {'启用' if db_task.is_active else '禁用'}")
    await db.commit()
    await db.refresh(db_task)
    
    await scheduler_service.reload_tasks()
    return db_task

@router.post("/{task_id}/run")
async def run_task_now(task_id: int, db: AsyncSession = Depends(get_db_session)):
    logger.info(f"收到手动执行请求，任务 ID: {task_id}")
    db_task = await db.get(TaskDefinition, task_id)
    if not db_task:
        logger.error(f"执行失败: 任务 ID {task_id} 不存在")
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 立即异步触发
    asyncio.create_task(scheduler_service.run_task_script(
        db_task.id, db_task.script_path, db_task.python_interpreter, db_task.environment_params
    ))
    return {"message": f"任务 {task_id} 已手动触发执行"}

@router.get("/{task_id}/logs", response_model=List[TaskLogRead])
async def read_task_logs(task_id: int, limit: int = 50, db: AsyncSession = Depends(get_db_session)):
    logger.debug(f"正在查询任务 ID: {task_id} 的执行历史 (限制 {limit} 条)...")
    result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.start_time.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    logger.debug(f"成功获取 {len(logs)} 条执行历史记录。")
    return logs
