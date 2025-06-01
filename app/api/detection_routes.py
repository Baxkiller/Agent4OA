from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import logging
from ..services.detection_manager import get_detection_manager, DetectionManager
from ..data_models.detection_result import (
    FakeNewsDetectionResult,
    ToxicContentDetectionResult, 
    PrivacyLeakDetectionResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/detection", tags=["content-detection"])


# 请求模型
class URLDetectionRequest(BaseModel):
    """URL检测请求"""
    url: HttpUrl
    user_id: Optional[str] = None


class TextDetectionRequest(BaseModel):
    """文本检测请求"""
    content: str
    user_id: Optional[str] = None


class ComprehensiveDetectionRequest(BaseModel):
    """综合检测请求"""
    content: str
    user_id: Optional[str] = None


# 响应模型
class DetectionResponse(BaseModel):
    """检测响应基类"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/fake-news/url", response_model=DetectionResponse)
async def detect_fake_news_from_url(
    request: URLDetectionRequest,
    detection_manager: DetectionManager = Depends(get_detection_manager)
):
    """
    从URL检测虚假信息/诈骗
    
    - **url**: 要检测的链接（短视频链接或文章链接）
    - **user_id**: 可选的用户ID
    
    返回检测结果，包括是否为虚假信息、置信度、理由和证据等。
    """
    try:
        result = await detection_manager.detect_fake_news_from_url(
            str(request.url), 
            request.user_id
        )
        
        return DetectionResponse(
            success=True,
            message="虚假信息检测完成",
            data=result.dict()
        )
        
    except Exception as e:
        logger.error(f"URL虚假信息检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/fake-news/text", response_model=DetectionResponse)
async def detect_fake_news_from_text(
    request: TextDetectionRequest,
    detection_manager: DetectionManager = Depends(get_detection_manager)
):
    """
    从文本内容检测虚假信息/诈骗
    
    - **content**: 要检测的文本内容
    - **user_id**: 可选的用户ID
    
    返回检测结果，包括是否为虚假信息、置信度、理由和证据等。
    """
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        result = await detection_manager.detect_fake_news_from_text(
            request.content, 
            request.user_id
        )
        
        return DetectionResponse(
            success=True,
            message="虚假信息检测完成",
            data=result.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本虚假信息检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/toxic-content", response_model=DetectionResponse)
async def detect_toxic_content(
    request: TextDetectionRequest,
    detection_manager: DetectionManager = Depends(get_detection_manager)
):
    """
    检测毒性内容
    
    - **content**: 要检测的文本内容
    - **user_id**: 可选的用户ID
    
    返回检测结果，包括是否为毒性内容、各类毒性分数、严重程度等。
    """
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        result = await detection_manager.detect_toxic_content(
            request.content, 
            request.user_id
        )
        
        return DetectionResponse(
            success=True,
            message="毒性内容检测完成",
            data=result.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"毒性内容检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/privacy-leak", response_model=DetectionResponse)
async def detect_privacy_leak(
    request: TextDetectionRequest,
    detection_manager: DetectionManager = Depends(get_detection_manager)
):
    """
    检测隐私泄露
    
    - **content**: 要检测的文本内容
    - **user_id**: 可选的用户ID
    
    返回检测结果，包括是否存在隐私泄露、隐私类型、敏感实体、风险等级等。
    """
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        result = await detection_manager.detect_privacy_leak(
            request.content, 
            request.user_id
        )
        
        return DetectionResponse(
            success=True,
            message="隐私泄露检测完成",
            data=result.dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"隐私泄露检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/comprehensive", response_model=DetectionResponse)
async def comprehensive_detection(
    request: ComprehensiveDetectionRequest,
    detection_manager: DetectionManager = Depends(get_detection_manager)
):
    """
    综合检测：同时进行虚假信息、毒性内容和隐私泄露检测
    
    - **content**: 要检测的文本内容
    - **user_id**: 可选的用户ID
    
    返回所有检测结果和综合风险评估。
    """
    try:
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        result = await detection_manager.comprehensive_detection(
            request.content, 
            request.user_id
        )
        
        return DetectionResponse(
            success=True,
            message="综合检测完成",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"综合检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "检测服务运行正常"} 