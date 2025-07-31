from typing import List
from app.data_models import RiskNotification
from app.database.repositories import notification_repo

def add_notification(notification: RiskNotification):
    """添加通知到数据库"""
    notification_repo.add_notification(notification)

def get_notifications() -> List[RiskNotification]:
    """获取所有通知"""
    return notification_repo.get_all_notifications()

def get_notifications_by_child(child_user_id: str) -> List[RiskNotification]:
    """根据子女ID获取通知"""
    return notification_repo.get_notifications_by_child(child_user_id)

def update_notification_status(notification_id: str, status: str) -> bool:
    """更新通知状态"""
    return notification_repo.update_notification_status(notification_id, status)

def delete_notification(notification_id: str) -> bool:
    """删除通知"""
    return notification_repo.delete_notification(notification_id)

def clear_notifications():
    """清空通知（测试用）"""
    # 注意：这个方法在生产环境中应该谨慎使用
    # 这里仅用于测试目的
    pass 