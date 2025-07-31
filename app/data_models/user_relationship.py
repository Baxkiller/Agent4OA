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

from app.database.repositories import relationship_repo

class UserRelationshipManager:
    """用户关系管理器"""
    def __init__(self):
        # 初始化时加载一些示例数据（如果数据库为空）
        self._init_sample_data()
    
    def _init_sample_data(self):
        """初始化示例数据"""
        try:
            # 检查是否已有数据
            existing_relationships = relationship_repo.get_all_relationships()
            if not existing_relationships:
                # 添加示例数据
                sample_relationships = [
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
                
                for rel in sample_relationships:
                    relationship_repo.add_relationship(rel)
                print("示例用户关系数据已初始化")
        except Exception as e:
            print(f"初始化示例数据失败: {e}")
    
    def get_child_user_id(self, elder_user_id: str) -> Optional[str]:
        """根据老年人ID获取子女ID"""
        return relationship_repo.get_child_user_id(elder_user_id)
    
    def get_elder_user_id(self, child_user_id: str) -> Optional[str]:
        """根据子女ID获取老年人ID"""
        return relationship_repo.get_elder_user_id(child_user_id)
    
    def get_all_children(self, elder_user_id: str) -> List[str]:
        """获取老年人的所有子女ID"""
        return relationship_repo.get_all_children(elder_user_id)
    
    def add_relationship(self, relationship: UserRelationship) -> bool:
        """添加用户关系"""
        return relationship_repo.add_relationship(relationship)
    
    def deactivate_relationship(self, elder_user_id: str, child_user_id: str) -> bool:
        """停用用户关系"""
        return relationship_repo.deactivate_relationship(elder_user_id, child_user_id) 