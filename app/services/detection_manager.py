import asyncio
import os
from typing import Optional, Dict, Any
import logging
from .fake_news_detector import FakeNewsDetector
from .toxic_content_detector import ToxicContentDetector
from .privacy_leak_detector import PrivacyLeakDetector
from ..data_models.detection_result import (
    DetectionResult, 
    FakeNewsDetectionResult, 
    ToxicContentDetectionResult, 
    PrivacyLeakDetectionResult
)

logger = logging.getLogger(__name__)


class DetectionManager:
    """检测服务管理器"""
    
    def __init__(self, openai_api_key: Optional[str] = None, model_name: str = "qwen-vl-max-2025-04-08"):
        # 从环境变量获取API密钥
        if not openai_api_key:
            openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            raise ValueError("需要提供API密钥")
        
        # 初始化各个检测器
        self.fake_news_detector = FakeNewsDetector(openai_api_key, model_name)
        self.toxic_content_detector = ToxicContentDetector(openai_api_key, model_name)
        self.privacy_leak_detector = PrivacyLeakDetector(openai_api_key, model_name)
        
        logger.info("检测服务管理器初始化完成")
    
    async def detect_fake_news_from_url(self, content_url: str, user_id: Optional[str] = None) -> FakeNewsDetectionResult:
        """从URL检测虚假信息"""
        try:
            return await self.fake_news_detector.detect_fake_news_from_url(content_url, user_id)
        except Exception as e:
            logger.error(f"虚假信息检测失败: {e}")
            raise
    
    async def detect_fake_news_from_text(self, content_text: str, user_id: Optional[str] = None) -> FakeNewsDetectionResult:
        """从文本检测虚假信息"""
        try:
            return await self.fake_news_detector.detect_fake_news_from_text(content_text, user_id)
        except Exception as e:
            logger.error(f"文本虚假信息检测失败: {e}")
            raise
    
    async def detect_toxic_content(self, content: str, user_id: Optional[str] = None) -> ToxicContentDetectionResult:
        """检测毒性内容"""
        try:
            return await self.toxic_content_detector.detect_toxic_content(content, user_id)
        except Exception as e:
            logger.error(f"毒性内容检测失败: {e}")
            raise
    
    async def detect_privacy_leak(self, content: str, user_id: Optional[str] = None) -> PrivacyLeakDetectionResult:
        """检测隐私泄露"""
        try:
            return await self.privacy_leak_detector.detect_privacy_leak(content, user_id)
        except Exception as e:
            logger.error(f"隐私泄露检测失败: {e}")
            raise
    
    async def comprehensive_detection(self, content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """综合检测：同时进行虚假信息、毒性内容和隐私泄露检测"""
        try:
            # 并行执行三种检测
            tasks = [
                self.detect_fake_news_from_text(content, user_id),
                self.detect_toxic_content(content, user_id),
                self.detect_privacy_leak(content, user_id)
            ]
            
            fake_news_result, toxic_result, privacy_result = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            results = {
                "fake_news": fake_news_result if not isinstance(fake_news_result, Exception) else None,
                "toxic_content": toxic_result if not isinstance(toxic_result, Exception) else None,
                "privacy_leak": privacy_result if not isinstance(privacy_result, Exception) else None,
                "errors": []
            }
            
            # 记录错误
            if isinstance(fake_news_result, Exception):
                results["errors"].append(f"虚假信息检测失败: {str(fake_news_result)}")
            if isinstance(toxic_result, Exception):
                results["errors"].append(f"毒性内容检测失败: {str(toxic_result)}")
            if isinstance(privacy_result, Exception):
                results["errors"].append(f"隐私泄露检测失败: {str(privacy_result)}")
            
            # 生成综合风险评估
            results["risk_assessment"] = self._generate_risk_assessment(results)
            
            return results
            
        except Exception as e:
            logger.error(f"综合检测失败: {e}")
            raise
    
    def _generate_risk_assessment(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合风险评估"""
        risk_assessment = {
            "overall_risk_level": "low",
            "detected_issues": [],
            "recommendations": [],
            "confidence_scores": {}
        }
        
        # 检查各项检测结果
        if results.get("fake_news") and results["fake_news"].is_detected:
            risk_assessment["detected_issues"].append("虚假信息")
            risk_assessment["confidence_scores"]["fake_news"] = results["fake_news"].confidence_score
            risk_assessment["recommendations"].extend(results["fake_news"].evidence)
        
        if results.get("toxic_content") and results["toxic_content"].is_detected:
            risk_assessment["detected_issues"].append("毒性内容")
            risk_assessment["confidence_scores"]["toxic_content"] = results["toxic_content"].confidence_score
            if results["toxic_content"].severity_level == "high":
                risk_assessment["overall_risk_level"] = "high"
            elif results["toxic_content"].severity_level == "medium" and risk_assessment["overall_risk_level"] == "low":
                risk_assessment["overall_risk_level"] = "medium"
        
        if results.get("privacy_leak") and results["privacy_leak"].is_detected:
            risk_assessment["detected_issues"].append("隐私泄露")
            risk_assessment["confidence_scores"]["privacy_leak"] = results["privacy_leak"].confidence_score
            if results["privacy_leak"].risk_level == "high":
                risk_assessment["overall_risk_level"] = "high"
            elif results["privacy_leak"].risk_level == "medium" and risk_assessment["overall_risk_level"] == "low":
                risk_assessment["overall_risk_level"] = "medium"
        
        # 生成建议
        if len(risk_assessment["detected_issues"]) == 0:
            risk_assessment["recommendations"].append("内容未检测到明显风险")
        else:
            risk_assessment["recommendations"].append(f"检测到以下问题：{', '.join(risk_assessment['detected_issues'])}")
            risk_assessment["recommendations"].append("建议谨慎处理相关内容")
        
        return risk_assessment


# 全局检测管理器实例
detection_manager = None

def get_detection_manager() -> DetectionManager:
    """获取检测管理器实例"""
    global detection_manager
    if detection_manager is None:
        detection_manager = DetectionManager()
    return detection_manager 