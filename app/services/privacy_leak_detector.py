import asyncio
import openai
import re
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
import spacy
from ..data_models.detection_result import PrivacyLeakDetectionResult

logger = logging.getLogger(__name__)


class PrivacyLeakDetector:
    """隐私泄露检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        
        # 尝试加载spaCy模型用于NER
        try:
            self.nlp = spacy.load("zh_core_web_sm")
        except OSError:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("未找到spaCy模型，将仅使用LLM进行检测")
                self.nlp = None
        
        # 隐私信息的正则表达式模式
        self.privacy_patterns = {
            "phone": [
                r'1[3-9]\d{9}',  # 中国手机号
                r'\+86\s*1[3-9]\d{9}',  # 带国际区号的中国手机号
                r'\(\d{3}\)\s*\d{3}-\d{4}',  # 美国电话格式
                r'\d{3}-\d{3}-\d{4}',  # 简单电话格式
            ],
            "email": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            "id_card": [
                r'\b\d{17}[\dXx]\b',  # 中国身份证号
                r'\b\d{15}\b',  # 旧版中国身份证号
            ],
            "bank_card": [
                r'\b\d{16,19}\b',  # 银行卡号
            ],
            "address": [
                r'[\u4e00-\u9fa5]+省[\u4e00-\u9fa5]+市[\u4e00-\u9fa5]+区',  # 中文地址
                r'[\u4e00-\u9fa5]+路\d+号',  # 中文街道地址
            ],
            "qq": [
                r'QQ[:：]\s*\d{5,12}',
                r'qq[:：]\s*\d{5,12}',
                r'\bQQ\d{5,12}\b',
            ],
            "wechat": [
                r'微信[:：]\s*[A-Za-z0-9_-]+',
                r'WeChat[:：]\s*[A-Za-z0-9_-]+',
                r'wx[:：]\s*[A-Za-z0-9_-]+',
            ]
        }
        
        # 隐私泄露检测的系统提示词
        self.system_prompt = """
你是一个专业的隐私保护专家。你的任务是分析给定的内容，识别其中可能泄露个人隐私的信息。

请从以下几个维度进行分析：
1. 个人身份信息：姓名、身份证号、护照号等
2. 联系方式：电话号码、邮箱地址、家庭住址等
3. 财务信息：银行卡号、支付账号、收入信息等
4. 社交账号：QQ号、微信号、社交媒体账号等
5. 生物特征：照片、指纹、声纹等生物识别信息
6. 位置信息：具体地址、GPS坐标、常去场所等
7. 工作信息：公司名称、职位、工作地点等
8. 家庭信息：家庭成员、关系状况、子女信息等

请以JSON格式返回分析结果，包含以下字段：
{
    "has_privacy_leak": boolean,  // 是否存在隐私泄露
    "confidence": float,  // 置信度 (0-1)
    "privacy_types": [string],  // 隐私类型列表
    "sensitive_entities": [  // 敏感实体信息
        {
            "type": string,  // 实体类型
            "value": string,  // 实体值（脱敏后）
            "risk_level": string  // 风险等级
        }
    ],
    "risk_level": string,  // 总体风险等级: "low", "medium", "high"
    "reasons": [string],  // 判断理由列表
    "evidence": [string],  // 支撑证据列表
    "protection_suggestions": [string]  // 隐私保护建议
}

