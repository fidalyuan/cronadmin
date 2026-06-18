from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.session import engine, async_session_factory
from sqlalchemy import select
from app.models.models import Base, User
from app.api.auth_routes import router as auth_router
from app.api.task_routes import router as task_router
from app.api.port_routes import router as port_router
from app.api.env_routes import router as env_router
from app.services.scheduler_service import scheduler_service
from app.core.security import get_password_hash
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

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
        
    # 初始化默认管理员
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            logger.info("未发现管理员账号，正在初始化默认账号 (admin / admin123)...")
            import hashlib
            # admin123 对应的 SHA-256 (前端传递的值)
            default_sha256 = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
            default_user = User(username="admin", hashed_password=get_password_hash(default_sha256))
            db.add(default_user)
            await db.commit()
    
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

@app.get("/")
async def root():
    return {"message": "CronAdmin API is running"}
