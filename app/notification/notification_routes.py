from fastapi import APIRouter, Query
from typing import List, Optional
from app.data_models import RiskNotification
from app.data_models.user_relationship import UserRelationshipManager
from app.notification.notification_store import (
    get_notifications, 
    get_notifications_by_child as get_notifications_by_child_id,
    update_notification_status,
    delete_notification
)

router = APIRouter()

# 使用独立的通知存储模块

# 用户关系管理器
relationship_manager = UserRelationshipManager()

@router.get("/notifications", response_model=List[RiskNotification])
def get_all_notifications():
    """获取所有风险通知（测试用）"""
    return get_notifications()

@router.get("/notifications/by_child", response_model=List[RiskNotification])
def get_notifications_by_child(child_user_id: str = Query(..., description="子女用户ID")):
    """根据子女ID获取风险通知"""
    return get_notifications_by_child_id(child_user_id)

@router.get("/relationship/child")
def get_child_user_id(elder_user_id: str = Query(..., description="老年人用户ID")):
    """根据老年人ID获取子女ID"""
    child_id = relationship_manager.get_child_user_id(elder_user_id)
    return {
        "elder_user_id": elder_user_id,
        "child_user_id": child_id,
        "found": child_id is not None
    }

@router.get("/relationship/elder")
def get_elder_user_id(child_user_id: str = Query(..., description="子女用户ID")):
    """根据子女ID获取老年人ID"""
    elder_id = relationship_manager.get_elder_user_id(child_user_id)
    return {
        "child_user_id": child_user_id,
        "elder_user_id": elder_id,
        "found": elder_id is not None
    }

@router.put("/notifications/{notification_id}/status")
def update_notification_status_route(notification_id: str, status: str):
    """更新通知状态"""
    success = update_notification_status(notification_id, status)
    return {
        "success": success,
        "message": "状态更新成功" if success else "状态更新失败",
        "notification_id": notification_id,
        "new_status": status
    }

@router.delete("/notifications/{notification_id}")
def delete_notification_route(notification_id: str):
    """删除通知"""
    success = delete_notification(notification_id)
    return {
        "success": success,
        "message": "通知删除成功" if success else "通知删除失败",
        "notification_id": notification_id
    }

@router.get("/relationships")
def get_all_relationships():
    """获取所有用户关系"""
    relationships = relationship_manager.get_all_relationships()
    return {
        "success": True,
        "relationships": [rel.dict() for rel in relationships],
        "count": len(relationships)
    }

@router.post("/relationships")
def add_relationship(relationship: dict):
    """添加用户关系"""
    try:
        from app.data_models.user_relationship import UserRelationship
        new_relationship = UserRelationship(**relationship)
        success = relationship_manager.add_relationship(new_relationship)
        return {
            "success": success,
            "message": "关系添加成功" if success else "关系添加失败",
            "relationship": new_relationship.dict()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"关系添加失败: {str(e)}"
        } 