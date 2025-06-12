import asyncio
import openai
from typing import List, Dict, Any, Optional
import logging
import json
import re
import base64
from datetime import datetime
try:
    from ..data_models.detection_result import FakeNewsDetectionResult
except ImportError:
    # 当直接运行此文件时，使用绝对导入
    import sys
    import os
    # 获取项目根目录（当前文件的上上级目录）
    current_dir = os.path.dirname(__file__)  # services目录
    parent_dir = os.path.dirname(current_dir)  # app目录  
    project_root = os.path.dirname(parent_dir)  # 项目根目录
    sys.path.insert(0, project_root)
    from app.data_models.detection_result import FakeNewsDetectionResult

logger = logging.getLogger(__name__)


class FakeNewsDetector:
    """虚假信息检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):  # 默认使用多模态模型
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        
        # 虚假信息检测的系统提示词
        # 从app/prompts/fake_news_detection_prompt.txt中读取
        try:
            with open('app/prompts/fake_news_detection_prompt.txt', 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
        except FileNotFoundError:
            # 当直接运行此文件时，使用相对于当前文件的路径
            import os
            current_dir = os.path.dirname(__file__)
            prompt_path = os.path.join(os.path.dirname(current_dir), 'prompts', 'fake_news_detection_prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
    
    async def detect_fake_news(
        self, 
        content: str, 
        user_id: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> FakeNewsDetectionResult:
        """检测虚假信息（支持多模态：文本+图像）"""
        max_tries = 5
        last_error = None
        
        for attempt in range(max_tries):
            try:
                logger.info(f"虚假信息检测尝试 {attempt + 1}/{max_tries}")
                
                # 使用LLM进行详细分析（支持多模态）
                analysis_result = await self._analyze_content_with_llm_multimodal(
                    content, images
                )
                
                # 兼容新旧字段
                is_fake = analysis_result.get("is_fake_news", analysis_result.get("is_fake", False))
                
                return FakeNewsDetectionResult(
                    result_id=self._generate_result_id(),
                    content_text=content,
                    is_detected=is_fake,
                    confidence_score=analysis_result.get("confidence", 0.0),
                    reasons=analysis_result.get("fake_aspects", analysis_result.get("reasons", [])),
                    evidence=analysis_result.get("false_claims", analysis_result.get("evidence", [])),
                    user_id=user_id,
                    fact_check_sources=analysis_result.get("safety_tips", analysis_result.get("fact_check_suggestions", [])),
                    
                    # 新增字段
                    is_fake_for_elderly=is_fake,
                    fake_aspects=analysis_result.get("fake_aspects", []),
                    false_claims=analysis_result.get("false_claims", []),
                    factual_version=analysis_result.get("factual_version", ""),
                    truth_explanation=analysis_result.get("truth_explanation", ""),
                    safety_tips=analysis_result.get("safety_tips", [])
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"虚假信息检测第{attempt + 1}次尝试失败: {e}")
                if attempt < max_tries - 1:
                    await asyncio.sleep(1)  # 短暂等待后重试
                    
        # 所有尝试都失败
        logger.error(f"虚假信息检测失败，已尝试{max_tries}次: {last_error}")
        return self._create_error_result(content, user_id, str(last_error))

    async def _analyze_content_with_llm_multimodal(
        self, 
        content: str, 
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """使用多模态大模型分析内容"""
        try:
            # 限制文本内容长度
            if len(content) > 2000:
                content = content[:2000] + "..."
            
            user_prompt = f"请分析以下内容是否包含虚假信息、谣言或诈骗内容：\n\n文本内容：\n{content}"
            
            # 如果有图像，添加说明
            if images and len(images) > 0:
                user_prompt += f"\n\n图像数量：{len(images)}张，请结合图像内容进行分析"
            
            user_prompt += "\n\n请严格按照JSON格式返回分析结果。"
            
            # 构建messages，支持图像输入
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # 用户消息包含文本和图像
            user_message = {"role": "user", "content": []}
            
            # 添加文本内容
            user_message["content"].append({
                "type": "text",
                "text": user_prompt
            })
            
            # 添加图像（最多5张）
            if images:
                image_count = min(len(images), 5)
                for i, image_path in enumerate(images[:image_count]):
                    try:
                        with open(image_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                        
                        user_message["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        logger.warning(f"无法读取图像 {image_path}: {e}")
            
            messages.append(user_message)
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON结果
            try:
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                else:
                    result_json = json.loads(result_text)
                
                return result_json
                
            except json.JSONDecodeError:
                logger.warning(f"LLM返回结果不是有效JSON: {result_text}")
                return self._get_default_llm_result()
                
        except Exception as e:
            logger.error(f"多模态LLM分析失败: {e}")
            return self._get_default_llm_result()
    
    def _get_default_llm_result(self) -> Dict[str, Any]:
        """获取默认的LLM结果"""
        return {
            "is_fake_news": False,
            "confidence": 0.0,
            "fake_aspects": ["系统无法正常分析内容"],
            "false_claims": [],
            "risk_level": "低风险",
            "factual_version": "内容的真实性暂时无法确定",
            "truth_explanation": "抱歉，系统暂时无法分析这段内容，建议您向权威机构或专业人士咨询。",
            "safety_tips": ["遇到不确定的信息，可以向家人或朋友询问", "可以查看官方媒体的相关报道"]
        }
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"fake_news_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _create_error_result(self, content: str, user_id: Optional[str], 
                            error_msg: str) -> FakeNewsDetectionResult:
        """创建错误结果"""
        return FakeNewsDetectionResult(
            result_id=self._generate_result_id(),
            content_text=content,
            is_detected=False,
            confidence_score=0.0,
            reasons=[f"检测失败: {error_msg}"],
            evidence=[],
            user_id=user_id,
            fact_check_sources=[],
            
            # 新增字段
            is_fake_for_elderly=False,
            fake_aspects=[f"检测失败: {error_msg}"],
            false_claims=[],
            factual_version="由于系统错误，无法提供准确信息",
            truth_explanation="系统遇到了技术问题，无法完成分析。建议您稍后重试或咨询专业人士。",
            safety_tips=["遇到技术问题时，可以稍后重试", "重要信息建议多方求证"]
        )

if __name__ == "__main__":
    # 配置日志输出到文件和控制台
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('fake_news_test.log', encoding='utf-8'),  # 输出到文件
            logging.StreamHandler()  # 输出到控制台
        ]
    )
    
    import asyncio
    from app.services.content_crawler import ContentCrawler
    
    async def test_detector():
        import os
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("错误: 未设置OPENAI_API_KEY环境变量")
            print("请设置环境变量后再运行测试")
            return
        detector = FakeNewsDetector(openai_api_key)
        crawler = ContentCrawler()
        douyin_content=crawler.process_douyin_content("https://www.iesdouyin.com/share/video/7510767099883867451/?region=CN&mid=7295817689289033738&u_code=174jbch63&did=MS4wLjABAAAAiI9AU35XILhOstht_K9TXNs_-ytW9mzHedcet48iSllA0s2OKl8r1cuJ3KqUh5Wj&iid=MS4wLjABAAAAMyVVHT8VSTilkC1aQjuNrjTTxeAR8ebw6XpfjCjWe60jlQ9gngEd8sBMgz7AqZ9x&with_sec_did=1&video_share_track_ver=&titleType=title&share_sign=7JQ.V8p.qvEOo1eXmZy5cWecgS6Cpv_QDhjHUaRGuqs-&share_version=340000&ts=1748786999&from_aid=1128&from_ssr=1&utm_source=copy&utm_campaign=client_share&utm_medium=android&app=aweme&activity_info=%7B%22social_author_id%22%3A%223959768795851737%22%2C%22social_share_id%22%3A%22102862430872_1748787023100%22%2C%22social_share_time%22%3A%221748787023%22%2C%22social_share_user_id%22%3A%22102862430872%22%7D&share_extra_params=%7B%22schema_type%22%3A%221%22%7D")
        
        result = await detector.detect_fake_news(content = douyin_content["transcript"], images = douyin_content["frames"])        
        print(f"🔍 原始信息: {result}")
        print(f"📱 是否为虚假信息: {'是' if result.is_detected else '否'}")
        print(f"🎯 确信程度: {result.confidence_score:.1%}")
        
        if result.is_detected:
            print(f"⚠️  风险等级: {getattr(result, 'risk_level', '未知')}")
            
            print(f"\n❓ 虚假方面:")
            for aspect in result.fake_aspects or []:
                print(f"   • {aspect}")
            
            print(f"\n🚫 虚假声称:")
            for claim in result.false_claims or []:
                print(f"   • {claim}")
            
            print(f"\n✨ 真实信息版本:")
            print(f"   {result.factual_version}")
        else:
            print(f"✅ 信息可信，无需纠正")
        
        print(f"\n💬 给老年人的解释:")
        print(f"   {result.truth_explanation}")
        
        if result.safety_tips:
            print(f"\n💡 防骗提醒:")
            for tip in result.safety_tips:
                print(f"   • {tip}")
    
    asyncio.run(test_detector()) 