from typing import Dict, Any
from .base_agent import BaseAgent, AgentConfig
import json

class IntentAndContentParserAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant that analyzes user behavior and content.
        You need to determine:
        1. If the user is viewing text/video content
        2. If there are user preferences to store
        3. If there's content being released
        4. If the user needs emotional support
        Provide your analysis in a the following structured json format:
        {
            "scanning_text_or_video": bool, 
            "user_preference": {
                "has_user_preference": bool, 
                "preference_type": str,
                "preference_description": str
            },
            "privacy_content_release": {
                "has_content_release": bool, 
                "need_privacy_reminder": str,
            }
            "emotion_support": {
                "need_emotion_support": bool,
                "emotion_support_prompt_for_response_agent": str
            }
        }
        """

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_utterance = input_data.get("user_utterance", "")
        screenshot = input_data.get("screenshot", None)
        action = input_data.get("action", None)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User utterance: {user_utterance}\nAction: {action}\nScreenshot available: {screenshot is not None}"}
        ]

        analysis_text = await self._call_llm(messages)
        
        try:
            # Parse the initial analysis
            if "```json" in analysis_text:
                json_str = analysis_text.split("```json")[1].split("```")[0].strip()
            elif "```" in analysis_text:
                json_str = analysis_text.split("```")[1].strip()
            else:
                json_str = analysis_text.strip()
                
            analysis = json.loads(json_str)
            
            # Ensure all required fields are present with default values if missing
            if "scanning_text_or_video" not in analysis:
                analysis["scanning_text_or_video"] = False
                
            if "user_preference" not in analysis:
                analysis["user_preference"] = {
                    "has_user_preference": False,
                    "preference_type": "",
                    "preference_description": ""
                }
            elif not isinstance(analysis["user_preference"], dict):
                analysis["user_preference"] = {
                    "has_user_preference": False,
                    "preference_type": "",
                    "preference_description": ""
                }
            else:
                user_pref = analysis["user_preference"]
                if "has_user_preference" not in user_pref:
                    user_pref["has_user_preference"] = False
                if "preference_type" not in user_pref:
                    user_pref["preference_type"] = ""
                if "preference_description" not in user_pref:
                    user_pref["preference_description"] = ""
                
            if "privacy_content_release" not in analysis:
                analysis["privacy_content_release"] = {
                    "has_content_release": False,
                    "need_privacy_reminder": ""
                }
            elif not isinstance(analysis["privacy_content_release"], dict):
                analysis["privacy_content_release"] = {
                    "has_content_release": False,
                    "need_privacy_reminder": ""
                }
            else:
                content_rel = analysis["privacy_content_release"]
                if "has_content_release" not in content_rel:
                    content_rel["has_content_release"] = False
                if "need_privacy_reminder" not in content_rel:
                    content_rel["need_privacy_reminder"] = ""
                
            if "emotion_support" not in analysis:
                analysis["emotion_support"] = {
                    "need_emotion_support": False,
                    "emotion_support_prompt_for_response_agent": ""
                }
            elif not isinstance(analysis["emotion_support"], dict):
                analysis["emotion_support"] = {
                    "need_emotion_support": False,
                    "emotion_support_prompt_for_response_agent": ""
                }
            else:
                emotion = analysis["emotion_support"]
                if "need_emotion_support" not in emotion:
                    emotion["need_emotion_support"] = False
                if "emotion_support_prompt_for_response_agent" not in emotion:
                    emotion["emotion_support_prompt_for_response_agent"] = ""
            
            return analysis
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Fallback to simpler parsing if JSON parsing fails
            return {
                "scanning_text_or_video": "scanning" in analysis_text.lower() or "text" in analysis_text.lower() or "video" in analysis_text.lower(),
                "user_preference": {
                    "has_user_preference": "preference" in analysis_text.lower(),
                    "preference_type": self._extract_preference_type(analysis_text),
                    "preference_description": self._extract_preference_description(analysis_text)
                },
                "privacy_content_release": {
                    "has_content_release": "release" in analysis_text.lower() or "content" in analysis_text.lower(),
                    "need_privacy_reminder": self._extract_content_reminder(analysis_text)
                },
                "emotion_support": {
                    "need_emotion_support": "emotion" in analysis_text.lower() or "support" in analysis_text.lower(),
                    "emotion_support_prompt_for_response_agent": ""
                }
            }

    def _extract_preference_type(self, analysis: str) -> str:
        if "app_usage" in analysis.lower():
            return "app_usage"
        elif "interest" in analysis.lower():
            return "interest"
        else:
            return ""

    def _extract_preference_description(self, analysis: str) -> str:
        lower_analysis = analysis.lower()
        
        if "preference description" in lower_analysis:
            start_idx = lower_analysis.find("preference description") + len("preference description")
            end_idx = lower_analysis.find(".", start_idx)
            if end_idx == -1:
                end_idx = len(analysis)
            return analysis[start_idx:end_idx].strip(': "\'')
        
        return ""

    def _extract_content_reminder(self, analysis: str) -> str:
        lower_analysis = analysis.lower()
        
        if "reminder" in lower_analysis:
            start_idx = lower_analysis.find("reminder") + len("reminder")
            end_idx = lower_analysis.find(".", start_idx)
            if end_idx == -1:
                end_idx = len(analysis)
            return analysis[start_idx:end_idx].strip(': "\'')
        
        return "" 