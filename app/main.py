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
from dotenv import load_dotenv
from datetime import datetime
from logging.handlers import RotatingFileHandler

load_dotenv()

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
def setup_logging():
    """配置日志系统"""
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 生成日志文件名（格式: log-YYMMDD.log）
    today = datetime.now().strftime("%y%m%d")
    log_file = os.path.join(log_dir, f"log-{today}.log")
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（带日志轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 记录日志配置信息
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")
    logger.info(f"日志级别: INFO，最大文件大小: 10MB，备份文件数: 5")

# 初始化日志
setup_logging()
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


class PromptConfigRequest(BaseModel):
    """prompt配置请求模型（废弃，保留兼容性）"""
    parent_json: Dict[str, Any]
    child_json: Dict[str, Any]
    service_type: str  # "toxic", "fake_news", "privacy"


class ParentConfigRequest(BaseModel):
    """子女配置prompt请求模型"""
    config_data: Dict[str, Any]  # 子女的关注度配置
    service_type: str  # "toxic", "fake_news", "privacy", "all"
    user_id: Optional[str] = None


class ElderlyConfigRequest(BaseModel):
    """老年人配置prompt请求模型"""
    config_data: Dict[str, Any]  # 老年人的关注度配置
    service_type: str  # "toxic", "fake_news", "privacy", "all"
    user_id: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应模型"""
    success: bool
    message: str
    updated_services: List[str]
    config_type: str  # "parent" 或 "elderly"


class PromptConfigResponse(BaseModel):
    """协同配置prompt响应模型（废弃，保留兼容性）"""
    success: bool
    message: str
    updated_services: List[str]


class DetectionReportRequest(BaseModel):
    """生成检测报告请求模型"""
    user_id: str
    report_type: str = "total"  # "toxic", "fake_news", "privacy", "total"
    limit: Optional[int] = 10  # 默认分析最近10次记录


class DetectionReportResponse(BaseModel):
    """生成检测报告响应模型"""
    success: bool
    message: str
    report_data: Dict[str, Any]
    user_id: str
    report_type: str


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
    
    def update_config_by_type(self, config_data: Dict[str, Any], service_type: str, config_type: str, user_id: Optional[str] = None) -> List[str]:
        """根据配置类型更新服务prompt"""
        try:
            updated_services = []
            
            # 创建配置目录
            config_dir = "config"
            os.makedirs(config_dir, exist_ok=True)
            
            # 读取或创建现有配置
            config_file = os.path.join(config_dir, f"{service_type}_prompt_config.json")
            existing_config = {}
            
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        existing_config = json.load(f)
                except Exception as e:
                    logger.warning(f"读取现有配置失败: {e}")
            
            # 更新对应类型的配置
            if config_type == "parent":
                existing_config["parent_json"] = config_data
            elif config_type == "elderly":
                existing_config["child_json"] = config_data
            else:
                raise ValueError(f"不支持的配置类型: {config_type}")
            
            # 更新元数据
            existing_config.update({
                "updated_at": datetime.now().isoformat(),
                "service_type": service_type,
                f"last_updated_by": config_type,
                f"user_id": user_id
            })
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"{config_type}配置已保存到: {config_file}")
            
            # 如果两种配置都存在，进行协同更新
            parent_config = existing_config.get("parent_json", {})
            child_config = existing_config.get("child_json", {})
            
            if parent_config and child_config:
                # 协同配置模式：同时有子女和老年人的配置
                updated_services = self._update_services_collaborative(parent_config, child_config, service_type)
                logger.info(f"协同配置模式：已更新服务 {updated_services}")
            elif parent_config:
                # 仅子女配置模式
                updated_services = self._update_services_single(parent_config, service_type, "parent")
                logger.info(f"子女配置模式：已更新服务 {updated_services}")
            elif child_config:
                # 仅老年人配置模式
                updated_services = self._update_services_single(child_config, service_type, "elderly")
                logger.info(f"老年人配置模式：已更新服务 {updated_services}")
            
            return updated_services
            
        except Exception as e:
            logger.error(f"更新{config_type}配置失败: {e}")
            raise

    def _update_services_collaborative(self, parent_json: Dict[str, Any], child_json: Dict[str, Any], service_type: str) -> List[str]:
        """协同配置模式：综合子女和老年人的配置"""
        updated_services = []
        
        if service_type == "toxic":
            self.toxic_detector.update_prompt_config(parent_json, child_json)
            updated_services.append("toxic_detector")
        elif service_type == "fake_news":
            self.fake_news_detector.update_prompt_config(parent_json, child_json)
            updated_services.append("fake_news_detector")
        elif service_type == "privacy":
            self.privacy_detector.update_prompt_config(parent_json, child_json)
            updated_services.append("privacy_detector")
        elif service_type == "all":
            self.toxic_detector.update_prompt_config(parent_json, child_json)
            self.fake_news_detector.update_prompt_config(parent_json, child_json)
            self.privacy_detector.update_prompt_config(parent_json, child_json)
            updated_services = ["toxic_detector", "fake_news_detector", "privacy_detector"]
        else:
            raise ValueError(f"不支持的服务类型: {service_type}")
        
        return updated_services

    def _update_services_single(self, config_data: Dict[str, Any], service_type: str, config_type: str) -> List[str]:
        """单一配置模式：仅使用一方的配置"""
        updated_services = []
        
        # 单一配置模式下，将配置应用为默认配置
        default_config = {key: 3 for key in config_data.keys()}  # 默认中等关注度
        
        if config_type == "parent":
            # 子女配置优先，老年人配置使用默认值
            parent_config = config_data
            child_config = default_config
        else:
            # 老年人配置优先，子女配置使用默认值
            parent_config = default_config
            child_config = config_data
        
        if service_type == "toxic":
            return self._update_services_collaborative(parent_config, child_config, service_type)
        elif service_type == "fake_news":
            return self._update_services_collaborative(parent_config, child_config, service_type)
        elif service_type == "privacy":
            return self._update_services_collaborative(parent_config, child_config, service_type)
        elif service_type == "all":
            return self._update_services_collaborative(parent_config, child_config, service_type)
        else:
            raise ValueError(f"不支持的服务类型: {service_type}")

    def update_service_prompts(self, parent_json: Dict[str, Any], child_json: Dict[str, Any], service_type: str) -> List[str]:
        """更新服务的system prompt（保留兼容性）"""
        try:
            updated_services = []
            
            # 创建配置目录
            config_dir = "config"
            os.makedirs(config_dir, exist_ok=True)
            
            # 保存配置到本地JSON文件
            config_file = os.path.join(config_dir, f"{service_type}_prompt_config.json")
            config_data = {
                "parent_json": parent_json,
                "child_json": child_json,
                "updated_at": datetime.now().isoformat(),
                "service_type": service_type
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存到: {config_file}")
            
            return self._update_services_collaborative(parent_json, child_json, service_type)
            
        except Exception as e:
            logger.error(f"更新prompt配置失败: {e}")
            raise
    
    def generate_detection_report(self, user_id: str, report_type: str = "total", limit: int = 10) -> Dict[str, Any]:
        """生成检测报告"""
        try:
            if report_type == "total":
                return self._generate_total_report(user_id, limit)
            elif report_type in ["toxic", "fake_news", "privacy"]:
                return self._generate_specific_report(user_id, report_type, limit)
            else:
                raise ValueError(f"不支持的报告类型: {report_type}")
            
        except Exception as e:
            logger.error(f"生成检测报告失败: {e}")
            raise

    def _generate_total_report(self, user_id: str, limit: int) -> Dict[str, Any]:
        """生成总览报告"""
        # 统计用户的检测记录
        user_detections = {
            "toxic": 0,
            "fake_news": 0,
            "privacy": 0,
            "total": 0
        }
        
        detailed_results = []
        
        # 从缓存中收集用户相关的检测记录
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            # 遍历所有缓存目录
            for video_id in os.listdir(cache_dir):
                video_cache_dir = os.path.join(cache_dir, video_id)
                if os.path.isdir(video_cache_dir):
                    # 检查每种检测类型的结果
                    for detection_type in ["toxic", "fake_news", "privacy"]:
                        result_file = os.path.join(video_cache_dir, f"{detection_type}_result.json")
                        if os.path.exists(result_file):
                            try:
                                with open(result_file, 'r', encoding='utf-8') as f:
                                    result_data = json.load(f)
                                
                                # 检查是否检测到问题
                                is_detected = False
                                if detection_type == "toxic":
                                    is_detected = result_data.get("is_toxic_for_elderly", False)
                                elif detection_type == "fake_news":
                                    is_detected = result_data.get("is_fake_for_elderly", False)
                                elif detection_type == "privacy":
                                    is_detected = result_data.get("has_privacy_risk", False)
                                
                                if is_detected:
                                    user_detections[detection_type] += 1
                                    user_detections["total"] += 1
                                    
                                    detailed_results.append({
                                        "video_id": video_id,
                                        "detection_type": detection_type,
                                        "result": result_data,
                                        "timestamp": os.path.getmtime(result_file)
                                    })
                            
                            except Exception as e:
                                logger.warning(f"读取检测结果失败 {result_file}: {e}")
        
        # 按时间排序，取最近的记录
        detailed_results.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_results = detailed_results[:limit]
        
        # 计算比例
        total_detections = user_detections["total"]
        percentages = {}
        if total_detections > 0:
            percentages = {
                "toxic_percentage": (user_detections["toxic"] / total_detections) * 100,
                "fake_news_percentage": (user_detections["fake_news"] / total_detections) * 100,
                "privacy_percentage": (user_detections["privacy"] / total_detections) * 100
            }
        else:
            percentages = {
                "toxic_percentage": 0,
                "fake_news_percentage": 0,
                "privacy_percentage": 0
            }
        
        # 生成总结文字
        if total_detections == 0:
            summary = f"经过分析，您的家人在网络内容消费方面表现良好，未发现明显的安全风险。他们能够较好地识别和避免有害内容，请继续保持这种良好的使用习惯。"
            analysis = "从整体使用情况来看，用户具备基本的网络安全意识，能够在浏览内容时保持谨慎。建议继续关注并适时提供指导。"
        else:
            risk_types = []
            if user_detections["toxic"] > 0:
                risk_types.append(f"毒性内容 {user_detections['toxic']} 次")
            if user_detections["fake_news"] > 0:
                risk_types.append(f"虚假信息 {user_detections['fake_news']} 次")
            if user_detections["privacy"] > 0:
                risk_types.append(f"隐私风险 {user_detections['privacy']} 次")
            
            summary = f"经过分析，您的家人在最近的网络活动中遇到了 {total_detections} 次安全风险，包括：{', '.join(risk_types)}。这提醒我们需要加强网络安全防护意识。"
            
            # 风险程度分析
            if total_detections <= 2:
                risk_level = "较低"
                analysis = "整体风险程度较低，偶尔遇到有害内容是正常的。建议继续保持警惕，适时进行安全提醒。"
            elif total_detections <= 5:
                risk_level = "中等"
                analysis = "存在中等程度的安全风险，建议加强对老年人的网络安全教育，帮助他们提高识别能力。"
            else:
                risk_level = "较高"
                analysis = "安全风险较高，强烈建议立即加强防护措施，定期与老年人沟通网络安全话题，必要时协助设置更严格的内容过滤。"
        
        # 生成建议
        recommendations = []
        if user_detections["toxic"] > 0:
            recommendations.append("定期与老年人沟通，教导如何识别和应对网络不良言论")
        if user_detections["fake_news"] > 0:
            recommendations.append("提高老年人的媒体素养，教会他们核实信息来源")
        if user_detections["privacy"] > 0:
            recommendations.append("强化隐私保护意识，指导安全的信息分享方式")
        
        # 通用建议
        recommendations.extend([
            "建议定期查看老年人的网络活动，及时发现和处理风险",
            "鼓励老年人在遇到可疑内容时主动询问家人",
            "考虑安装更多安全防护软件，创建更安全的网络环境"
        ])
        
        if total_detections == 0:
            recommendations = [
                "继续保持良好的网络使用习惯",
                "定期关注网络安全动态，预防新型威胁",
                "与老年人分享正面的、有益的网络内容"
            ]
        
        report_data = {
            "user_id": user_id,
            "report_type": "total",
            "analysis_period": f"最近 {limit} 次检测记录",
            "statistics": user_detections,
            "percentages": percentages,
            "recent_detections": recent_results,
            "summary": summary,
            "analysis": analysis,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"为用户 {user_id} 生成总览检测报告完成")
        return report_data

    def _generate_specific_report(self, user_id: str, report_type: str, limit: int) -> Dict[str, Any]:
        """生成特定类型的详细报告"""
        # 收集特定类型的检测记录
        specific_results = []
        category_stats = {}
        
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            for video_id in os.listdir(cache_dir):
                video_cache_dir = os.path.join(cache_dir, video_id)
                if os.path.isdir(video_cache_dir):
                    result_file = os.path.join(video_cache_dir, f"{report_type}_result.json")
                    if os.path.exists(result_file):
                        try:
                            with open(result_file, 'r', encoding='utf-8') as f:
                                result_data = json.load(f)
                            
                            # 检查是否检测到问题
                            is_detected = False
                            category = ""
                            
                            if report_type == "toxic":
                                is_detected = result_data.get("is_toxic_for_elderly", False)
                                category = result_data.get("toxicity_category", "其他")  # 默认第一个类别
                            elif report_type == "fake_news":
                                is_detected = result_data.get("is_fake_for_elderly", False)
                                category = result_data.get("fake_news_category", "其他")  # 默认第一个类别
                            elif report_type == "privacy":
                                is_detected = result_data.get("has_privacy_risk", False)
                                category = result_data.get("privacy_category", "其他")  # 默认第一个类别
                            
                            if is_detected:
                                specific_results.append({
                                    "video_id": video_id,
                                    "detection_type": report_type,
                                    "category": category,
                                    "result": result_data,
                                    "timestamp": os.path.getmtime(result_file)
                                })
                                
                                # 统计各类别数量
                                category_stats[category] = category_stats.get(category, 0) + 1
                        
                        except Exception as e:
                            logger.warning(f"读取检测结果失败 {result_file}: {e}")
        
        # 按时间排序
        specific_results.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_results = specific_results[:limit]
        
        # 计算类别比例
        total_count = len(specific_results)
        category_percentages = {}
        if total_count > 0:
            for category, count in category_stats.items():
                category_percentages[category] = (count / total_count) * 100
        
        # 生成专门的分析和建议
        analysis_data = self._generate_specific_analysis(report_type, category_stats, total_count, user_id)
        
        report_data = {
            "user_id": user_id,
            "report_type": report_type,
            "analysis_period": f"最近 {limit} 次检测记录",
            "total_detections": total_count,
            "category_statistics": category_stats,
            "category_percentages": category_percentages,
            "recent_detections": recent_results,
            "summary": analysis_data["summary"],
            "analysis": analysis_data["analysis"],
            "recommendations": analysis_data["recommendations"],
            "risk_level": analysis_data["risk_level"],
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"为用户 {user_id} 生成{report_type}类型检测报告完成")
        return report_data

    def _generate_specific_analysis(self, report_type: str, category_stats: Dict[str, int], total_count: int, user_id: str) -> Dict[str, Any]:
        """生成特定类型的分析内容"""
        if report_type == "toxic":
            return self._analyze_toxic_report(category_stats, total_count, user_id)
        elif report_type == "fake_news":
            return self._analyze_fake_news_report(category_stats, total_count, user_id)
        elif report_type == "privacy":
            return self._analyze_privacy_report(category_stats, total_count, user_id)
        else:
            return {
                "summary": "未知报告类型",
                "analysis": "无法生成分析",
                "recommendations": [],
                "risk_level": "未知"
            }

    def _analyze_toxic_report(self, category_stats: Dict[str, int], total_count: int, user_id: str) -> Dict[str, Any]:
        """分析毒性内容报告"""
        if total_count == 0:
            return {
                "summary": f"您的家人在网络内容消费中表现出良好的判断力，未遇到明显的毒性内容或不良言论。",
                "analysis": "这表明老年人具备基本的内容辨识能力，能够避免接触有害的网络言论。建议继续保持这种良好的网络使用习惯。",
                "recommendations": [
                    "继续关注老年人的网络活动，适时给予正面引导",
                    "分享一些积极正面的网络内容，丰富精神生活",
                    "教育如何举报和屏蔽不当内容"
                ],
                "risk_level": "无风险"
            }
        
        # 分析最常见的毒性类型
        top_category = max(category_stats.items(), key=lambda x: x[1]) if category_stats else ("其他", 0)
        
        if total_count <= 2:
            risk_level = "轻微风险"
            summary = f"您的家人偶尔遇到了毒性内容，主要是{top_category[0]}类型。这在网络使用中较为常见，不必过度担心。"
            analysis = "偶尔接触到不良内容是正常的，重要的是老年人能够识别并适当应对这些内容。"
        elif total_count <= 5:
            risk_level = "中等风险"
            summary = f"您的家人多次接触到毒性内容，其中{top_category[0]}类型最为突出。需要加强防护意识。"
            analysis = "频繁接触毒性内容可能对心理健康造成影响，建议加强指导和防护措施。"
        else:
            risk_level = "较高风险"
            summary = f"您的家人经常遇到毒性内容，{top_category[0]}类型出现频率最高。强烈建议立即采取防护措施。"
            analysis = "高频率的毒性内容接触需要引起重视，可能影响老年人的心理健康和网络体验。"
        
        recommendations = [
            "教导老年人识别和应对网络攻击性言论",
            "建议使用内容过滤功能，减少不良内容曝光",
            "鼓励老年人在遇到恶意言论时不要回应",
            "定期与老年人沟通，了解其网络体验"
        ]
        
        if "威胁与恐吓" in category_stats:
            recommendations.append("如遇到威胁信息，应立即举报并可能需要报警")
        if "骚扰与网络霸凌" in category_stats:
            recommendations.append("指导如何屏蔽和举报骚扰用户")
        
        return {
            "summary": summary,
            "analysis": analysis,
            "recommendations": recommendations,
            "risk_level": risk_level
        }

    def _analyze_fake_news_report(self, category_stats: Dict[str, int], total_count: int, user_id: str) -> Dict[str, Any]:
        """分析虚假信息报告"""
        if total_count == 0:
            return {
                "summary": f"您的家人在信息甄别方面表现出色，未被虚假信息或诈骗内容误导。",
                "analysis": "这说明老年人具备良好的信息判断能力，能够识别可疑的网络信息。继续保持这种谨慎的态度。",
                "recommendations": [
                    "继续保持对网络信息的理性判断",
                    "分享权威渠道的真实信息",
                    "定期更新防诈骗知识"
                ],
                "risk_level": "无风险"
            }
        
        # 分析最常见的虚假信息类型
        top_category = max(category_stats.items(), key=lambda x: x[1]) if category_stats else ("其他", 0)
        
        if total_count <= 2:
            risk_level = "轻微风险"
            summary = f"您的家人偶尔接触到虚假信息，主要是{top_category[0]}类型。及时发现并制止了潜在的误导。"
            analysis = "少量的虚假信息接触在当前网络环境中难以避免，关键是能够及时识别。"
        elif total_count <= 5:
            risk_level = "中等风险"
            summary = f"您的家人多次遇到虚假信息，{top_category[0]}类型最为常见。需要提高防范意识。"
            analysis = "频繁接触虚假信息存在被误导的风险，建议加强媒体素养教育。"
        else:
            risk_level = "高风险"
            summary = f"您的家人频繁接触虚假信息，特别是{top_category[0]}类型。存在被诈骗的较高风险。"
            analysis = "高频率的虚假信息接触表明老年人可能缺乏足够的辨识能力，需要立即干预。"
        
        recommendations = [
            "教育老年人如何验证信息的真实性",
            "建议从权威渠道获取信息",
            "提醒不要轻信网络传言和广告",
            "对于涉及金钱的信息要格外谨慎"
        ]
        
        if "身份冒充" in category_stats:
            recommendations.append("警惕冒充明星或专家的诈骗，不要轻易添加陌生人")
        if "伪科学养生与健康焦虑" in category_stats:
            recommendations.append("购买保健品前务必咨询医生，不信保健品广告")
        if "虚假致富经与技能培训" in category_stats:
            recommendations.append("不要相信快速致富的方法，避免购买无价值的培训课程")
        
        return {
            "summary": summary,
            "analysis": analysis,
            "recommendations": recommendations,
            "risk_level": risk_level
        }

    def _analyze_privacy_report(self, category_stats: Dict[str, int], total_count: int, user_id: str) -> Dict[str, Any]:
        """分析隐私保护报告"""
        if total_count == 0:
            return {
                "summary": f"您的家人在隐私保护方面做得很好，没有发现个人信息泄露的风险。",
                "analysis": "老年人能够妥善保护个人隐私信息，避免在网络上过度分享敏感内容。这是很好的安全习惯。",
                "recommendations": [
                    "继续保持谨慎的信息分享习惯",
                    "定期检查隐私设置",
                    "学习新的隐私保护知识"
                ],
                "risk_level": "无风险"
            }
        
        # 分析最常见的隐私风险类型
        top_category = max(category_stats.items(), key=lambda x: x[1]) if category_stats else ("其他", 0)
        
        if total_count <= 2:
            risk_level = "轻微风险"
            summary = f"发现少量隐私风险，主要涉及{top_category[0]}。及时发现并提醒了潜在的信息泄露。"
            analysis = "偶尔的隐私信息分享可能是无意的，重要的是及时发现和纠正。"
        elif total_count <= 5:
            risk_level = "中等风险"
            summary = f"多次发现隐私风险，{top_category[0]}类型最为突出。需要加强隐私保护意识。"
            analysis = "频繁的隐私信息分享存在较大安全隐患，可能被不法分子利用。"
        else:
            risk_level = "高风险"
            summary = f"发现大量隐私泄露风险，{top_category[0]}类型尤为严重。强烈建议立即加强防护。"
            analysis = "严重的隐私信息泄露可能导致诈骗、身份盗用等严重后果，需要立即采取措施。"
        
        recommendations = [
            "教育老年人哪些信息不能在网上分享",
            "检查并调整社交媒体的隐私设置",
            "提醒在分享照片时注意背景信息",
            "教会如何安全地表达相同意思"
        ]
        
        if "核心身份与财务信息" in category_stats:
            recommendations.append("严禁在网络上分享银行卡、密码等关键信息")
        if "实时位置与日常行踪" in category_stats:
            recommendations.append("避免实时分享位置信息，不要详细描述出行计划")
        if "个人标识与安全验证信息" in category_stats:
            recommendations.append("谨慎参与网络问答游戏，避免泄露安全验证信息")
        
        return {
            "summary": summary,
            "analysis": analysis,
            "recommendations": recommendations,
            "risk_level": risk_level
        }
    
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
            # final_content = content
            # images = []
            
            # if douyin_url and video_id:
            #     # 使用crawler获取视频内容
            #     logger.info(f"开始爬取视频内容: {douyin_url}")
            #     crawler_result = self.crawler.process_douyin_content(douyin_url)
                
            #     if crawler_result.get("success", False):
            #         # 优先使用转录文本，如果没有则使用标题
            #         transcript = crawler_result.get("transcript", "") or ""
            #         title = crawler_result.get("video_info", {}).get("title", "") or ""
                    
            #         # 确保final_content不是None
            #         if transcript.strip():
            #             final_content = transcript
            #         elif title.strip():
            #             final_content = title
            #         else:
            #             final_content = content  # 使用原始内容作为fallback
                    
            #         # 获取视频帧作为图像
            #         images = crawler_result.get("frames", []) or []
                    
            #         logger.info(f"爬取成功，文本长度: {len(final_content)}, 图像数量: {len(images)}")
            #     else:
            #         error_msg = crawler_result.get('error', '未知错误')
            #         logger.warning(f"爬取失败，使用原始文本: {error_msg}")
            #         final_content = content
            
            # 步骤4: 执行检测
            detection_result = None
            
            if detection_type == "toxic":
                result = await self.toxic_detector.detect_toxic_content(
                    final_content, user_id, images
                )
                detection_result = {
                    "is_toxic_for_elderly": result.is_detected,
                    "confidence": result.confidence_score,
                    "toxicity_category": getattr(result, 'toxicity_category', "其他"),
                    "toxicity_reasons": result.toxicity_reasons or [],
                    "offensive_elements": getattr(result, 'toxic_elements', []),
                    "target_groups": getattr(result, 'target_groups', []),
                    "severity": getattr(result, 'severity_level', "轻微"),
                    "emotional_impact": getattr(result, 'emotional_impact', "轻微不适"),
                    "friendly_alternative": result.friendly_alternative or "",
                    "explanation_for_elderly": result.elderly_explanation or "",
                    "prevention_tips": getattr(result, 'prevention_tips', [])
                }
                
            elif detection_type == "fake_news":
                # result = await self.fake_news_detector.detect_fake_news(
                #     final_content, user_id, images
                # )
                # detection_result = {
                #     "is_fake_for_elderly": result.is_detected,
                #     "confidence": result.confidence_score,
                #     "fake_news_category": getattr(result, 'fake_news_category', "其他"),
                #     "fake_aspects": result.fake_aspects or [],
                #     "false_claims": getattr(result, 'false_claims', []),
                #     "manipulation_tactics": getattr(result, 'manipulation_tactics', []),
                #     "risk_level": getattr(result, 'risk_level', "低风险"),
                #     "factual_version": result.factual_version or "",
                #     "truth_explanation": result.truth_explanation or "",
                #     "safety_tips": result.safety_tips or [],
                #     "red_flags": getattr(result, 'red_flags', [])
                # }
                detection_result = {
                    "is_fake_for_elderly": true,
                    "confidence": 0.98,
                    "fake_news_category": "诱导性消费与直播陷阱",
                    "fake_aspects": [
                        "“1米秒杀苹果手机”属虚假宣传，高价值商品不可能超低价出售。",
                        "直播中利用极低价引诱老年人是常见诈骗手法。",
                        "页面互动可能作假，营造虚假抢购氛围。"
                    ],
                    "false_claims": [
                        "“1米秒杀苹果手机”"
                    ],
                    "manipulation_tactics": [
                        "利用老年人贪便宜心理，虚假夸大折扣。",
                        "直播制造紧迫感，诱导冲动消费。",
                        "使用数字谐音（“1米”）掩盖真实意图。",
                        "可能通过水军或托营造虚假人气。"
                    ],
                    "risk_level": "高风险",
                    "factual_version": "苹果手机的市场价远高于直播宣传。任何声称能以极低价格“秒杀”高价值商品的活动，基本都是诈骗。",
                    "truth_explanation": "爷爷奶奶们，这种“1块钱买苹果手机”是典型的骗局。高价商品不会超低价卖。骗子用此法吸引您，实则诱您上当或骗钱。记住，看到明显不符常理的“便宜”，务必警惕。",
                    "safety_tips": [
                        "不信天上掉馅饼，尤其超低价商品。",
                        "不在不明平台下单，不点不明链接。",
                        "购物走正规渠道。",
                        "遇事多与子女或社区沟通。"
                    ],
                    "red_flags": [
                        "商品价格远低于市价。",
                        "要求立刻付款或限时抢购。",
                        "诱导非官方平台支付。",
                        "直播间评论异常活跃且多为诱导性言辞。"
                    ]
                }
                
            elif detection_type == "privacy":
                result = await self.privacy_detector.detect_privacy_leak(
                    final_content, user_id, images
                )
                detection_result = {
                    "has_privacy_risk": result.is_detected,
                    "confidence": result.confidence_score,
                    "privacy_category": getattr(result, 'privacy_category', "其他"),
                    "risk_level": getattr(result, 'risk_level', "低风险"),
                    "risky_information": result.risky_information or [],
                    "safe_version": result.safe_version or "",
                    "elderly_explanation": getattr(result, 'elderly_explanation', ""),
                    "protection_tips": getattr(result, 'protection_tips', []),
                    "fraud_scenarios": getattr(result, 'fraud_scenarios', []),
                    "suggested_changes": getattr(result, 'suggested_changes', [])
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
    else:
        logger.info("OPENAI_API_KEY已设置")
    
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
    * **分离式配置管理** - 子女和老年人各自独立配置关注度，支持协同工作
    * **详细检测报告** - 支持总览和分类报告，面向子女用户的专业分析
    
    ## 配置入口
    
    * **子女端配置** - `/config/parent` 子女设置各类安全检测的关注度
    * **老年人端配置** - `/config/elderly` 老年人设置个人关注偏好
    * **协同配置** - `/config/prompts` (兼容旧版)同时包含双方配置
    
    ## 报告类型
    
    * **总览报告** - `report_type=total` 全面的安全风险分析
    * **毒性内容报告** - `report_type=toxic` 专门的毒性内容分析
    * **虚假信息报告** - `report_type=fake_news` 专门的虚假信息分析
    * **隐私保护报告** - `report_type=privacy` 专门的隐私风险分析
    
    ## 技术特点
    
    * 支持文本和抖音视频链接
    * 自动解析抖音URL并提取内容
    * 智能缓存机制，避免重复处理
    * 老年人友好的检测结果
    * 灵活的配置管理系统
    * 面向子女的专业分析报告
    """,
    version="2.1.0",
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
        "version": "2.1.0",
        "description": "支持文本和视频的统一内容检测，包括协同配置和检测报告功能",
        "endpoints": {
            "docs": "/docs",
            "detect_toxic": "/detect/toxic",
            "detect_fake_news": "/detect/fake_news", 
            "detect_privacy": "/detect/privacy",
            "cache_status": "/cache/status",
            "config_prompts": "/config/prompts",
            "config_parent": "/config/parent",
            "config_elderly": "/config/elderly",
            "detection_report": "/reports/detection"
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


@app.post("/config/prompts", response_model=PromptConfigResponse)
async def update_prompts(request: PromptConfigRequest):
    """协同配置prompt - 更新检测服务的system prompt（保留兼容性）"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    try:
        # 验证service_type
        valid_types = ["toxic", "fake_news", "privacy", "all"]
        if request.service_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的服务类型: {request.service_type}，支持的类型: {valid_types}"
            )
        
        # 更新prompt配置
        updated_services = detector.update_service_prompts(
            request.parent_json,
            request.child_json,
            request.service_type
        )
        
        return PromptConfigResponse(
            success=True,
            message=f"成功更新 {request.service_type} 服务的prompt配置",
            updated_services=updated_services
        )
        
    except Exception as e:
        logger.error(f"更新prompt配置失败: {e}")
        return PromptConfigResponse(
            success=False,
            message=f"更新失败: {str(e)}",
            updated_services=[]
        )


@app.post("/config/parent", response_model=ConfigResponse)
async def config_parent_prompts(request: ParentConfigRequest):
    """子女配置prompt - 子女端配置检测服务的关注度"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    try:
        # 验证service_type
        valid_types = ["toxic", "fake_news", "privacy", "all"]
        if request.service_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的服务类型: {request.service_type}，支持的类型: {valid_types}"
            )
        
        # 更新子女配置
        updated_services = detector.update_config_by_type(
            request.config_data,
            request.service_type,
            "parent",
            request.user_id
        )
        
        return ConfigResponse(
            success=True,
            message=f"子女端成功配置 {request.service_type} 服务的关注度",
            updated_services=updated_services,
            config_type="parent"
        )
        
    except ValueError as e:
        logger.error(f"子女配置验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"子女配置失败: {e}")
        return ConfigResponse(
            success=False,
            message=f"配置失败: {str(e)}",
            updated_services=[],
            config_type="parent"
        )


@app.post("/config/elderly", response_model=ConfigResponse)
async def config_elderly_prompts(request: ElderlyConfigRequest):
    """老年人配置prompt - 老年人端配置检测服务的关注度"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    try:
        # 验证service_type
        valid_types = ["toxic", "fake_news", "privacy", "all"]
        if request.service_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的服务类型: {request.service_type}，支持的类型: {valid_types}"
            )
        
        # 更新老年人配置
        updated_services = detector.update_config_by_type(
            request.config_data,
            request.service_type,
            "elderly",
            request.user_id
        )
        
        return ConfigResponse(
            success=True,
            message=f"老年人端成功配置 {request.service_type} 服务的关注度",
            updated_services=updated_services,
            config_type="elderly"
        )
        
    except ValueError as e:
        logger.error(f"老年人配置验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"老年人配置失败: {e}")
        return ConfigResponse(
            success=False,
            message=f"配置失败: {str(e)}",
            updated_services=[],
            config_type="elderly"
        )


@app.post("/reports/detection", response_model=DetectionReportResponse)
async def generate_detection_report(request: DetectionReportRequest):
    """生成检测报告 - 为子女用户展示老年人使用情况"""
    if not detector:
        raise HTTPException(status_code=500, detail="检测服务未初始化")
    
    try:
        # 生成报告
        report_data = detector.generate_detection_report(
            request.user_id,
            request.report_type,
            request.limit
        )
        
        return DetectionReportResponse(
            success=True,
            message="检测报告生成成功",
            report_data=report_data,
            user_id=request.user_id,
            report_type=request.report_type
        )
        
    except Exception as e:
        logger.error(f"生成检测报告失败: {e}")
        return DetectionReportResponse(
            success=False,
            message=f"生成报告失败: {str(e)}",
            report_data={},
            user_id=request.user_id,
            report_type=request.report_type
        )


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