请确保分析准确，对敏感信息进行适当脱敏处理。
"""
    
    async def detect_privacy_leak(self, content: str, user_id: Optional[str] = None) -> PrivacyLeakDetectionResult:
        """检测隐私泄露"""
        try:
            # 使用正则表达式进行初步检测
            regex_result = self._detect_with_regex(content)
            
            # 使用NER进行实体识别
            ner_result = self._detect_with_ner(content) if self.nlp else {}
            
            # 使用LLM进行详细分析
            llm_result = await self._analyze_content_with_llm(content)
            
            # 综合所有检测结果
            final_result = self._combine_results(regex_result, ner_result, llm_result)
            
            return PrivacyLeakDetectionResult(
                result_id=self._generate_result_id(),
                content_text=content,
                is_detected=final_result.get("has_privacy_leak", False),
                confidence_score=final_result.get("confidence", 0.0),
                reasons=final_result.get("reasons", []),
                evidence=final_result.get("evidence", []),
                user_id=user_id,
                privacy_types=final_result.get("privacy_types", []),
                sensitive_entities=final_result.get("sensitive_entities", []),
                risk_level=final_result.get("risk_level", "low")
            )
            
        except Exception as e:
            logger.error(f"隐私泄露检测失败: {e}")
            return self._create_error_result(content, user_id, str(e))
    
    def _detect_with_regex(self, content: str) -> Dict[str, Any]:
        """使用正则表达式检测隐私信息"""
        detected_entities = []
        privacy_types = []
        
        for privacy_type, patterns in self.privacy_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 对敏感信息进行脱敏
                    masked_value = self._mask_sensitive_info(match, privacy_type)
                    detected_entities.append({
                        "type": privacy_type,
                        "value": masked_value,
                        "risk_level": self._assess_risk_level(privacy_type)
                    })
                    if privacy_type not in privacy_types:
                        privacy_types.append(privacy_type)
        
        has_privacy_leak = len(detected_entities) > 0
        confidence = min(0.9, len(detected_entities) * 0.3) if has_privacy_leak else 0.0
        
        return {
            "has_privacy_leak": has_privacy_leak,
            "confidence": confidence,
            "privacy_types": privacy_types,
            "sensitive_entities": detected_entities,
            "detection_method": "regex"
        }
    
    def _detect_with_ner(self, content: str) -> Dict[str, Any]:
        """使用命名实体识别检测隐私信息"""
        if not self.nlp:
            return {}
        
        try:
            doc = self.nlp(content)
            detected_entities = []
            privacy_types = []
            
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]:
                    privacy_type = self._map_ner_label_to_privacy_type(ent.label_)
                    if privacy_type:
                        masked_value = self._mask_sensitive_info(ent.text, privacy_type)
                        detected_entities.append({
                            "type": privacy_type,
                            "value": masked_value,
                            "risk_level": self._assess_risk_level(privacy_type)
                        })
                        if privacy_type not in privacy_types:
                            privacy_types.append(privacy_type)
            
            has_privacy_leak = len(detected_entities) > 0
            confidence = min(0.7, len(detected_entities) * 0.2) if has_privacy_leak else 0.0
            
            return {
                "has_privacy_leak": has_privacy_leak,
                "confidence": confidence,
                "privacy_types": privacy_types,
                "sensitive_entities": detected_entities,
                "detection_method": "ner"
            }
            
        except Exception as e:
            logger.warning(f"NER检测失败: {e}")
            return {}
    
    async def _analyze_content_with_llm(self, content: str) -> Dict[str, Any]:
        """使用大模型分析内容"""
        try:
            # 限制内容长度
            if len(content) > 2000:
                content = content[:2000] + "..."
            
            user_prompt = f"""
