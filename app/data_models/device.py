from pydantic import BaseModel, Field
from typing import Optional

class Device(BaseModel):
    device_id: str = Field(..., description="设备ID")
    device_name: str = Field(..., description="设备名称")
    Android_version: Optional[str] = Field(None, description="Android系统版本") 