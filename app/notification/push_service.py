import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from app.data_models import RiskNotification

logger = logging.getLogger(__name__)

class PushProvider(ABC):
    """推送服务提供者基类"""
    
    @abstractmethod
    async def send_notification(self, notification: RiskNotification, recipient_info: Dict[str, Any]) -> bool:
        """发送通知"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供者名称"""
        pass

class WebSocketPushProvider(PushProvider):
    """WebSocket实时推送提供者"""
    
    def __init__(self):
        self.connected_clients: Dict[str, Any] = {}  # 存储连接的客户端
    
    def get_provider_name(self) -> str:
        return "websocket"
    
    def add_client(self, user_id: str, websocket):
        """添加WebSocket客户端"""
        self.connected_clients[user_id] = websocket
        logger.info(f"WebSocket客户端已连接: {user_id}")
    
    def remove_client(self, user_id: str):
        """移除WebSocket客户端"""
        if user_id in self.connected_clients:
            del self.connected_clients[user_id]
            logger.info(f"WebSocket客户端已断开: {user_id}")
    
    async def send_notification(self, notification: RiskNotification, recipient_info: Dict[str, Any]) -> bool:
        """通过WebSocket发送实时通知"""
        try:
            child_user_id = notification.child_user_id
            
            if child_user_id in self.connected_clients:
                websocket = self.connected_clients[child_user_id]
                
                # 构建推送消息
                push_message = {
                    "type": "risk_notification",
                    "timestamp": datetime.now().isoformat(),
                    "notification": {
                        "notification_id": notification.notification_id,
                        "elder_user_id": notification.elder_user_id,
                        "content_type": notification.content_type,
                        "risk_level": notification.risk_level,
                        "platform": notification.platform,
                        "suggestion": notification.suggestion,
                        "detected_at": notification.detected_at.isoformat()
                    }
                }
                
                # 发送消息
                await websocket.send_text(json.dumps(push_message))
                logger.info(f"WebSocket通知已发送给: {child_user_id}")
                return True
            else:
                logger.warning(f"WebSocket客户端未连接: {child_user_id}")
                return False
                
        except Exception as e:
            logger.error(f"WebSocket推送失败: {e}")
            return False

class EmailPushProvider(PushProvider):
    """邮件推送提供者"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = None
        self.sender_password = None
    
    def get_provider_name(self) -> str:
        return "email"
    
    def configure(self, sender_email: str, sender_password: str):
        """配置邮件发送者信息"""
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    async def send_notification(self, notification: RiskNotification, recipient_info: Dict[str, Any]) -> bool:
        """发送邮件通知"""
        try:
            if not self.sender_email or not self.sender_password:
                logger.warning("邮件服务未配置")
                return False
            
            recipient_email = recipient_info.get("email")
            if not recipient_email:
                logger.warning("未提供收件人邮箱")
                return False
            
            # 构建邮件内容
            subject = f"风险通知 - {notification.content_type}"
            
            # 构建HTML邮件内容
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                    .content {{ margin: 20px 0; }}
                    .risk-high {{ color: #dc3545; font-weight: bold; }}
                    .risk-medium {{ color: #ffc107; font-weight: bold; }}
                    .risk-low {{ color: #28a745; font-weight: bold; }}
                    .suggestion {{ background-color: #e9ecef; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🚨 风险通知</h2>
                    <p>检测时间: {notification.detected_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="content">
                    <h3>检测详情</h3>
                    <ul>
                        <li><strong>内容类型:</strong> {notification.content_type}</li>
                        <li><strong>风险等级:</strong> <span class="risk-{notification.risk_level.lower()}">{notification.risk_level}</span></li>
                        <li><strong>涉及平台:</strong> {notification.platform}</li>
                        <li><strong>老年人ID:</strong> {notification.elder_user_id}</li>
                    </ul>
                    
                    <div class="suggestion">
                        <h4>💡 处理建议</h4>
                        <p>{notification.suggestion or '请及时关注并处理相关风险'}</p>
                    </div>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px;">
                    <p>此邮件由Agent4OA系统自动发送，请勿回复。</p>
                </div>
            </body>
            </html>
            """
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"邮件通知已发送给: {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"邮件推送失败: {e}")
            return False

