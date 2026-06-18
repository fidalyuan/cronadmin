import psutil
import asyncio
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import async_session_factory
from app.models.models import PortConfig, TaskDefinition
from app.services.scheduler_service import scheduler_service
from loguru import logger

class PortService:
    @staticmethod
    async def get_port_status() -> List[Dict]:
        """扫描所有监听端口并标记受控/容器状态 [F-401 增强]"""
        logger.debug("正在执行系统端口扫描...")
        container_ports = set()
        container_pids = set()
        try:
            # 使用 exec 替代 shell，显式处理编码
            process = await asyncio.create_subprocess_exec(
                "podman", "ps", "--format", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                import json
                containers = json.loads(stdout.decode('utf-8'))
                for container in containers:
                    # 记录容器的主进程 PID (支持 Host 网络模式)
                    c_pid = container.get("Pid") or container.get("pid")
                    if c_pid:
                        container_pids.add(int(c_pid))

                    # 记录映射端口 (支持 Bridge 网络模式)
                    ports = container.get("Ports") or container.get("ports") or []
                    if isinstance(ports, list):
                        for p_info in ports:
                            h_port = p_info.get("host_port") or p_info.get("HostPort")
                            p_range = p_info.get("range") or p_info.get("Range") or 1
                            if h_port is not None:
                                try:
                                    base_port = int(h_port)
                                    for i in range(int(p_range)):
                                        container_ports.add(base_port + i)
                                except (ValueError, TypeError):
                                    continue
            logger.debug(f"已识别出 {len(container_pids)} 个运行中的容器。")
        except Exception as e:
            logger.error(f"Podman 状态获取失败: {e}")

        async with async_session_factory() as db:
            result = await db.execute(select(PortConfig))
            managed_configs = {c.port: c for c in result.scalars().all()}
            
            # 获取当前所有监听的端口 (IPv4 & IPv6)
            connections = psutil.net_connections(kind='inet')
            listening_ports = {}
            port_to_pid = {} # 记录每个监听端口对应的 PID
            for conn in connections:
                if conn.status == 'LISTEN':
                    port = conn.laddr.port
                    proc_name = "unknown"
                    if conn.pid:
                        port_to_pid[port] = conn.pid
                        try:
                            process = psutil.Process(conn.pid)
                            proc_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    listening_ports[port] = proc_name
            
            status_list = []
            
            # 1. 首先添加所有在数据库中配置的“管理端口”
            for port, config in managed_configs.items():
                is_up = port in listening_ports
                is_container = (port in container_ports) or (port_to_pid.get(port) in container_pids)
                status_list.append({
                    "port": port,
                    "service_name": config.service_name,
                    "custom_label": config.custom_label,
                    "status": "UP" if is_up else "DOWN",
                    "recovery_task_id": config.recovery_task_id,
                    "is_managed": config.is_monitored,
                    "is_container": is_container,
                    "process_name": listening_ports.get(port, "N/A")
                })
            
            # 2. 其次添加所有“非管理”但正在运行的端口
            for port, proc_name in listening_ports.items():
                if port not in managed_configs:
                    is_container = (port in container_ports) or (port_to_pid.get(port) in container_pids)
                    status_list.append({
                        "port": port,
                        "service_name": proc_name,
                        "custom_label": None,
                        "status": "UP",
                        "recovery_task_id": None,
                        "is_managed": False,
                        "is_container": is_container,
                        "process_name": proc_name
                    })
            
            # 按端口号排序
            logger.debug(f"端口扫描完成，共发现 {len(status_list)} 个监听端口。")
            return sorted(status_list, key=lambda x: x["port"])

    @staticmethod
    async def check_and_heal():
        """执行自愈逻辑 [F-402]"""
        logger.info("执行定时自愈检查...")
        statuses = await PortService.get_port_status()
        heal_count = 0
        for s in statuses:
            if s["status"] == "DOWN" and s["recovery_task_id"]:
                logger.warning(f"检测到受控服务掉线: 端口 {s['port']}，正在尝试自愈...")
                # 触发关联的恢复任务
                async with async_session_factory() as db:
                    recovery_task = await db.get(TaskDefinition, s["recovery_task_id"])
                    if recovery_task:
                        # 立即触发
                        import asyncio
                        asyncio.create_task(scheduler_service.run_task_script(
                            recovery_task.id, recovery_task.script_path, recovery_task.environment_params
                        ))
                        heal_count += 1
        
        if heal_count > 0:
            logger.success(f"自愈检查完成，已下发 {heal_count} 个恢复任务。")
        else:
            logger.debug("自愈检查完成，所有受控服务状态正常。")
