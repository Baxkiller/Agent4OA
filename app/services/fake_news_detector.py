import asyncio
import openai
from typing import List, Dict, Any, Optional
import logging
import json
import re
from datetime import datetime
from ..data_models.detection_result import FakeNewsDetectionResult
from .content_crawler import ContentCrawler

logger = logging.getLogger(__name__)


class FakeNewsDetector:
    """虚假信息检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        self.crawler = ContentCrawler()
        
        # 虚假信息检测的系统提示词
        self.system_prompt = """
你是一个专业的虚假信息检测专家。你的任务是分析给定的内容，判断其是否包含虚假信息或诈骗内容。

请从以下几个维度进行分析：
1. 事实准确性：内容中的事实陈述是否准确
2. 信息来源：是否有可靠的信息来源支撑
3. 逻辑一致性：内容逻辑是否自洽
4. 情感煽动：是否使用过度情感化的语言来误导读者
5. 时效性：信息是否过时或被断章取义
6. 诈骗特征：是否包含典型的诈骗话术或套路

请以JSON格式返回分析结果，包含以下字段：
{
    "is_fake": boolean,  // 是否为虚假信息
    "confidence": float,  // 置信度 (0-1)
    "reasons": [string],  // 判断理由列表
    "evidence": [string],  // 支撑证据列表
    "risk_level": string,  // 风险等级: "low", "medium", "high"
    "fact_check_suggestions": [string]  // 事实核查建议
}

请确保分析客观、准确，避免误判。
"""
    
    async def detect_fake_news_from_url(self, content_url: str, user_id: Optional[str] = None) -> FakeNewsDetectionResult:
        """从URL检测虚假信息"""
        try:
            # 判断是视频还是文章链接
            if self._is_video_url(content_url):
                return await self._detect_from_video(content_url, user_id)
            else:
                return await self._detect_from_article(content_url, user_id)
                
        except Exception as e:
            logger.error(f"虚假信息检测失败: {e}")
            return self._create_error_result(content_url, user_id, str(e))
    
    async def detect_fake_news_from_text(self, content_text: str, user_id: Optional[str] = None) -> FakeNewsDetectionResult:
        """从文本内容检测虚假信息"""
        try:
            analysis_result = await self._analyze_content_with_llm(content_text)
            
            return FakeNewsDetectionResult(
                result_id=self._generate_result_id(),
                content_text=content_text,
                is_detected=analysis_result.get("is_fake", False),
                confidence_score=analysis_result.get("confidence", 0.0),
                reasons=analysis_result.get("reasons", []),
                evidence=analysis_result.get("evidence", []),
                user_id=user_id,
                fact_check_sources=analysis_result.get("fact_check_suggestions", [])
            )
            
        except Exception as e:
            logger.error(f"文本虚假信息检测失败: {e}")
            return self._create_error_result(None, user_id, str(e), content_text)
    
    async def _detect_from_video(self, video_url: str, user_id: Optional[str]) -> FakeNewsDetectionResult:
        """从视频检测虚假信息"""
        # 提取视频内容
        frames, transcript = await self.crawler.extract_video_content(video_url)
        
        # 构建分析内容
        content_for_analysis = f"视频音频转录内容：\n{transcript}\n\n"
        
        # 如果有视频帧，可以添加视觉内容描述（这里简化处理）
        if frames:
            content_for_analysis += f"视频包含 {len(frames)} 个关键帧。"
        
        # 使用LLM分析
        analysis_result = await self._analyze_content_with_llm(content_for_analysis)
        
        return FakeNewsDetectionResult(
            result_id=self._generate_result_id(),
            content_url=video_url,
            content_text=transcript,
            is_detected=analysis_result.get("is_fake", False),
            confidence_score=analysis_result.get("confidence", 0.0),
            reasons=analysis_result.get("reasons", []),
            evidence=analysis_result.get("evidence", []),
            user_id=user_id,
            video_frames=frames,
            audio_transcript=transcript,
            fact_check_sources=analysis_result.get("fact_check_suggestions", [])
        )
    
    async def _detect_from_article(self, article_url: str, user_id: Optional[str]) -> FakeNewsDetectionResult:
        """从文章检测虚假信息"""
        # 提取文章内容
        article_content = await self.crawler.extract_article_content(article_url)
        
        if not article_content:
            return self._create_error_result(article_url, user_id, "无法提取文章内容")
        
        # 使用LLM分析
        analysis_result = await self._analyze_content_with_llm(article_content)
        
        return FakeNewsDetectionResult(
            result_id=self._generate_result_id(),
            content_url=article_url,
            content_text=article_content[:1000] + "..." if len(article_content) > 1000 else article_content,
            is_detected=analysis_result.get("is_fake", False),
            confidence_score=analysis_result.get("confidence", 0.0),
            reasons=analysis_result.get("reasons", []),
            evidence=analysis_result.get("evidence", []),
            user_id=user_id,
            fact_check_sources=analysis_result.get("fact_check_suggestions", [])
        )
    
    async def _analyze_content_with_llm(self, content: str) -> Dict[str, Any]:
        """使用大模型分析内容"""
        try:
            # 限制内容长度以避免token超限
            if len(content) > 3000:
                content = content[:3000] + "..."
            
            user_prompt = f"""
请分析以下内容是否包含虚假信息或诈骗内容：

内容：
{content}

请严格按照JSON格式返回分析结果。
"""
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON结果
            try:
                # 提取JSON部分
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                else:
                    result_json = json.loads(result_text)
                
                return result_json
                
            except json.JSONDecodeError:
                logger.warning(f"LLM返回结果不是有效JSON: {result_text}")
                return {
                    "is_fake": False,
                    "confidence": 0.0,
                    "reasons": ["分析结果解析失败"],
                    "evidence": [],
                    "risk_level": "low",
                    "fact_check_suggestions": []
                }
                
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return {
                "is_fake": False,
                "confidence": 0.0,
                "reasons": [f"分析过程出错: {str(e)}"],
                "evidence": [],
                "risk_level": "low",
                "fact_check_suggestions": []
            }
    
    def _is_video_url(self, url: str) -> bool:
        """判断是否为视频URL"""
        video_domains = [
            'youtube.com', 'youtu.be', 'bilibili.com', 'douyin.com',
            'tiktok.com', 'weibo.com', 'qq.com'
        ]
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        
        url_lower = url.lower()
        
        # 检查域名
        for domain in video_domains:
            if domain in url_lower:
                return True
        
        # 检查文件扩展名
        for ext in video_extensions:
            if url_lower.endswith(ext):
                return True
        
        return False
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"fake_news_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _create_error_result(self, content_url: Optional[str], user_id: Optional[str], 
                           error_msg: str, content_text: Optional[str] = None) -> FakeNewsDetectionResult:
        """创建错误结果"""
        return FakeNewsDetectionResult(
            result_id=self._generate_result_id(),
            content_url=content_url,
            content_text=content_text,
            is_detected=False,
            confidence_score=0.0,
            reasons=[f"检测失败: {error_msg}"],
            evidence=[],
            user_id=user_id
        ) 