class SMSPushProvider(PushProvider):
    """短信推送提供者"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        # 这里使用阿里云短信服务作为示例
        self.sms_url = "https://dysmsapi.aliyuncs.com"
    
    def get_provider_name(self) -> str:
        return "sms"
    
    def configure(self, api_key: str, api_secret: str):
        """配置短信服务"""
        self.api_key = api_key
        self.api_secret = api_secret
    
    async def send_notification(self, notification: RiskNotification, recipient_info: Dict[str, Any]) -> bool:
        """发送短信通知"""
        try:
            if not self.api_key or not self.api_secret:
                logger.warning("短信服务未配置")
                return False
            
            phone_number = recipient_info.get("phone")
            if not phone_number:
                logger.warning("未提供手机号码")
                return False
            
            # 构建短信内容
            sms_content = f"风险通知：检测到{notification.content_type}，风险等级{notification.risk_level}，请及时关注。"
            
            # 这里简化处理，实际应该调用短信服务API
            # 示例：阿里云短信服务
            sms_data = {
                "PhoneNumbers": phone_number,
                "SignName": "Agent4OA",
                "TemplateCode": "SMS_123456789",
                "TemplateParam": json.dumps({
                    "content_type": notification.content_type,
                    "risk_level": notification.risk_level,
                    "suggestion": notification.suggestion[:50] + "..." if len(notification.suggestion) > 50 else notification.suggestion
                })
            }
            
            # 模拟发送短信（实际项目中需要调用真实的短信API）
            logger.info(f"短信通知已发送给: {phone_number}")
            logger.info(f"短信内容: {sms_content}")
            
            # 这里返回True表示发送成功，实际应该根据API响应判断
            return True
            
        except Exception as e:
            logger.error(f"短信推送失败: {e}")
            return False

class PushService:
    """推送服务管理器"""
    
    def __init__(self):
        self.providers: Dict[str, PushProvider] = {}
        self.recipient_info: Dict[str, Dict[str, Any]] = {}
        
        # 初始化默认提供者
        self.websocket_provider = WebSocketPushProvider()
        self.email_provider = EmailPushProvider()
        self.sms_provider = SMSPushProvider()
        
        self.providers["websocket"] = self.websocket_provider
        self.providers["email"] = self.email_provider
        self.providers["sms"] = self.sms_provider
    
    def configure_email(self, sender_email: str, sender_password: str):
        """配置邮件服务"""
        self.email_provider.configure(sender_email, sender_password)
    
    def configure_sms(self, api_key: str, api_secret: str):
        """配置短信服务"""
        self.sms_provider.configure(api_key, api_secret)
    
    def add_recipient_info(self, user_id: str, info: Dict[str, Any]):
        """添加收件人信息"""
        self.recipient_info[user_id] = info
    
    def get_recipient_info(self, user_id: str) -> Dict[str, Any]:
        """获取收件人信息"""
        return self.recipient_info.get(user_id, {})
    
    async def send_notification(self, notification: RiskNotification, push_methods: List[str] = None) -> Dict[str, bool]:
        """发送通知到多个渠道"""
        if push_methods is None:
            push_methods = ["websocket"]  # 默认只使用WebSocket
        
        results = {}
        child_user_id = notification.child_user_id
        recipient_info = self.get_recipient_info(child_user_id)
        
        for method in push_methods:
            if method in self.providers:
                provider = self.providers[method]
                try:
                    success = await provider.send_notification(notification, recipient_info)
                    results[method] = success
                    logger.info(f"{method}推送{'成功' if success else '失败'}")
                except Exception as e:
                    logger.error(f"{method}推送异常: {e}")
                    results[method] = False
            else:
                logger.warning(f"未知的推送方式: {method}")
                results[method] = False
        
        return results
    
    def add_websocket_client(self, user_id: str, websocket):
        """添加WebSocket客户端"""
        self.websocket_provider.add_client(user_id, websocket)
    
    def remove_websocket_client(self, user_id: str):
        """移除WebSocket客户端"""
        self.websocket_provider.remove_client(user_id)

# 全局推送服务实例
push_service = PushService() 