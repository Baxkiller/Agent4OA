from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from .database import db_manager
from app.data_models import RiskNotification
from app.data_models.user_relationship import UserRelationship

logger = logging.getLogger(__name__)

class NotificationRepository:
    """通知数据访问层"""
    
    def add_notification(self, notification: RiskNotification) -> bool:
        """添加通知"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO risk_notifications 
                    (notification_id, elder_user_id, child_user_id, content_type, 
                     risk_level, platform, suggestion, detected_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    notification.notification_id,
                    notification.elder_user_id,
                    notification.child_user_id,
                    notification.content_type,
                    notification.risk_level,
                    notification.platform,
                    notification.suggestion,
                    notification.detected_at.isoformat(),
                    notification.status
                ))
                conn.commit()
                logger.info(f"通知已保存到数据库: {notification.notification_id}")
                return True
        except Exception as e:
            logger.error(f"保存通知失败: {e}")
            return False
    
    def get_all_notifications(self) -> List[RiskNotification]:
        """获取所有通知"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM risk_notifications 
                    ORDER BY detected_at DESC
                ''')
                rows = cursor.fetchall()
                
                notifications = []
                for row in rows:
                    notification = RiskNotification(
                        notification_id=row['notification_id'],
                        elder_user_id=row['elder_user_id'],
                        child_user_id=row['child_user_id'],
                        content_type=row['content_type'],
                        risk_level=row['risk_level'],
                        platform=row['platform'],
                        suggestion=row['suggestion'],
                        detected_at=datetime.fromisoformat(row['detected_at']),
                        status=row['status']
                    )
                    notifications.append(notification)
                
                return notifications
        except Exception as e:
            logger.error(f"获取通知失败: {e}")
            return []
    
    def get_notifications_by_child(self, child_user_id: str) -> List[RiskNotification]:
        """根据子女ID获取通知"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM risk_notifications 
                    WHERE child_user_id = ?
                    ORDER BY detected_at DESC
                ''', (child_user_id,))
                rows = cursor.fetchall()
                
                notifications = []
                for row in rows:
                    notification = RiskNotification(
                        notification_id=row['notification_id'],
                        elder_user_id=row['elder_user_id'],
                        child_user_id=row['child_user_id'],
                        content_type=row['content_type'],
                        risk_level=row['risk_level'],
                        platform=row['platform'],
                        suggestion=row['suggestion'],
                        detected_at=datetime.fromisoformat(row['detected_at']),
                        status=row['status']
                    )
                    notifications.append(notification)
                
                return notifications
        except Exception as e:
            logger.error(f"获取子女通知失败: {e}")
            return []
    
    def update_notification_status(self, notification_id: str, status: str) -> bool:
        """更新通知状态"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE risk_notifications 
                    SET status = ? 
                    WHERE notification_id = ?
                ''', (status, notification_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新通知状态失败: {e}")
            return False
    
    def delete_notification(self, notification_id: str) -> bool:
        """删除通知"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM risk_notifications 
                    WHERE notification_id = ?
                ''', (notification_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除通知失败: {e}")
            return False

class UserRelationshipRepository:
    """用户关系数据访问层"""
    
    def add_relationship(self, relationship: UserRelationship) -> bool:
        """添加用户关系"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_relationships 
                    (relationship_id, elder_user_id, child_user_id, relationship_type, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    relationship.relationship_id,
                    relationship.elder_user_id,
                    relationship.child_user_id,
                    relationship.relationship_type,
                    relationship.is_active
                ))
                conn.commit()
                logger.info(f"用户关系已保存: {relationship.relationship_id}")
                return True
        except Exception as e:
            logger.error(f"保存用户关系失败: {e}")
            return False
    
    def get_child_user_id(self, elder_user_id: str) -> Optional[str]:
        """根据老年人ID获取子女ID"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT child_user_id FROM user_relationships 
                    WHERE elder_user_id = ? AND is_active = 1
                    LIMIT 1
                ''', (elder_user_id,))
                row = cursor.fetchone()
                return row['child_user_id'] if row else None
        except Exception as e:
            logger.error(f"获取子女ID失败: {e}")
            return None
    
    def get_elder_user_id(self, child_user_id: str) -> Optional[str]:
        """根据子女ID获取老年人ID"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT elder_user_id FROM user_relationships 
                    WHERE child_user_id = ? AND is_active = 1
                    LIMIT 1
                ''', (child_user_id,))
                row = cursor.fetchone()
                return row['elder_user_id'] if row else None
        except Exception as e:
            logger.error(f"获取老年人ID失败: {e}")
            return None
    
    def get_all_children(self, elder_user_id: str) -> List[str]:
        """获取老年人的所有子女ID"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT child_user_id FROM user_relationships 
                    WHERE elder_user_id = ? AND is_active = 1
                ''', (elder_user_id,))
                rows = cursor.fetchall()
                return [row['child_user_id'] for row in rows]
        except Exception as e:
            logger.error(f"获取所有子女ID失败: {e}")
            return []
    
    def deactivate_relationship(self, elder_user_id: str, child_user_id: str) -> bool:
        """停用用户关系"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_relationships 
                    SET is_active = 0 
                    WHERE elder_user_id = ? AND child_user_id = ?
                ''', (elder_user_id, child_user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"停用用户关系失败: {e}")
            return False
    
    def get_all_relationships(self) -> List[UserRelationship]:
        """获取所有用户关系"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM user_relationships 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                ''')
                rows = cursor.fetchall()
                
                relationships = []
                for row in rows:
                    relationship = UserRelationship(
                        relationship_id=row['relationship_id'],
                        elder_user_id=row['elder_user_id'],
                        child_user_id=row['child_user_id'],
                        relationship_type=row['relationship_type'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        is_active=bool(row['is_active'])
                    )
                    relationships.append(relationship)
                
                return relationships
        except Exception as e:
            logger.error(f"获取所有用户关系失败: {e}")
            return []

# 全局Repository实例
notification_repo = NotificationRepository()
relationship_repo = UserRelationshipRepository() 