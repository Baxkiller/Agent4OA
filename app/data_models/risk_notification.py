from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class RiskNotification(BaseModel):
    """跨端风险通知数据模型"""
    notification_id: str
    elder_user_id: str  # 老年人用户ID
    child_user_id: str  # 子女用户ID
    content_type: str   # 内容类型，如诈骗、隐私泄露等
    risk_level: str     # 风险等级，如高、中、低
    platform: str       # 涉及平台，如微信、短信等
    suggestion: Optional[str] = None  # 处理建议
    detected_at: datetime = datetime.now()  # 检测时间
    status: str = "pending"  # 通知状态，如pending, sent, read

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 