from datetime import datetime
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class TaskDefinition(Base):
    __tablename__ = "task_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    script_path: Mapped[str]
    python_interpreter: Mapped[str | None] = mapped_column(nullable=True) # 自定义 Python 环境路径
    cron_expression: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    config_hash: Mapped[str | None] = mapped_column(nullable=True)  # 用于热加载校验
    environment_params: Mapped[dict | None] = mapped_column(JSON, nullable=True) # JSON 格式参数
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(index=True)
    start_time: Mapped[datetime] = mapped_column(server_default=func.now())
    end_time: Mapped[datetime | None] = mapped_column(nullable=True)
    exit_code: Mapped[int | None] = mapped_column(nullable=True)
    log_file_path: Mapped[str | None] = mapped_column(nullable=True)
    stdout: Mapped[str | None] = mapped_column(nullable=True)
    stderr: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default="running") # running, success, failed, timeout

class RuntimeEnvironment(Base):
    __tablename__ = "runtime_environments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    interpreter_path: Mapped[str]
    description: Mapped[str | None] = mapped_column(nullable=True)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)

class PortConfig(Base):
    __tablename__ = "port_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    port: Mapped[int] = mapped_column(unique=True, index=True)
    service_name: Mapped[str]
    custom_label: Mapped[str | None] = mapped_column(nullable=True) # 自定义分组标签
    recovery_task_id: Mapped[int | None] = mapped_column(nullable=True) # 关联的自动自愈任务
    is_monitored: Mapped[bool] = mapped_column(default=True)
    is_valid: Mapped[bool] = mapped_column(default=True)
