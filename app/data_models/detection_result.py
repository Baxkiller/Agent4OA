from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class DetectionResult(BaseModel):
    """检测结果数据模型"""
    result_id: str
    detection_type: str  # "fake_news", "toxic_content", "privacy_leak"
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    is_detected: bool
    confidence_score: float
    reasons: List[str] = []
    evidence: List[str] = []
    created_at: datetime = datetime.now()
    user_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FakeNewsDetectionResult(DetectionResult):
    """虚假信息检测结果"""
    detection_type: str = "fake_news"
    video_frames: Optional[List[str]] = None  # 视频帧路径
    audio_transcript: Optional[str] = None  # 音频转文字结果
    fact_check_sources: Optional[List[str]] = None  # 事实核查来源
    
    # 新增面向老年人的字段
    is_fake_for_elderly: Optional[bool] = None  # 对老年人是否为虚假信息
    fake_aspects: Optional[List[str]] = None  # 虚假的方面
    false_claims: Optional[List[str]] = None  # 虚假声称
    factual_version: Optional[str] = None  # 真实信息版本
    truth_explanation: Optional[str] = None  # 真相解释
    safety_tips: Optional[List[str]] = None  # 防骗提醒


class ToxicContentDetectionResult(DetectionResult):
    """毒性内容检测结果"""
    detection_type: str = "toxic_content"
    toxicity_categories: Optional[Dict[str, float]] = None  # 各类毒性分数
    severity_level: Optional[str] = None  # "轻微", "中等", "严重"
    
    # 新增面向老年人的字段
    is_toxic_for_elderly: Optional[bool] = None  # 对老年人是否有毒性
    toxicity_reasons: Optional[List[str]] = None  # 毒性原因
    toxic_elements: Optional[List[str]] = None  # 毒性元素
    detoxified_meaning: Optional[str] = None  # 去毒后的意思
    friendly_alternative: Optional[str] = None  # 友善的替代表达
    elderly_explanation: Optional[str] = None  # 面向老年人的解释


class PrivacyLeakDetectionResult(DetectionResult):
    """隐私泄露检测结果"""
    detection_type: str = "privacy_leak"
    privacy_types: Optional[List[str]] = None  # 隐私类型列表
    sensitive_entities: Optional[List[Dict[str, Any]]] = None  # 敏感实体信息
    risk_level: Optional[str] = None  # "low", "medium", "high" 
    
    # 为老年人设计的新字段
    has_privacy_risk: Optional[bool] = None  # 是否存在隐私风险
    privacy_risks: Optional[List[str]] = None  # 隐私风险类型列表
    risky_information: Optional[List[Dict[str, Any]]] = None  # 有风险的信息详情
    safe_version: Optional[str] = None  # 安全的替代版本
    elderly_explanation: Optional[str] = None  # 给老年人的通俗解释
    protection_tips: Optional[List[str]] = None  # 隐私保护建议
    suggested_changes: Optional[List[Dict[str, Any]]] = None  # 具体修改建议 