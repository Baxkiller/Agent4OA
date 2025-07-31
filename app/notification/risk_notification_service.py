from app.data_models import RiskNotification
from datetime import datetime
from typing import Optional

class RiskNotificationService:
    """跨端风险通知服务"""
    def __init__(self):
        # 这里可以初始化通知渠道，如短信、推送等
        pass

    def send_notification(self, elder_user_id: str, child_user_id: str, content_type: str, risk_level: str, platform: str, suggestion: Optional[str] = None) -> RiskNotification:
        """
        组装并发送风险通知（初版为模拟发送，实际可扩展为推送、短信等）
        """
        notification = RiskNotification(
            notification_id=f"notif_{datetime.now().timestamp()}",
            elder_user_id=elder_user_id,
            child_user_id=child_user_id,
            content_type=content_type,
            risk_level=risk_level,
            platform=platform,
            suggestion=suggestion,
            detected_at=datetime.now(),
            status="sent"
        )
        # 这里可以扩展为实际发送逻辑，如调用第三方API
        print(f"[通知已发送] {notification}")
        return notification 