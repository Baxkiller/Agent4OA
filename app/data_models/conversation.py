from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class Conversation(BaseModel):
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    speaker: Literal["user", "assistant"] = Field(..., description="说话者类型")
    message: str = Field(..., description="消息内容")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="消息创建时间") 