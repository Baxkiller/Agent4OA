from pydantic import BaseModel, Field
from datetime import datetime

class ModelResponse(BaseModel):
    agent_id: str = Field(..., description="AI代理ID")
    agent_content: str = Field(..., description="AI回复内容")
    to_user_id: str = Field(..., description="接收用户ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间") 