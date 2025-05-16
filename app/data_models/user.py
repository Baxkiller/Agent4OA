from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class User(BaseModel):
    user_id: str = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名")
    user_gender: Optional[str] = Field(None, description="用户性别")
    user_created_at: datetime = Field(default_factory=datetime.utcnow, description="用户创建时间")
    device_id: Optional[str] = Field(None, description="设备ID")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str} 