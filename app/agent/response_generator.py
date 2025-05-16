from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentConfig

class ResponseGenerator(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant that generates responses for elderly users.
        Consider the following when generating responses:
        1. Use clear and simple language
        2. Explain technical terms or internet slang when used
        3. Be patient and supportive
        4. Consider the user's age and background
        5. Provide helpful actions when needed"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_utterance = input_data.get("user_utterance", "")
        memory = input_data.get("memory", {})
        user_age = input_data.get("user_age", 60)  # Default age if not provided

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Generate a response for a {user_age}-year-old user.
            User message: {user_utterance}
            Context from memory: {memory}
            Please provide:
            1. A natural, helpful response
            2. Any necessary actions (click, swipe, etc.)
            3. Explanations for any technical terms used"""}
        ]

        response = await self._call_llm(messages)
        
        # Parse the response into structured format
        return {
            "reply_sentence": self._extract_reply(response),
            "action_list": self._extract_actions(response),
            "explanations": self._extract_explanations(response)
        }

    def _extract_reply(self, response: str) -> str:
        # Implementation to extract the main reply from the response
        return response.split("Actions:")[0].strip()

    def _extract_actions(self, response: str) -> List[Dict[str, str]]:
        # Implementation to extract actions from the response
        actions = []
        if "Actions:" in response:
            action_section = response.split("Actions:")[1].split("Explanations:")[0].strip()
            # Parse action section into structured format
            # Example: [{"type": "click", "target": "button1"}, {"type": "swipe", "direction": "up"}]
        return actions

    def _extract_explanations(self, response: str) -> Dict[str, str]:
        # Implementation to extract explanations of technical terms
        explanations = {}
        if "Explanations:" in response:
            explanation_section = response.split("Explanations:")[1].strip()
            # Parse explanation section into dictionary
            # Example: {"term1": "explanation1", "term2": "explanation2"}
        return explanations 