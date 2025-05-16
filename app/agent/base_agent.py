from typing import Dict, Any, Optional
import openai
from dataclasses import dataclass

@dataclass
class AgentConfig:
    api_key: str
    model_name: str = "gpt-4"
    endpoint: str = "https://api.openai.com/v1"
    system_prompt: str = ""

class BaseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.endpoint
        )
        
    async def _call_llm(self, messages: list[Dict[str, str]]) -> str:
        """Call the LLM with the given messages."""
        response = await self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages
        )
        return response.choices[0].message.content

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process method") 