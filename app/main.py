from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import os
import re
import json
from contextlib import asynccontextmanager

# 导入服务
try:
    # 相对导入（当作为包使用时）
    from .services.tools import parse_url_from_text, extract_urls_from_text
    from .services.content_crawler import ContentCrawler
    from .services.toxic_content_detector import ToxicContentDetector
    from .services.fake_news_detector import FakeNewsDetector
    from .services.privacy_leak_detector import PrivacyLeakDetector
except ImportError:
    # 绝对导入（当直接运行时）
    import sys
    import os
    # 添加项目根目录到Python路径
    current_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    
    from app.services.tools import parse_url_from_text, extract_urls_from_text
    from app.services.content_crawler import ContentCrawler
    from app.services.toxic_content_detector import ToxicContentDetector
    from app.services.fake_news_detector import FakeNewsDetector
    from app.services.privacy_leak_detector import PrivacyLeakDetector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentDetectionRequest(BaseModel):
    """通用内容检测请求模型"""
    content: str
    user_id: Optional[str] = None


class FakeNewsDetectionRequest(BaseModel):
    """虚假信息检测请求模型"""
    content: str
    user_id: Optional[str] = None


class ToxicContentDetectionRequest(BaseModel):
    """毒性内容检测请求模型"""
    content: str
    user_id: Optional[str] = None


class PrivacyLeakDetectionRequest(BaseModel):
    """隐私泄露检测请求模型"""
    content: str
    user_id: Optional[str] = None


class ContentDetectionResponse(BaseModel):
    """内容检测响应模型"""
    success: bool
    message: str
    data: Dict[str, Any]
    video_id: Optional[str] = None  # 如果是视频内容，返回视频ID
    cached: bool = False  # 是否使用了缓存


