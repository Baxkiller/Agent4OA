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


class ToxicContentDetectionResult(DetectionResult):
    """毒性内容检测结果"""
    detection_type: str = "toxic_content"
    toxicity_categories: Optional[Dict[str, float]] = None  # 各类毒性分数
    severity_level: Optional[str] = None  # "low", "medium", "high"


class PrivacyLeakDetectionResult(DetectionResult):
    """隐私泄露检测结果"""
    detection_type: str = "privacy_leak"
    privacy_types: Optional[List[str]] = None  # 隐私类型列表
    sensitive_entities: Optional[List[Dict[str, Any]]] = None  # 敏感实体信息
    risk_level: Optional[str] = None  # "low", "medium", "high" 