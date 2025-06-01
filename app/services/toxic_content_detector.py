import asyncio
import openai
from typing import List, Dict, Any, Optional
import logging
import json
import re
from datetime import datetime
from detoxify import Detoxify
from ..data_models.detection_result import ToxicContentDetectionResult

logger = logging.getLogger(__name__)


class ToxicContentDetector:
    """毒性内容检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        
        # 初始化detoxify模型
        try:
            self.detoxify_model = Detoxify('multilingual')
        except Exception as e:
            logger.warning(f"Detoxify模型加载失败，将仅使用LLM: {e}")
            self.detoxify_model = None
        
        # 毒性内容检测的系统提示词
        self.system_prompt = """
你是一个专业的毒性内容检测专家。你的任务是分析给定的内容，判断其是否包含有害、毒性或不当内容。

请从以下几个维度进行分析：
1. 仇恨言论：是否包含针对特定群体的仇恨或歧视性言论
2. 威胁暴力：是否包含暴力威胁或煽动暴力的内容
3. 骚扰辱骂：是否包含人身攻击、辱骂或骚扰性言论
4. 色情低俗：是否包含不当的性暗示或色情内容
5. 自我伤害：是否包含自杀、自残等自我伤害内容
6. 极端主义：是否包含极端主义或恐怖主义相关内容
7. 网络霸凌：是否构成网络霸凌或恶意攻击

请以JSON格式返回分析结果，包含以下字段：
{
    "is_toxic": boolean,  // 是否为毒性内容
    "confidence": float,  // 置信度 (0-1)
    "toxicity_categories": {  // 各类毒性分数
        "hate_speech": float,
        "threat": float,
        "harassment": float,
        "sexual_content": float,
        "self_harm": float,
        "extremism": float,
        "cyberbullying": float
    },
    "severity_level": string,  // 严重程度: "low", "medium", "high"
    "reasons": [string],  // 判断理由列表
    "evidence": [string],  // 支撑证据列表
    "moderation_suggestions": [string]  // 内容审核建议
}

请确保分析客观、准确，考虑文化背景和语境。
"""
    
    async def detect_toxic_content(self, content: str, user_id: Optional[str] = None) -> ToxicContentDetectionResult:
        """检测毒性内容"""
        try:
            # 使用detoxify进行初步检测
            detoxify_result = None
            if self.detoxify_model and content.strip():
                try:
                    detoxify_result = self.detoxify_model.predict(content)
                except Exception as e:
                    logger.warning(f"Detoxify检测失败: {e}")
            
            # 使用LLM进行详细分析
            llm_result = await self._analyze_content_with_llm(content)
            
            # 综合两个模型的结果
            final_result = self._combine_results(detoxify_result, llm_result)
            
            return ToxicContentDetectionResult(
                result_id=self._generate_result_id(),
                content_text=content,
                is_detected=final_result.get("is_toxic", False),
                confidence_score=final_result.get("confidence", 0.0),
                reasons=final_result.get("reasons", []),
                evidence=final_result.get("evidence", []),
                user_id=user_id,
                toxicity_categories=final_result.get("toxicity_categories", {}),
                severity_level=final_result.get("severity_level", "low")
            )
            
        except Exception as e:
            logger.error(f"毒性内容检测失败: {e}")
            return self._create_error_result(content, user_id, str(e))
    
    async def _analyze_content_with_llm(self, content: str) -> Dict[str, Any]:
        """使用大模型分析内容"""
        try:
            # 限制内容长度
            if len(content) > 2000:
                content = content[:2000] + "..."
            
            user_prompt = f"""
请分析以下内容是否包含毒性或有害内容：

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
            logger.error(f"LLM分析失败: {e}")
            return self._get_default_llm_result()
    
    def _combine_results(self, detoxify_result: Optional[Dict], llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """综合detoxify和LLM的结果"""
        combined_result = llm_result.copy()
        
        if detoxify_result:
            # detoxify的结果映射
            detoxify_mapping = {
                'toxicity': 'general_toxicity',
                'severe_toxicity': 'severe_toxicity',
                'obscene': 'obscene',
                'threat': 'threat',
                'insult': 'harassment',
                'identity_attack': 'hate_speech'
            }
            
            # 更新毒性分类分数
            if 'toxicity_categories' not in combined_result:
                combined_result['toxicity_categories'] = {}
            
            max_detoxify_score = 0
            for key, value in detoxify_result.items():
                if key in detoxify_mapping:
                    mapped_key = detoxify_mapping[key]
                    combined_result['toxicity_categories'][mapped_key] = float(value)
                    max_detoxify_score = max(max_detoxify_score, float(value))
            
            # 如果detoxify检测到高毒性，调整最终结果
            if max_detoxify_score > 0.7:
                combined_result['is_toxic'] = True
                combined_result['confidence'] = max(combined_result.get('confidence', 0), max_detoxify_score)
                
                if max_detoxify_score > 0.9:
                    combined_result['severity_level'] = 'high'
                elif max_detoxify_score > 0.7:
                    combined_result['severity_level'] = 'medium'
                
                # 添加detoxify的检测理由
                if 'reasons' not in combined_result:
                    combined_result['reasons'] = []
                combined_result['reasons'].append(f"机器学习模型检测到毒性内容，最高分数: {max_detoxify_score:.2f}")
        
        return combined_result
    
    def _get_default_llm_result(self) -> Dict[str, Any]:
        """获取默认的LLM结果"""
        return {
            "is_toxic": False,
            "confidence": 0.0,
            "toxicity_categories": {},
            "severity_level": "low",
            "reasons": ["分析结果解析失败"],
            "evidence": [],
            "moderation_suggestions": []
        }
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"toxic_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _create_error_result(self, content: str, user_id: Optional[str], error_msg: str) -> ToxicContentDetectionResult:
        """创建错误结果"""
        return ToxicContentDetectionResult(
            result_id=self._generate_result_id(),
            content_text=content,
            is_detected=False,
            confidence_score=0.0,
            reasons=[f"检测失败: {error_msg}"],
            evidence=[],
            user_id=user_id,
            toxicity_categories={},
            severity_level="low"
        ) 