class UnifiedContentDetector:
    """统一内容检测服务"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.crawler = ContentCrawler()
        
        # 初始化各种检测器
        self.toxic_detector = ToxicContentDetector(openai_api_key)
        self.fake_news_detector = FakeNewsDetector(openai_api_key)
        self.privacy_detector = PrivacyLeakDetector(openai_api_key)
        
        # 结果缓存 - 基于视频ID
        self.result_cache = {}
        
        logger.info("统一内容检测服务初始化完成")
    
    def extract_video_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        # 从分享链接中提取视频ID
        patterns = [
            r'/video/(\d+)',
            r'/share/video/(\d+)',
            r'video_id=(\d+)',
            r'aweme_id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def check_cache_for_detection(self, video_id: str, detection_type: str) -> Optional[Dict[str, Any]]:
        """检查特定检测类型的缓存"""
        cache_key = f"{video_id}_{detection_type}"
        return self.result_cache.get(cache_key)
    
    def save_detection_to_cache(self, video_id: str, detection_type: str, result: Dict[str, Any]):
        """保存检测结果到缓存"""
        cache_key = f"{video_id}_{detection_type}"
        self.result_cache[cache_key] = result
        
        # 同时保存到文件缓存
        try:
            cache_dir = os.path.join("cache", video_id)
            os.makedirs(cache_dir, exist_ok=True)
            
            cache_file = os.path.join(cache_dir, f"{detection_type}_result.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"检测结果已缓存: {cache_key}")
        except Exception as e:
            logger.error(f"保存检测结果缓存失败: {e}")
    
    def load_detection_from_file_cache(self, video_id: str, detection_type: str) -> Optional[Dict[str, Any]]:
        """从文件缓存加载检测结果"""
        try:
            cache_file = os.path.join("cache", video_id, f"{detection_type}_result.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    
                # 加载到内存缓存
                cache_key = f"{video_id}_{detection_type}"
                self.result_cache[cache_key] = result
                
                logger.info(f"从文件缓存加载检测结果: {cache_key}")
                return result
        except Exception as e:
            logger.error(f"加载文件缓存失败: {e}")
        
        return None
    
    async def process_content(self, content: str, detection_type: str, user_id: Optional[str] = None) -> ContentDetectionResponse:
        """统一内容处理流程"""
        try:
            video_id = None
            cached = False
            
            # 步骤1: 检查是否包含抖音URL
            douyin_url = None
            urls = extract_urls_from_text(content)
            
            for url in urls:
                if 'douyin.com' in url or 'iesdouyin.com' in url:
                    # 解析抖音URL
                    douyin_url = parse_url_from_text(content)
                    video_id = self.extract_video_id_from_url(douyin_url)
                    logger.info(f"检测到抖音视频: {video_id}")
                    break
            
            # 步骤2: 检查缓存
            if video_id:
                # 先检查内存缓存
                cached_result = self.check_cache_for_detection(video_id, detection_type)
                
                # 如果内存缓存没有，检查文件缓存
                if not cached_result:
                    cached_result = self.load_detection_from_file_cache(video_id, detection_type)
                
                if cached_result:
                    logger.info(f"使用缓存结果: {video_id}_{detection_type}")
                    return ContentDetectionResponse(
                        success=True,
                        message="检测完成（缓存）",
                        data=cached_result,
                        video_id=video_id,
                        cached=True
                    )
            
            # 步骤3: 获取内容
            final_content = content
            images = []
            
            if douyin_url and video_id:
                # 使用crawler获取视频内容
                logger.info(f"开始爬取视频内容: {douyin_url}")
                crawler_result = self.crawler.process_douyin_content(douyin_url)
                
                if crawler_result.get("success", False):
                    # 优先使用转录文本，如果没有则使用标题
                    final_content = crawler_result.get("transcript", "")
                    if not final_content.strip():
                        final_content = crawler_result.get("video_info", {}).get("title", "")
                    
                    # 获取视频帧作为图像
                    images = crawler_result.get("frames", [])
                    
                    logger.info(f"爬取成功，文本长度: {len(final_content)}, 图像数量: {len(images)}")
                else:
                    logger.warning(f"爬取失败，使用原始文本: {crawler_result.get('error', '未知错误')}")
            
            # 步骤4: 执行检测
            detection_result = None
            
            if detection_type == "toxic":
                result = await self.toxic_detector.detect_toxic_content(
                    final_content, user_id, images
                )
                detection_result = {
                    "is_toxic_for_elderly": result.is_detected,
                    "toxicity_reasons": result.toxicity_reasons or [],
                    "friendly_alternative": result.friendly_alternative or ""
                }
                
            elif detection_type == "fake_news":
                result = await self.fake_news_detector.detect_fake_news(
                    final_content, user_id, images
                )
                detection_result = {
                    "is_fake_for_elderly": result.is_detected,
                    "fake_aspects": result.fake_aspects or [],
                    "factual_version": result.factual_version or "",
                    "truth_explanation": result.truth_explanation or ""
                }
                
            elif detection_type == "privacy":
                result = await self.privacy_detector.detect_privacy_leak(
                    final_content, user_id, images
                )
                detection_result = {
                    "has_privacy_risk": result.is_detected,
                    "risky_information": result.risky_information or [],
                    "safe_version": result.safe_version or ""
                }
            else:
                raise HTTPException(status_code=400, detail=f"不支持的检测类型: {detection_type}")
            
            # 步骤5: 缓存结果（仅对视频内容）
            if video_id and detection_result:
                self.save_detection_to_cache(video_id, detection_type, detection_result)
            
            return ContentDetectionResponse(
                success=True,
                message="检测完成",
                data=detection_result,
                video_id=video_id,
                cached=False
            )
            
        except Exception as e:
            logger.error(f"内容检测失败: {e}", exc_info=True)
            return ContentDetectionResponse(
                success=False,
                message=f"检测失败: {str(e)}",
                data={},
                video_id=video_id,
                cached=False
            )


# 全局检测器实例
detector: Optional[UnifiedContentDetector] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global detector
    
    # 启动时的初始化
    logger.info("启动内容检测服务...")
    
    # 检查必要的环境变量
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("未设置OPENAI_API_KEY环境变量")
        raise RuntimeError("需要设置OPENAI_API_KEY环境变量")
    
    # 初始化统一检测器
    detector = UnifiedContentDetector(openai_api_key)
    
    yield
    
    # 关闭时的清理
    logger.info("关闭内容检测服务...")


# 创建FastAPI应用
app = FastAPI(
    title="老年人内容安全检测服务",
    description="""
    面向老年人的内容安全检测服务，提供统一的检测接口：
    
    ## 主要功能
    
    * **毒性内容检测** - 识别有害、攻击性或不当内容，提供友好替代版本
    * **虚假信息检测** - 检测谣言和虚假信息，提供真实信息版本
    * **隐私泄露检测** - 检测隐私风险，提供安全发送建议
    
    ## 技术特点
    
    * 支持文本和抖音视频链接
    * 自动解析抖音URL并提取内容
    * 智能缓存机制，避免重复处理
    * 老年人友好的检测结果
    """,
    version="2.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "老年人内容安全检测服务",
        "version": "2.0.0",
        "description": "支持文本和视频的统一内容检测",
        "endpoints": {
            "docs": "/docs",
            "detect_toxic": "/detect/toxic",
            "detect_fake_news": "/detect/fake_news", 
            "detect_privacy": "/detect/privacy",
            "cache_status": "/cache/status"
        }
    }

@app.post("/detect/toxic", response_model=ContentDetectionResponse)
async def detect_toxic_content(request: ToxicContentDetectionRequest):
    """检测毒性内容"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    return await detector.process_content(
        content=request.content,
        detection_type="toxic",
        user_id=request.user_id
    )


@app.post("/detect/fake_news", response_model=ContentDetectionResponse)
async def detect_fake_news(request: FakeNewsDetectionRequest):
    """检测虚假信息"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    return await detector.process_content(
        content=request.content,
        detection_type="fake_news", 
        user_id=request.user_id
    )


@app.post("/detect/privacy", response_model=ContentDetectionResponse)
async def detect_privacy_leak(request: PrivacyLeakDetectionRequest):
    """检测隐私泄露"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    return await detector.process_content(
        content=request.content,
        detection_type="privacy",
        user_id=request.user_id
    )


@app.get("/cache/status")
async def get_cache_status():
    """获取缓存状态"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    cache_size = len(detector.result_cache)
    
    # 统计文件缓存
    file_cache_count = 0
    cache_dir = "cache"
    if os.path.exists(cache_dir):
        for item in os.listdir(cache_dir):
            item_path = os.path.join(cache_dir, item)
            if os.path.isdir(item_path):
                file_cache_count += 1
    
    return {
        "memory_cache_size": cache_size,
        "file_cache_videos": file_cache_count,
        "cache_keys": list(detector.result_cache.keys())
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务内部错误",
            "detail": "请稍后重试或联系管理员"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 