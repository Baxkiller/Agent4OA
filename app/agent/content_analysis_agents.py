from typing import Dict, Any, Tuple
from .base_agent import BaseAgent, AgentConfig

class HarmfulContentDetector(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant specialized in detecting harmful content.
        Analyze the given content and determine if it contains:
        1. Violence or graphic content
        2. Hate speech or discrimination
        3. Adult or inappropriate content
        4. Self-harm or dangerous content
        Return your analysis in the following format:
        {
            "is_harmful": bool,
            "harm_type": str,  # One of: "violence", "hate_speech", "adult", "self_harm", "none"
            "description": str  # Detailed explanation of why the content is harmful
        }"""

    async def process(self, input_data: Dict[str, Any]) -> Tuple[bool, str]:
        content = input_data.get("content", "")
        screenshot = input_data.get("screenshot", None)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Content to analyze: {content}\nScreenshot available: {screenshot is not None}"}
        ]

        analysis = await self._call_llm(messages)
        try:
            result = eval(analysis)  # Simple parsing for demonstration
            return result["is_harmful"], result["description"]
        except:
            return False, "Unable to analyze content"

class FakeContentDetector(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant specialized in detecting fake or misleading content.
        Analyze the given content and determine if it contains:
        1. Misinformation or fake news
        2. Misleading claims
        3. Outdated information
        4. Manipulated media
        Return your analysis in the following format:
        {
            "is_fake": bool,
            "fake_type": str,  # One of: "misinformation", "misleading", "outdated", "manipulated", "none"
            "description": str  # Detailed explanation of why the content is fake
        }"""

    async def process(self, input_data: Dict[str, Any]) -> Tuple[bool, str]:
        content = input_data.get("content", "")
        screenshot = input_data.get("screenshot", None)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Content to analyze: {content}\nScreenshot available: {screenshot is not None}"}
        ]

        analysis = await self._call_llm(messages)
        try:
            result = eval(analysis)  # Simple parsing for demonstration
            return result["is_fake"], result["description"]
        except:
            return False, "Unable to analyze content"

class ReminanceContentDetector(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant specialized in detecting content that might trigger reminiscence.
        Analyze the given content and determine if it contains:
        1. Historical events or periods
        2. Cultural references from the past
        3. Personal memories or experiences
        4. Nostalgic elements
        Return your analysis in the following format:
        {
            "is_reminiscent": bool,
            "reminiscence_type": str,  # One of: "historical", "cultural", "personal", "nostalgic", "none"
            "description": str  # Detailed explanation of why the content might trigger reminiscence
        }"""

    async def process(self, input_data: Dict[str, Any]) -> Tuple[bool, str]:
        content = input_data.get("content", "")
        screenshot = input_data.get("screenshot", None)
        user_age = input_data.get("user_age", 60)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Content to analyze: {content}\nScreenshot available: {screenshot is not None}\nUser age: {user_age}"}
        ]

        analysis = await self._call_llm(messages)
        try:
            result = eval(analysis)  # Simple parsing for demonstration
            return result["is_reminiscent"], result["description"]
        except:
            return False, "Unable to analyze content" 