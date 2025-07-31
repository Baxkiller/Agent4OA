from fastapi import APIRouter, Query
from typing import List, Optional
from app.data_models import RiskNotification
from app.data_models.user_relationship import UserRelationshipManager

router = APIRouter()

# 模拟内存存储，后续可替换为数据库
risk_notifications: List[RiskNotification] = []

# 用户关系管理器
relationship_manager = UserRelationshipManager()

@router.get("/notifications", response_model=List[RiskNotification])
def get_all_notifications():
    """获取所有风险通知（测试用）"""
    return risk_notifications

@router.get("/notifications/by_child", response_model=List[RiskNotification])
def get_notifications_by_child(child_user_id: str = Query(..., description="子女用户ID")):
    """根据子女ID获取风险通知"""
    return [n for n in risk_notifications if n.child_user_id == child_user_id]

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

# 可扩展更多接口，如标记已读、删除等 