import asyncio
import dashscope
from typing import List, Dict, Any, Optional
import logging
import json
import re
import base64
from datetime import datetime
try:
    from ..data_models.detection_result import ToxicContentDetectionResult
except ImportError:
    # 当直接运行此文件时，设置正确的Python路径
    import sys
    import os
    # 获取项目根目录（当前文件的上上级目录）
    current_dir = os.path.dirname(__file__)  # services目录
    parent_dir = os.path.dirname(current_dir)  # app目录  
    project_root = os.path.dirname(parent_dir)  # 项目根目录
    sys.path.insert(0, project_root)
    from app.data_models.detection_result import ToxicContentDetectionResult

logger = logging.getLogger(__name__)


class ToxicContentDetector:
    """毒性内容检测服务"""
    
    def __init__(self, openai_api_key: str, model_name: str = "qwen-vl-max-2025-04-08"):  # 默认使用Qwen-VL模型
        dashscope.api_key = openai_api_key
        self.model_name = model_name
        
        # 毒性内容检测的系统提示词
        # 从app/prompts/toxic_content_detection_prompt.txt中读取
        try:
            with open('app/prompts/toxic_content_detection_prompt.txt', 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
        except FileNotFoundError:
            # 当直接运行此文件时，使用相对于当前文件的路径
            import os
            current_dir = os.path.dirname(__file__)
            prompt_path = os.path.join(os.path.dirname(current_dir), 'prompts', 'toxic_content_detection_prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as file:
                self.system_prompt = file.read()
    
    def update_prompt_config(self, parent_json: Dict[str, Any], child_json: Dict[str, Any]):
        """更新系统提示词配置"""
        try:
            # 重新读取原始prompt文件，确保有最新的基础prompt
            try:
                with open('app/prompts/toxic_content_detection_prompt.txt', 'r', encoding='utf-8') as file:
                    base_prompt = file.read()
            except FileNotFoundError:
                import os
                current_dir = os.path.dirname(__file__)
                prompt_path = os.path.join(os.path.dirname(current_dir), 'prompts', 'toxic_content_detection_prompt.txt')
                with open(prompt_path, 'r', encoding='utf-8') as file:
                    base_prompt = file.read()
            
            # 定义标准的毒性内容类别映射
            standard_categories = {
                "骚扰与网络霸凌": ["骚扰", "网络霸凌", "霸凌", "骚扰与网络霸凌"],
                "仇恨言论与身份攻击": ["仇恨言论", "身份攻击", "歧视", "仇恨言论与身份攻击"],
                "威胁与恐吓": ["威胁", "恐吓", "威胁与恐吓"],
                "公开羞辱与诋毁": ["公开羞辱", "诋毁", "人肉搜索", "公开羞辱与诋毁"]
            }
            
            # 将输入的类别映射到标准类别
            mapped_scores = {}
            all_input_categories = set(parent_json.keys()) | set(child_json.keys())
            
            for input_category in all_input_categories:
                parent_score = parent_json.get(input_category, 0)
                child_score = child_json.get(input_category, 0)
                combined_score = (parent_score + child_score) / 2
                
                # 找到匹配的标准类别
                matched = False
                for standard_cat, aliases in standard_categories.items():
                    if any(alias in input_category for alias in aliases) or input_category in aliases:
                        mapped_scores[standard_cat] = max(mapped_scores.get(standard_cat, 0), combined_score)
                        matched = True
                        break
                
                # 如果没有匹配到标准类别，直接使用原类别名
                if not matched:
                    mapped_scores[input_category] = combined_score
            
            # 根据评分生成prompt调整内容
            if mapped_scores:
                base_prompt += "\n\n## 🎯 毒性内容检测关注度配置\n"
                base_prompt += "请根据以下各类毒性内容的关注程度调整检测严格度：\n"
                
                # 按分数排序，高分的优先关注
                sorted_categories = sorted(mapped_scores.items(), key=lambda x: x[1], reverse=True)
                
                high_priority = []  # 4-5分
                medium_priority = []  # 2-3分
                low_priority = []  # 0-1分
                
                for category, score in sorted_categories:
                    if score >= 4:
                        high_priority.append(f"{category}({score:.1f}分)")
                    elif score >= 2:
                        medium_priority.append(f"{category}({score:.1f}分)")
                    else:
                        low_priority.append(f"{category}({score:.1f}分)")
                
                if high_priority:
                    base_prompt += f"\n**🚨 高度关注类别（严格检测）**: {', '.join(high_priority)}"
                    base_prompt += "\n- 对这些类别的内容要特别敏感，即使轻微的倾向也要标记"
                    base_prompt += "\n- 在toxicity_category字段中优先识别这些类别"
                
                if medium_priority:
                    base_prompt += f"\n**⚠️ 中度关注类别（常规检测）**: {', '.join(medium_priority)}"
                    base_prompt += "\n- 对这些类别保持正常的检测标准"
                
                if low_priority:
                    base_prompt += f"\n**📝 低度关注类别（宽松检测）**: {', '.join(low_priority)}"
                    base_prompt += "\n- 对这些类别可以相对宽松，只标记明显的有害内容"
                
                base_prompt += "\n\n**重要**: 在返回的JSON中，toxicity_category字段必须使用以下标准类别名称之一："
                base_prompt += "\n- 骚扰与网络霸凌"
                base_prompt += "\n- 仇恨言论与身份攻击" 
                base_prompt += "\n- 威胁与恐吓"
                base_prompt += "\n- 公开羞辱与诋毁"
                base_prompt += "\n\n**严格要求**: 不允许使用'其他'类别，必须准确归类到上述四个标准类别中的一个。"
                base_prompt += "\n\n请在检测时参考以上关注度设置，调整判断的严格程度。"
            
            # 更新系统提示词
            self.system_prompt = base_prompt
            logger.info(f"毒性内容检测器的系统提示词已更新，处理了{len(mapped_scores)}个类别")
            
        except Exception as e:
            logger.error(f"更新毒性内容检测器提示词失败: {e}")
            raise
    
    async def detect_toxic_content(
        self, 
        content: str, 
        user_id: Optional[str] = None,
        video_frames: Optional[List[str]] = None,
        audio_transcript: Optional[str] = None
    ) -> ToxicContentDetectionResult:
        """检测毒性内容（支持多模态：文本+视频帧+音频转录）"""
        max_tries = 3
        last_error = None
        
        for attempt in range(max_tries):
            try:
                logger.info(f"毒性内容检测尝试 {attempt + 1}/{max_tries}")
                
                # 使用LLM进行详细分析（支持多模态）
                final_result = await self._analyze_content_with_llm_multimodal(
                    content, video_frames, audio_transcript
                )
                        
                # 兼容新旧字段
                has_toxicity = final_result.get("has_toxicity", final_result.get("is_toxic", False))
                
                return ToxicContentDetectionResult(
                    result_id=self._generate_result_id(),
                    content_text=content,
                    is_detected=has_toxicity,
                    confidence_score=final_result.get("confidence", 0.0),
                    reasons=final_result.get("toxic_aspects", final_result.get("reasons", [])),
                    evidence=final_result.get("offensive_words", final_result.get("evidence", [])),
                    user_id=user_id,
                    toxicity_categories=final_result.get("toxicity_categories", {}),
                    severity_level=final_result.get("severity", final_result.get("severity_level", "轻微")),
                    
                    # 新增字段
                    is_toxic_for_elderly=has_toxicity,
                    toxicity_reasons=final_result.get("toxic_aspects", []),
                    toxic_elements=final_result.get("offensive_words", []),
                    detoxified_meaning=final_result.get("clean_version", ""),
                    friendly_alternative=final_result.get("clean_version", ""),
                    elderly_explanation=final_result.get("explanation_for_elderly", ""),
                    toxicity_category=final_result.get("toxicity_category", "其他")
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"毒性内容检测第{attempt + 1}次尝试失败: {e}")
                if attempt < max_tries - 1:
                    await asyncio.sleep(1)  # 短暂等待后重试
                    
        # 所有尝试都失败
        logger.error(f"毒性内容检测失败，已尝试{max_tries}次: {last_error}")
        return self._create_error_result(content, user_id, str(last_error))

    async def _analyze_content_with_llm_multimodal(
        self, 
        content: str, 
        video_frames: Optional[List[str]] = None,
        audio_transcript: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用多模态大模型分析内容"""
        try:
            # 构建多模态user_prompt
            user_prompt_parts = []
            
            # 文本内容部分
            if len(content) > 2000:
                content = content[:2000] + "..."
            user_prompt_parts.append(f"文本内容：\n{content}")
            
            # 音频转录部分
            if audio_transcript:
                if len(audio_transcript) > 1500:
                    audio_transcript = audio_transcript[:1500] + "..."
                user_prompt_parts.append(f"\n音频转录内容：\n{audio_transcript}")
            
            # 视频帧说明
            if video_frames and len(video_frames) > 0:
                user_prompt_parts.append(f"\n视频帧数量：{len(video_frames)}张，请结合图像内容进行分析")
            
            user_prompt = "请分析以下多媒体内容是否包含毒性或有害内容：\n\n" + "\n".join(user_prompt_parts) + "\n\n请严格按照JSON格式返回分析结果。"
            
            # 构建messages
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 准备图像数据
            image_urls = []
            if video_frames:
                frame_count = min(len(video_frames), 5)
                for i, frame_path in enumerate(video_frames[:frame_count]):
                    try:
                        with open(frame_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                            image_urls.append(f"data:image/jpeg;base64,{base64_image}")
                    except Exception as e:
                        logger.warning(f"无法读取视频帧 {frame_path}: {e}")
            
            # 调用Qwen-VL API
            response = await asyncio.to_thread(
                dashscope.MultiModalConversation.call,
                model=self.model_name,
                messages=messages,
                images=image_urls if image_urls else None,
                temperature=0.1,
                max_tokens=1000
            )
            
            if response.status_code != 200:
                if "API" in str(response.message):
                    print("Current API key invalid: ", dashscope.api_key)
                raise Exception(f"API调用失败: {response.message}")
            
            # 修复：处理content可能是list的情况
            content_raw = response.output.choices[0].message.content
            if isinstance(content_raw, list):
                # 如果是list，合并所有文本内容
                result_text = ""
                for item in content_raw:
                    if isinstance(item, dict) and 'text' in item:
                        result_text += item['text']
                    elif isinstance(item, str):
                        result_text += item
                    else:
                        result_text += str(item)
            else:
                # 如果是字符串，直接使用
                result_text = str(content_raw)
            
            result_text = result_text.strip()
            logger.debug(f"LLM原始返回: {result_text}")
            
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
            "has_toxicity": False,
            "confidence": 0.0,
            "toxic_aspects": ["系统无法正常分析内容"],
            "offensive_words": [],
            "severity": "轻微",
            "clean_version": "内容的具体含义暂时无法确定",
            "explanation_for_elderly": "抱歉，系统暂时无法分析这段内容，但这并不意味着内容有问题。建议您可以询问家人或朋友的看法。"
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
        
if __name__ == "__main__":
    # 配置日志输出到文件和控制台
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('toxic_content_test.log', encoding='utf-8'),  # 输出到文件
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
        detector = ToxicContentDetector(openai_api_key)
        
        # 测试多个不同类型的内容，包括老年人可能在网上看到的各种表达
        test_cases = [
            "你是脑子有病是吧，跟你说话真费劲",  # 典型的冒犯性表达
            "今天天气真好，适合出去散步",  # 友善内容
            "这个老不死的怎么还不滚",  # 对老年人的攻击性言论
            "谢谢您的帮助，您真是太好了",  # 礼貌表达
            "妈的，这破手机怎么这么卡",  # 包含粗话的抱怨
            "我觉得你说得不对，我们可以再讨论一下"  # 正常的不同意见表达
        ]
        
        for i, test_content in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"测试案例 {i}: {test_content}")
            print('='*60)
            
            result = await detector.detect_toxic_content(test_content)
    
    asyncio.run(test_detector())