请分析以下内容是否包含隐私泄露风险：

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
    
    def _combine_results(self, regex_result: Dict, ner_result: Dict, llm_result: Dict) -> Dict[str, Any]:
        """综合所有检测结果"""
        combined_result = llm_result.copy()
        
        # 合并实体信息
        all_entities = []
        all_privacy_types = set()
        
        # 添加正则检测的结果
        if regex_result.get("sensitive_entities"):
            all_entities.extend(regex_result["sensitive_entities"])
            all_privacy_types.update(regex_result.get("privacy_types", []))
        
        # 添加NER检测的结果
        if ner_result.get("sensitive_entities"):
            all_entities.extend(ner_result["sensitive_entities"])
            all_privacy_types.update(ner_result.get("privacy_types", []))
        
        # 添加LLM检测的结果
        if combined_result.get("sensitive_entities"):
            all_entities.extend(combined_result["sensitive_entities"])
            all_privacy_types.update(combined_result.get("privacy_types", []))
        
        # 去重和更新结果
        combined_result["sensitive_entities"] = all_entities
        combined_result["privacy_types"] = list(all_privacy_types)
        
        # 如果任何方法检测到隐私泄露，则认为存在泄露
        has_leak = (regex_result.get("has_privacy_leak", False) or 
                   ner_result.get("has_privacy_leak", False) or 
                   combined_result.get("has_privacy_leak", False))
        
        combined_result["has_privacy_leak"] = has_leak
        
        # 计算综合置信度
        confidences = [
            regex_result.get("confidence", 0),
            ner_result.get("confidence", 0),
            combined_result.get("confidence", 0)
        ]
        combined_result["confidence"] = max(confidences) if has_leak else 0.0
        
        # 评估总体风险等级
        if len(all_entities) >= 3:
            combined_result["risk_level"] = "high"
        elif len(all_entities) >= 1:
            combined_result["risk_level"] = "medium"
        else:
            combined_result["risk_level"] = "low"
        
        return combined_result
    
    def _mask_sensitive_info(self, value: str, privacy_type: str) -> str:
        """对敏感信息进行脱敏处理"""
        if privacy_type == "phone":
            if len(value) >= 7:
                return value[:3] + "*" * (len(value) - 6) + value[-3:]
        elif privacy_type == "email":
            if "@" in value:
                local, domain = value.split("@", 1)
                if len(local) > 2:
                    local = local[:2] + "*" * (len(local) - 2)
                return f"{local}@{domain}"
        elif privacy_type == "id_card":
            if len(value) >= 8:
                return value[:4] + "*" * (len(value) - 8) + value[-4:]
        elif privacy_type == "bank_card":
            if len(value) >= 8:
                return value[:4] + "*" * (len(value) - 8) + value[-4:]
        else:
            # 通用脱敏：保留前后各1/4，中间用*替代
            if len(value) > 4:
                keep_len = max(1, len(value) // 4)
                return value[:keep_len] + "*" * (len(value) - 2 * keep_len) + value[-keep_len:]
        
        return value
    
    def _assess_risk_level(self, privacy_type: str) -> str:
        """评估隐私类型的风险等级"""
        high_risk = ["id_card", "bank_card", "phone"]
        medium_risk = ["email", "address", "qq", "wechat"]
        
        if privacy_type in high_risk:
            return "high"
        elif privacy_type in medium_risk:
            return "medium"
        else:
            return "low"
    
    def _map_ner_label_to_privacy_type(self, ner_label: str) -> Optional[str]:
        """将NER标签映射到隐私类型"""
        mapping = {
            "PERSON": "name",
            "ORG": "organization",
            "GPE": "location",
            "LOC": "location"
        }
        return mapping.get(ner_label)
    
    def _get_default_llm_result(self) -> Dict[str, Any]:
        """获取默认的LLM结果"""
        return {
            "has_privacy_leak": False,
            "confidence": 0.0,
            "privacy_types": [],
            "sensitive_entities": [],
            "risk_level": "low",
            "reasons": ["分析结果解析失败"],
            "evidence": [],
            "protection_suggestions": []
        }
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"privacy_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _create_error_result(self, content: str, user_id: Optional[str], error_msg: str) -> PrivacyLeakDetectionResult:
        """创建错误结果"""
        return PrivacyLeakDetectionResult(
            result_id=self._generate_result_id(),
            content_text=content,
            is_detected=False,
            confidence_score=0.0,
            reasons=[f"检测失败: {error_msg}"],
            evidence=[],
            user_id=user_id,
            privacy_types=[],
            sensitive_entities=[],
            risk_level="low"
        ) 