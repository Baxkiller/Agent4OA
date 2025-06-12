import asyncio
import openai
import re
from typing import List, Dict, Any, Optional
import logging
import json
import base64
from datetime import datetime

try:
    from ..data_models.detection_result import PrivacyLeakDetectionResult
except ImportError:
    # 当直接运行此文件时，使用绝对导入
    import sys
    import os
    # 获取项目根目录（当前文件的上上级目录）
    current_dir = os.path.dirname(__file__)  # services目录
    parent_dir = os.path.dirname(current_dir)  # app目录  
    project_root = os.path.dirname(parent_dir)  # 项目根目录
    sys.path.insert(0, project_root)
    from app.data_models.detection_result import PrivacyLeakDetectionResult

logger = logging.getLogger(__name__)


class PrivacyLeakDetector:
    """老年人隐私保护检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o"):  # 默认使用多模态模型
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model_name = model_name
        

        
        # 隐私保护的系统提示词
        # 从app/prompts/privacy_protection_prompt.txt中读取
        try:
            with open('app/prompts/privacy_protection_prompt.txt', 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
        except FileNotFoundError:
            # 当直接运行此文件时，使用相对于当前文件的路径
            import os
            current_dir = os.path.dirname(__file__)
            prompt_path = os.path.join(os.path.dirname(current_dir), 'prompts', 'privacy_protection_prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
    
    async def detect_privacy_leak(
        self, 
        content: str, 
        user_id: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> PrivacyLeakDetectionResult:
        """检测隐私泄露风险（支持多模态：文本+图像）"""
        max_tries = 5
        last_error = None
        
        for attempt in range(max_tries):
            try:
                logger.info(f"隐私保护检测尝试 {attempt + 1}/{max_tries}")
                
                # 使用LLM进行详细分析（支持多模态）
                analysis_result = await self._analyze_content_with_llm_multimodal(
                    content, images
                )
                
                # 兼容新旧字段
                has_risk = analysis_result.get("has_privacy_risk", analysis_result.get("has_privacy_leak", False))
                
                # 处理 evidence 字段 - 将字典列表转换为字符串列表
                risky_info = analysis_result.get("risky_information", [])
                evidence_strings = []
                if isinstance(risky_info, list):
                    for item in risky_info:
                        if isinstance(item, dict):
                            # 将字典转换为描述性字符串
                            risk_type = item.get("type", "未知类型")
                            content = item.get("content", "")
                            explanation = item.get("risk_explanation", "")
                            evidence_strings.append(f"{risk_type}: {content} - {explanation}")
                        else:
                            evidence_strings.append(str(item))
                
                return PrivacyLeakDetectionResult(
                    result_id=self._generate_result_id(),
                    content_text=content,
                    is_detected=has_risk,
                    confidence_score=analysis_result.get("confidence", 0.0),
                    reasons=analysis_result.get("privacy_risks", analysis_result.get("reasons", [])),
                    evidence=evidence_strings,  # 使用转换后的字符串列表
                    user_id=user_id,
                    privacy_types=analysis_result.get("privacy_risks", []),
                    sensitive_entities=analysis_result.get("risky_information", []),
                    risk_level=analysis_result.get("risk_level", "low"),
                    
                    # 新增的老年人专用字段
                    has_privacy_risk=has_risk,
                    privacy_risks=analysis_result.get("privacy_risks", []),
                    risky_information=analysis_result.get("risky_information", []),
                    safe_version=analysis_result.get("safe_version", ""),
                    elderly_explanation=analysis_result.get("elderly_explanation", ""),
                    protection_tips=analysis_result.get("protection_tips", []),
                    suggested_changes=analysis_result.get("suggested_changes", [])
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"隐私保护检测第{attempt + 1}次尝试失败: {e}")
                if attempt < max_tries - 1:
                    await asyncio.sleep(1)  # 短暂等待后重试
                    
        # 所有尝试都失败
        logger.error(f"隐私保护检测失败，已尝试{max_tries}次: {last_error}")
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
            
            user_prompt = f"请帮这位老年朋友检查一下即将发送的内容是否安全：\n\n要发送的内容：\n{content}"
            
            # 如果有图像，添加说明
            if images and len(images) > 0:
                user_prompt += f"\n\n图像数量：{len(images)}张，请一起检查图片中是否有隐私信息"
            
            user_prompt += "\n\n请仔细检查并给出安全建议。"
            
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
                max_tokens=1500
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
            "has_privacy_risk": False,
            "confidence": 0.0,
            "risk_level": "low",
            "privacy_risks": ["系统无法正常分析内容"],
            "risky_information": [],
            "safe_version": "内容的安全性暂时无法确定",
            "elderly_explanation": "抱歉，系统暂时无法分析这段内容的隐私风险，建议您谨慎发送，或者咨询家人朋友的意见。",
            "protection_tips": ["发送个人信息前，先想想是否真的有必要", "重要信息最好当面或电话沟通", "不确定的时候可以问问子女"],
            "suggested_changes": []
        }
    
    def _generate_result_id(self) -> str:
        """生成结果ID"""
        return f"privacy_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _create_error_result(self, content: str, user_id: Optional[str], 
                            error_msg: str) -> PrivacyLeakDetectionResult:
        """创建错误结果"""
        return PrivacyLeakDetectionResult(
            result_id=self._generate_result_id(),
            content_text=content,
            is_detected=False,
            confidence_score=0.0,
            reasons=[f"检测失败: {error_msg}"],
            evidence=[f"系统错误: {error_msg}"],  # 确保是字符串列表
            user_id=user_id,
            privacy_types=[],
            sensitive_entities=[],
            risk_level="low",
            
            # 新增字段
            has_privacy_risk=False,
            privacy_risks=[f"检测失败: {error_msg}"],
            risky_information=[],
            safe_version="由于系统错误，无法提供安全建议",
            elderly_explanation="系统遇到了技术问题，无法完成隐私检查。建议您暂时不要发送，或者咨询家人的意见。",
            protection_tips=["遇到技术问题时，谨慎为上", "重要信息建议当面或电话沟通"],
            suggested_changes=[]
        )

if __name__ == "__main__":
    # 配置日志输出到文件和控制台
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('privacy_test.log', encoding='utf-8'),  # 输出到文件
            logging.StreamHandler()  # 输出到控制台
        ]
    )
    
    import asyncio
    
    async def test_detector():
        import os
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("错误: 未设置OPENAI_API_KEY环境变量")
            print("请设置环境变量后再运行测试")
            return
        detector = PrivacyLeakDetector(openai_api_key)
        
        # 测试多个不同类型的内容，模拟老年人可能要发送的各种信息
        test_cases = [
            "我住在北京市朝阳区建国路123号，手机号是13812345678，有空来找我玩！",  # 明显隐私泄露
            "今天天气不错，我在公园里散步，心情很好。",  # 安全内容
            "我的银行卡号是6225123456789012，密码是123456，帮我转账吧。",  # 严重财务信息泄露
            "我儿子在腾讯公司上班，工资很高，我们家很有钱。",  # 家庭信息泄露
            "我的身份证号是110101195001011234，可以帮我订票吗？",  # 身份信息泄露
            "昨天去医院检查，医生说我身体还不错，子女们都很孝顺。",  # 相对安全的分享
            "我的QQ号是123456789，微信号是wanglaoshi，快加我好友！",  # 社交账号泄露
            "明天上午10点我要去银行取钱，下午2点去超市买菜。"  # 行程信息泄露
        ]
        
        for i, test_content in enumerate(test_cases, 1):
            print(f"\n{'='*70}")
            print(f"测试案例 {i}: {test_content}")
            print('='*70)
            
            result = await detector.detect_privacy_leak(test_content)
            
            print(f"📝 要发送的内容: {test_content}")
            print(f"🔒 是否有隐私风险: {'有风险' if result.is_detected else '安全'}")
            print(f"🎯 风险程度: {result.confidence_score:.1%}")
            print(f"⚠️  风险等级: {result.risk_level}")
            
            if result.is_detected:
                print(f"\n🚨 隐私风险类型:")
                for risk in result.privacy_risks or []:
                    print(f"   • {risk}")
                
                if result.risky_information:
                    print(f"\n🔍 具体风险信息:")
                    for info in result.risky_information:
                        print(f"   • {info.get('type', '未知')}: {info.get('content', '')} - {info.get('risk_explanation', '')}")
                
                print(f"\n✅ 安全的替代版本:")
                print(f"   {result.safe_version}")
                
                if result.suggested_changes:
                    print(f"\n📝 具体修改建议:")
                    for change in result.suggested_changes:
                        print(f"   原文: {change.get('original', '')}")
                        print(f"   改为: {change.get('suggested', '')}")
                        print(f"   原因: {change.get('reason', '')}")
                        print()
            else:
                print(f"✅ 内容安全，可以放心发送")
            
            print(f"\n💬 温馨提醒:")
            print(f"   {result.elderly_explanation}")
            
            if result.protection_tips:
                print(f"\n💡 隐私保护小贴士:")
                for tip in result.protection_tips:
                    print(f"   • {tip}")
    
    asyncio.run(test_detector()) 