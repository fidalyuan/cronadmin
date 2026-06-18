from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db_session
from app.models.models import PortConfig, TaskDefinition
from app.schemas.port_schema import PortRead, PortCreate
from app.services.port_service import PortService
from app.services.scheduler_service import scheduler_service
import asyncio
from typing import List
from pydantic import BaseModel
from loguru import logger

class PortNameUpdate(BaseModel):
    service_name: str

class PortLabelUpdate(BaseModel):
    custom_label: str | None

class PortManagementUpdate(BaseModel):
    is_monitored: bool
    recovery_task_id: int | None

from app.core.security import get_current_user

router = APIRouter(prefix="/ports", tags=["端口与容器管理"], dependencies=[Depends(get_current_user)])

@router.put("/{port}/management")
async def update_port_management(port: int, payload: PortManagementUpdate, db: AsyncSession = Depends(get_db_session)):
    """更新端口的管理/自愈配置"""
    logger.info(f"正在更新端口 {port} 的管理配置: monitored={payload.is_monitored}, task={payload.recovery_task_id}")
    result = await db.execute(select(PortConfig).where(PortConfig.port == port))
    db_port = result.scalars().first()
    
    if db_port:
        db_port.is_monitored = payload.is_monitored
        db_port.recovery_task_id = payload.recovery_task_id
    else:
        # 尝试查找当前运行的进程名作为初始 service_name
        import psutil
        current_proc_name = "unknown"
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN' and conn.laddr.port == port and conn.pid:
                    proc = psutil.Process(conn.pid)
                    current_proc_name = proc.name()
                    break
        except Exception:
            pass
        db_port = PortConfig(
            port=port, 
            service_name=current_proc_name, 
            is_monitored=payload.is_monitored, 
            recovery_task_id=payload.recovery_task_id
        )
        db.add(db_port)
        
    await db.commit()
    logger.success(f"端口 {port} 管理配置更新成功。")
    return {"message": "success"}

@router.put("/{port}/label")
async def update_port_label(port: int, payload: PortLabelUpdate, db: AsyncSession = Depends(get_db_session)):
    """允许用户自定义修改端口的分组标签 (Upsert)"""
    logger.info(f"正在修改端口 {port} 的分组标签为: {payload.custom_label}")
    result = await db.execute(select(PortConfig).where(PortConfig.port == port))
    db_port = result.scalars().first()
    
    if db_port:
        db_port.custom_label = payload.custom_label
    else:
        # 如果数据库中没有该端口配置，则新建一个
        import psutil
        current_proc_name = "unknown"
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN' and conn.laddr.port == port and conn.pid:
                    proc = psutil.Process(conn.pid)
                    current_proc_name = proc.name()
                    break
        except Exception:
            pass
        db_port = PortConfig(port=port, service_name=current_proc_name, custom_label=payload.custom_label, is_monitored=False)
        db.add(db_port)
        
    await db.commit()
    logger.success(f"端口 {port} 分组标签修改保存成功。")
    return {"message": "success"}

@router.put("/{port}/name")
async def update_port_name(port: int, payload: PortNameUpdate, db: AsyncSession = Depends(get_db_session)):
    """允许用户自定义修改端口用途名称 (Upsert)"""
    logger.info(f"正在修改端口 {port} 的用途名称为: {payload.service_name}")
    result = await db.execute(select(PortConfig).where(PortConfig.port == port))
    db_port = result.scalars().first()
    
    if db_port:
        db_port.service_name = payload.service_name
    else:
        db_port = PortConfig(port=port, service_name=payload.service_name, is_monitored=False)
        db.add(db_port)
        
    await db.commit()
    logger.success(f"端口 {port} 名称修改保存成功。")
    return {"message": "success"}

@router.get("/status")
async def get_all_port_status():
    """获取受控端口的实时状态列表 [F-401]"""
    return await PortService.get_port_status()

@router.post("/{port}/restart")
async def restart_service(port: int, db: AsyncSession = Depends(get_db_session)):
    """智能重启逻辑：如果是容器则重启容器，如果是受控进程则触发恢复任务 [F-403 增强]"""
    logger.warning(f"收到重启请求：端口 {port}")
    
    # 1. 尝试查找 Podman 容器
    target_pid = None
    try:
        import psutil
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                target_pid = conn.pid
                break
    except Exception:
        pass

    container_name = None
    try:
        process = await asyncio.create_subprocess_exec(
            "podman", "ps", "--format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        if stdout:
            import json
            containers = json.loads(stdout.decode('utf-8'))
            for container in containers:
                ports = container.get("Ports") or container.get("ports") or []
                c_pid = container.get("Pid") or container.get("pid")
                match = False
                if isinstance(ports, list):
                    for p_info in ports:
                        h_port = p_info.get("host_port") or p_info.get("HostPort")
                        if h_port and int(h_port) == port:
                            match = True; break
                if not match and target_pid and c_pid and int(c_pid) == target_pid:
                    match = True
                
                if match:
                    container_name = (container.get("Names") or container.get("names") or [""])[0]
                    break
    except Exception as e:
        logger.error(f"Podman 匹配异常: {e}")

    if container_name:
        logger.info(f"检测到 Podman 容器 [{container_name}]，执行 podman restart...")
        res = await asyncio.create_subprocess_exec("podman", "restart", container_name)
        await res.wait()
        if res.returncode == 0:
            logger.success(f"容器 {container_name} 重启成功。")
            return {"message": f"容器 {container_name} 重启成功"}
        raise HTTPException(status_code=500, detail=f"容器 {container_name} 重启失败")

    # 2. 如果不是容器，检查是否绑定了恢复任务
    result = await db.execute(select(PortConfig).where(PortConfig.port == port))
    db_port = result.scalars().first()
    if db_port and db_port.recovery_task_id:
        logger.info(f"检测到受控进程绑定了恢复任务 ID:{db_port.recovery_task_id}，正在触发脚本...")
        recovery_task = await db.get(TaskDefinition, db_port.recovery_task_id)
        if recovery_task:
            asyncio.create_task(scheduler_service.run_task_script(
                recovery_task.id, recovery_task.script_path, recovery_task.python_interpreter, recovery_task.environment_params
            ))
            logger.success(f"已成功下发恢复脚本: {recovery_task.name}")
            return {"message": "已成功触发进程恢复任务"}
    
    logger.error(f"端口 {port} 无法重启: 既非容器也未绑定恢复任务。")
    raise HTTPException(status_code=400, detail="该端口关联的进程无法自动重启（非容器且未绑定恢复脚本）")

@router.post("/{port}/restart-container")
async def restart_podman_container(port: int, db: AsyncSession = Depends(get_db_session)):
    """保持旧路径兼容性"""
    return await restart_service(port, db)

@router.get("/", response_model=List[PortRead])
async def read_ports(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(PortConfig))
    return result.scalars().all()

@router.post("/", response_model=PortRead)
async def create_port_config(port: PortCreate, db: AsyncSession = Depends(get_db_session)):
    db_port = PortConfig(**port.model_dump())
    db.add(db_port)
    await db.commit()
    await db.refresh(db_port)
    return db_port
