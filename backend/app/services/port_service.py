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
    _port_status_cache = []

    @staticmethod
    async def get_port_status() -> List[Dict]:
        """获取受控端口的缓存状态列表 [F-401 增强]"""
        return PortService._port_status_cache

    @staticmethod
    def _parse_proc_net_tcp(content: str) -> set:
        ports = set()
        if not content:
            return ports
        lines = content.strip().split('\n')
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                local_addr = parts[1]
                state = parts[3]
                if state == '0A': # TCP_LISTEN
                    try:
                        _, port_hex = local_addr.split(':')
                        port = int(port_hex, 16)
                        ports.add(port)
                    except Exception:
                        continue
        return ports

    @staticmethod
    async def refresh_port_status_cache():
        """扫描所有监听端口并标记受控/容器状态并更新缓存"""
        logger.debug("正在执行系统端口扫描并更新缓存...")
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
            all_configs = result.scalars().all()
            
            # 获取当前所有监听的端口 (IPv4 & IPv6)
            listening_ports = {}
            port_to_pid = {} # 记录每个监听端口对应的 PID
            
            try:
                connections = psutil.net_connections(kind='inet')
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
            except Exception as e:
                logger.warning(f"无法使用 psutil 获取系统监听端口 (可能受限于平台权限，例如 Android/Termux): {e}")
                
                # 尝试使用 tsu root 权限读取 /proc/net/tcp 和 /proc/net/tcp6
                root_ports = set()
                try:
                    import subprocess
                    res_tcp = subprocess.run(['tsu', '-c', 'cat /proc/net/tcp'], capture_output=True, text=True, timeout=1)
                    res_tcp6 = subprocess.run(['tsu', '-c', 'cat /proc/net/tcp6'], capture_output=True, text=True, timeout=1)
                    if res_tcp.returncode == 0:
                        root_ports.update(PortService._parse_proc_net_tcp(res_tcp.stdout))
                    if res_tcp6.returncode == 0:
                        root_ports.update(PortService._parse_proc_net_tcp(res_tcp6.stdout))
                except Exception as root_e:
                    logger.debug(f"尝试使用 tsu 获取系统端口失败 (平台不支持或未 Root): {root_e}")
                
                if root_ports:
                    logger.info("成功通过 tsu (root 权限) 获取系统监听端口。")
                    for port in root_ports:
                        listening_ports[port] = "active_service"
                else:
                    logger.warning("tsu 执行未成功，将使用 socket 连接法主动探测已配置的端口。")
                    import socket
                    for config in all_configs:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.1) # 快速检测超时
                        try:
                            result_code = s.connect_ex(('127.0.0.1', config.port))
                            if result_code == 0:
                                listening_ports[config.port] = "active_service"
                        except Exception:
                            pass
                        finally:
                            s.close()
            
            # 动态更新数据库中配置的 is_valid 状态
            updated_any = False
            for config in all_configs:
                is_up = config.port in listening_ports
                if not is_up and config.is_valid:
                    config.is_valid = False
                    db.add(config)
                    updated_any = True
                    logger.info(f"端口 {config.port} 当前未在系统监听中发现，已将其在数据库中置为无效（is_valid=False）")
                elif is_up and not config.is_valid:
                    config.is_valid = True
                    db.add(config)
                    updated_any = True
                    logger.info(f"端口 {config.port} 重新在系统监听中发现，已将其在数据库中恢复为有效（is_valid=True）")
            
            if updated_any:
                await db.commit()
                # 重新查询以确保数据最新
                result = await db.execute(select(PortConfig))
                all_configs = result.scalars().all()
            
            status_list = []
            active_managed_ports = {}
            
            # 1. 首先添加所有有效的“管理端口”
            for config in all_configs:
                if config.is_valid:
                    active_managed_ports[config.port] = config
                    is_container = (config.port in container_ports) or (port_to_pid.get(config.port) in container_pids)
                    status_list.append({
                        "port": config.port,
                        "service_name": config.service_name,
                        "custom_label": config.custom_label,
                        "status": "UP",  # 有效的管理端口必然是监听状态，即 UP
                        "recovery_task_id": config.recovery_task_id,
                        "is_managed": config.is_monitored,
                        "is_container": is_container,
                        "process_name": listening_ports.get(config.port, "unknown")
                    })
            
            # 2. 其次添加所有“非管理”但正在监听的端口
            for port, proc_name in listening_ports.items():
                if port not in active_managed_ports:
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
            PortService._port_status_cache = sorted(status_list, key=lambda x: x["port"])
            logger.debug(f"端口扫描与缓存更新完成，共发现 {len(PortService._port_status_cache)} 个监听端口。")

    @staticmethod
    async def check_and_heal():
        """执行自愈逻辑 [F-402]"""
        logger.info("执行定时自愈检查...")
        # 1. 刷新最新端口状态缓存与数据库 is_valid 标记
        await PortService.refresh_port_status_cache()
        
        heal_count = 0
        # 2. 查询所有被监控且当前处于掉线状态的端口配置
        async with async_session_factory() as db:
            result = await db.execute(
                select(PortConfig).where(PortConfig.is_monitored == True, PortConfig.is_valid == False)
            )
            down_configs = result.scalars().all()
            for config in down_configs:
                if config.recovery_task_id:
                    logger.warning(f"检测到受控服务掉线: 端口 {config.port}，正在尝试自愈...")
                    # 触发关联的恢复任务
                    recovery_task = await db.get(TaskDefinition, config.recovery_task_id)
                    if recovery_task:
                        # 立即触发恢复脚本并传入完整的 Python 解释器参数
                        import asyncio
                        asyncio.create_task(scheduler_service.run_task_script(
                            recovery_task.id,
                            recovery_task.script_path,
                            recovery_task.python_interpreter,
                            recovery_task.environment_params
                        ))
                        heal_count += 1
        
        if heal_count > 0:
            logger.success(f"自愈检查完成，已下发 {heal_count} 个恢复任务。")
        else:
            logger.debug("自愈检查完成，所有受控服务状态正常。")
