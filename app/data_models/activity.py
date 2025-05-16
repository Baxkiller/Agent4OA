from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Activity(BaseModel):
    device_id: str = Field(..., description="设备ID")
    action_type: str = Field(..., description="操作类型")
    position: Optional[str] = Field(None, description="操作位置")
    UI_element: Optional[str] = Field(None, description="UI元素")
    action_time: datetime = Field(default_factory=datetime.utcnow, description="操作时间")
    app_name: Optional[str] = Field(None, description="应用名称")
    app_package_name: Optional[str] = Field(None, description="应用包名")
    screenshot_path: Optional[str] = Field(None, description="截图路径") 