from app.data_models import RiskNotification
from datetime import datetime
from typing import Optional, List
from app.notification.push_service import push_service

class RiskNotificationService:
    """跨端风险通知服务"""
    def __init__(self):
        # 初始化推送服务
        self.push_service = push_service

    async def send_notification(self, elder_user_id: str, child_user_id: str, content_type: str, risk_level: str, platform: str, suggestion: Optional[str] = None, push_methods: List[str] = None) -> RiskNotification:
        """
        组装并发送风险通知，支持多种推送方式
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
        
        # 发送推送通知
        if push_methods:
            push_results = await self.push_service.send_notification(notification, push_methods)
            print(f"[推送结果] {push_results}")
        
        return notification
    
    def configure_email_service(self, sender_email: str, sender_password: str):
        """配置邮件服务"""
        self.push_service.configure_email(sender_email, sender_password)
    
    def configure_sms_service(self, api_key: str, api_secret: str):
        """配置短信服务"""
        self.push_service.configure_sms(api_key, api_secret)
    
    def add_recipient_info(self, user_id: str, info: dict):
        """添加收件人信息"""
        self.push_service.add_recipient_info(user_id, info) 