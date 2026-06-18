from pydantic import BaseModel, ConfigDict

class PortBase(BaseModel):
    port: int
    service_name: str
    custom_label: str | None = None
    recovery_task_id: int | None = None
    is_monitored: bool = True

class PortCreate(PortBase):
    pass

class PortRead(PortBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
