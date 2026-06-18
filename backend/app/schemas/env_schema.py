from pydantic import BaseModel, ConfigDict

class RuntimeEnvBase(BaseModel):
    name: str
    interpreter_path: str
    description: str | None = None

class RuntimeEnvCreate(RuntimeEnvBase):
    pass

class RuntimeEnvRead(RuntimeEnvBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
