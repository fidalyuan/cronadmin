from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.session import engine, async_session_factory
from sqlalchemy import select, text
from app.models.models import Base, User, RuntimeEnvironment, TaskDefinition
from app.api.auth_routes import router as auth_router
from app.api.task_routes import router as task_router
from app.api.port_routes import router as port_router
from app.api.env_routes import router as env_router
from app.services.scheduler_service import scheduler_service
from app.core.security import get_password_hash
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os

# 配置 Loguru
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在启动 CronAdmin 后端服务...")
    # Startup: Create tables
    async with engine.begin() as conn:
        logger.info("正在同步数据库表结构...")
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE port_configs ADD COLUMN is_valid BOOLEAN DEFAULT 1"))
            logger.info("已成功尝试为 port_configs 表添加 is_valid 字段。")
        except Exception:
            pass
        
    # 初始化默认管理员及默认运行环境与任务
    async with async_session_factory() as db:
        # 1. 默认管理员
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            logger.info("未发现管理员账号，正在初始化默认账号 (admin / admin123)...")
            import hashlib
            # admin123 对应的 SHA-256 (前端传递的值)
            default_sha256 = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
            default_user = User(username="admin", hashed_password=get_password_hash(default_sha256))
            db.add(default_user)
            await db.commit()

        # 2. 默认 Python 运行环境
        default_interpreter = os.getenv("CRONADMIN_PYTHON", sys.executable)
        if default_interpreter:
            env_result = await db.execute(select(RuntimeEnvironment).where(RuntimeEnvironment.interpreter_path == default_interpreter))
            if not env_result.scalars().first():
                logger.info(f"正在同步环境变量配置的 Python 环境至系统运行环境: {default_interpreter}")
                env_name = "default"
                name_check = await db.execute(select(RuntimeEnvironment).where(RuntimeEnvironment.name == env_name))
                if name_check.scalars().first():
                    env_name = "default_python"
                
                default_env = RuntimeEnvironment(
                    name=env_name,
                    interpreter_path=default_interpreter,
                    description="系统启动时自动加载的默认 Python 环境"
                )
                db.add(default_env)
                await db.commit()

        # 3. 默认 Demo 任务 conf/heavy_task.py
        task_result = await db.execute(select(TaskDefinition).where(TaskDefinition.script_path == "conf/heavy_task.py"))
        if not task_result.scalars().first():
            logger.info("未发现默认 Demo 任务，正在创建...")
            demo_task = TaskDefinition(
                name="🔥 重压测试任务 (大日志)",
                script_path="conf/heavy_task.py",
                python_interpreter=None,
                cron_expression="0 * * * *",
                is_active=True,
                environment_params={"TEST_MODE": "true"}
            )
            db.add(demo_task)
            await db.commit()
            logger.success("默认 Demo 任务已成功同步到数据库中。")
    
    # Initialize SchedulerService
    logger.info("正在启动任务调度引擎...")
    await scheduler_service.start()
    
    logger.success("CronAdmin 后端服务已就绪！")
    yield
    
    # Shutdown: Clean up resources
    logger.info("正在关闭服务并清理资源...")
    await scheduler_service.stop()
    await engine.dispose()
    logger.info("服务已停止。")

app = FastAPI(
    title="CronAdmin API",
    description="Dynamic Task Scheduling and Port Management System",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境建议收窄
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(port_router, prefix="/api/v1")
app.include_router(env_router, prefix="/api/v1")

# 挂载前端打包文件 (生产环境)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

# 仅在非 dev 模式下挂载前端静态打包文件
if os.getenv("CRONADMIN_MODE") != "dev" and os.path.exists(frontend_dist_dir):
    assets_dir = os.path.join(frontend_dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def root():
    if os.getenv("CRONADMIN_MODE") != "dev":
        index_path = os.path.join(frontend_dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"message": "CronAdmin API is running"}

@app.exception_handler(404)
async def custom_404_handler(request, exc):
    if not request.url.path.startswith("/api") and os.getenv("CRONADMIN_MODE") != "dev":
        index_path = os.path.join(frontend_dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})

