from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class UserRelationship(BaseModel):
    """用户关系数据模型"""
    relationship_id: str
    elder_user_id: str  # 老年人用户ID
    child_user_id: str  # 子女用户ID
    relationship_type: str = "parent_child"  # 关系类型
    created_at: datetime = datetime.now()
    is_active: bool = True  # 关系是否有效
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserRelationshipManager:
    """用户关系管理器"""
    def __init__(self):
        # 模拟关系数据，实际应存储在数据库中
        self.relationships = [
            UserRelationship(
                relationship_id="rel_001",
                elder_user_id="elder_001",
                child_user_id="child_001"
            ),
            UserRelationship(
                relationship_id="rel_002", 
                elder_user_id="elder_002",
                child_user_id="child_002"
            )
        ]
    
    def get_child_user_id(self, elder_user_id: str) -> Optional[str]:
        """根据老年人ID获取子女ID"""
        for rel in self.relationships:
            if rel.elder_user_id == elder_user_id and rel.is_active:
                return rel.child_user_id
        return None
    
    def get_elder_user_id(self, child_user_id: str) -> Optional[str]:
        """根据子女ID获取老年人ID"""
        for rel in self.relationships:
            if rel.child_user_id == child_user_id and rel.is_active:
                return rel.elder_user_id
        return None
    
    def get_all_children(self, elder_user_id: str) -> List[str]:
        """获取老年人的所有子女ID"""
        children = []
        for rel in self.relationships:
            if rel.elder_user_id == elder_user_id and rel.is_active:
                children.append(rel.child_user_id)
        return children 