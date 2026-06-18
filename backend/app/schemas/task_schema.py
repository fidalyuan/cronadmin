from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any

class TaskBase(BaseModel):
    name: str
    script_path: str
    python_interpreter: str | None = None
    cron_expression: str
    is_active: bool = True
    environment_params: dict[str, Any] | None = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    name: str | None = None
    script_path: str | None = None
    cron_expression: str | None = None
    is_active: bool | None = None

class TaskRead(TaskBase):
    id: int
    config_hash: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskLogRead(BaseModel):
    id: int
    task_id: int
    start_time: datetime
    end_time: datetime | None = None
    exit_code: int | None = None
    log_file_path: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)
