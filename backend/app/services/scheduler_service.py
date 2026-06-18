import asyncio
import hashlib
import json
import subprocess
import os
import aiofiles
from datetime import datetime
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.session import async_session_factory
from app.models.models import TaskDefinition, TaskLog

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.task_hashes: Dict[int, str] = {}
        self._is_running = False

    async def start(self):
        if not self._is_running:
            logger.info("调度引擎启动中...")
            self.scheduler.start()
            self._is_running = True
            # 初始加载任务
            await self.reload_tasks()
            # 开启定时轮询 DB 进行热更新（例如每 30 秒）
            self.scheduler.add_job(self.reload_tasks, "interval", seconds=30, id="system_reload_tasks")
            
            # 开启端口自愈检测（例如每 1 分钟）
            from app.services.port_service import PortService
            self.scheduler.add_job(PortService.check_and_heal, "interval", minutes=1, id="system_port_check")
            logger.success("调度引擎已启动，已开启定时扫描与自愈任务。")

    async def stop(self):
        if self._is_running:
            logger.info("正在关闭调度引擎...")
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("调度引擎已关闭。")

    async def reload_tasks(self):
        """拉取 DB 配置并根据 Hash 值决定是否重载"""
        logger.debug("正在检查数据库以同步任务配置...")
        async with async_session_factory() as db:
            try:
                result = await db.execute(select(TaskDefinition).where(TaskDefinition.is_active == True))
                tasks = result.scalars().all()
                
                current_db_ids = {task.id for task in tasks}
                
                # 1. 删除已在 DB 中禁用或删除的任务
                scheduled_job_ids = {job.id for job in self.scheduler.get_jobs() if job.id.startswith("task_")}
                for job_id in scheduled_job_ids:
                    task_id = int(job_id.replace("task_", ""))
                    if task_id not in current_db_ids:
                        logger.warning(f"任务 ID:{task_id} 已在库中禁用或删除，正在从调度器移除。")
                        self.scheduler.remove_job(job_id)
                        self.task_hashes.pop(task_id, None)

                # 2. 新增或更新任务
                for task in tasks:
                    task_config = {
                        "script_path": task.script_path,
                        "python_interpreter": task.python_interpreter,
                        "cron_expression": task.cron_expression,
                        "env": task.environment_params
                    }
                    config_hash = hashlib.md5(json.dumps(task_config, sort_keys=True).encode()).hexdigest()
                    
                    if self.task_hashes.get(task.id) != config_hash:
                        # 如果 Hash 不一致，更新任务
                        job_id = f"task_{task.id}"
                        if self.scheduler.get_job(job_id):
                            logger.info(f"任务 ID:{task.id} [{task.name}] 配置已变更，正在重新加载...")
                            self.scheduler.remove_job(job_id)
                        else:
                            logger.info(f"发现新任务 ID:{task.id} [{task.name}]，正在注册到调度器...")
                        
                        try:
                            self.scheduler.add_job(
                                self.run_task_script,
                                CronTrigger.from_crontab(task.cron_expression),
                                id=job_id,
                                args=[task.id, task.script_path, task.python_interpreter, task.environment_params],
                                max_instances=1, # 防重叠机制 [F-104]
                                replace_existing=True
                            )
                            self.task_hashes[task.id] = config_hash
                            
                            # 更新 DB 中的 Hash
                            task.config_hash = config_hash
                            await db.commit()
                            logger.success(f"任务 ID:{task.id} [{task.name}] 已成功部署，Cron: {task.cron_expression}")
                        except ValueError as ve:
                            logger.error(f"任务 ID:{task.id} 的 Cron 表达式无效: {ve}")
                            continue
            except Exception as e:
                logger.error(f"同步任务配置时发生异常: {e}")

    async def run_task_script(self, task_id: int, script_path: str, python_interpreter: str | None, env_params: Dict[str, Any] | None):
        """执行脚本并记录日志 [F-103], [F-301], [F-302]"""
        start_time = datetime.now()
        logger.info(f"开始执行任务 ID:{task_id}，脚本: {script_path}，使用环境: {python_interpreter or '默认(pytask)'}")
        
        # 准备日志文件路径
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_filename = f"task_{task_id}_{start_time.strftime('%Y%m%d%H%M%S')}.log"
        log_file_path = os.path.join(log_dir, log_filename)
        
        # 写入初始日志
        async with async_session_factory() as db:
            log = TaskLog(task_id=task_id, start_time=start_time, status="running", log_file_path=log_file_path)
            db.add(log)
            await db.commit()
            await db.refresh(log)
            log_id = log.id

        try:
            # 准备环境变量
            run_env = os.environ.copy()
            if env_params:
                logger.debug(f"正在为任务 {task_id} 注入环境变量: {env_params}")
                # 将 dict 转换为字符串格式以注入环境变量
                for k, v in env_params.items():
                    run_env[k] = str(v)

            # 确定解释器路径，如果未指定则回退到 pytask 环境
            python_path = python_interpreter or "/home/star/miniconda3/envs/pytask/bin/python3"
            
            process = await asyncio.create_subprocess_exec(
                python_path, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=run_env
            )
            
            stdout_preview = []
            stderr_preview = []

            async def read_stream_to_file(stream, preview_buffer, prefix=""):
                async with aiofiles.open(log_file_path, mode='a', encoding='utf-8') as f:
                    line_count = 0
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        decoded_line = line.decode(errors="replace")
                        await f.write(f"{prefix}{decoded_line}")
                        await f.flush()
                        
                        if line_count < 3:
                            preview_buffer.append(decoded_line)
                            line_count += 1
            
            if process.stdout and process.stderr:
                await asyncio.gather(
                    read_stream_to_file(process.stdout, stdout_preview, ""),
                    read_stream_to_file(process.stderr, stderr_preview, "[错误] ")
                )
            
            await process.wait()
            exit_code = process.returncode
            status = "success" if exit_code == 0 else "failed"
            
        except Exception as e:
            err_msg = f"\n[系统错误] {str(e)}"
            logger.critical(f"执行任务 {task_id} 时主进程发生崩溃: {e}")
            async with aiofiles.open(log_file_path, mode='a', encoding='utf-8') as f:
                await f.write(err_msg)
            stderr_preview = [err_msg]
            exit_code = -1
            status = "failed"

        # 回填日志
        async with async_session_factory() as db:
            log_db = await db.get(TaskLog, log_id)
            if log_db:
                log_db.end_time = datetime.now()
                log_db.exit_code = exit_code
                log_db.status = status
                log_db.stdout = "".join(stdout_preview)
                log_db.stderr = "".join(stderr_preview)
                await db.commit()
                
        if status == "success":
            logger.success(f"任务 ID:{task_id} 执行完成 (退出码: 0)")
        else:
            logger.error(f"任务 ID:{task_id} 执行失败 (退出码: {exit_code})")

# 全局单例
scheduler_service = SchedulerService()
