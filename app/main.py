from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from .api.detection_routes import router as detection_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    logger.info("启动内容检测服务...")
    
    # 检查必要的环境变量
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("未设置OPENAI_API_KEY环境变量，某些功能可能无法正常工作")
    
    yield
    
    # 关闭时的清理
    logger.info("关闭内容检测服务...")


# 创建FastAPI应用
app = FastAPI(
    title="内容检测服务",
    description="""
    面向老年人的内容安全检测服务，提供以下功能：
    
    ## 主要功能
    
    * **虚假信息检测** - 检测短视频和文章中的虚假信息和诈骗内容
    * **毒性内容检测** - 识别有害、毒性或不当内容
    * **隐私泄露检测** - 检测可能泄露个人隐私的信息
    * **综合检测** - 同时进行上述三种检测并提供风险评估
    
    ## 技术特点
    
    * 基于大语言模型的智能分析
    * 结合传统机器学习和深度学习技术
    * 支持中文内容检测
    * 提供详细的检测报告和建议
    """,
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(detection_router)


@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "内容检测服务",
        "version": "1.0.0",
        "description": "面向老年人的内容安全检测服务",
        "endpoints": {
            "docs": "/docs",
            "health": "/api/detection/health",
            "fake_news_url": "/api/detection/fake-news/url",
            "fake_news_text": "/api/detection/fake-news/text",
            "toxic_content": "/api/detection/toxic-content",
            "privacy_leak": "/api/detection/privacy-leak",
            "comprehensive": "/api/detection/comprehensive"
        }
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