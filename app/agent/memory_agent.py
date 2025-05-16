from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent, AgentConfig

class MemoryAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = """You are an AI assistant that manages user memory and preferences.
        You need to:
        1. Maintain conversation history
        2. Store and retrieve user preferences
        3. Generate summaries of conversations
        4. Provide relevant context for responses"""
        self.conversation_history: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.conversation_count = 0

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = input_data.get("user_id")
        current_message = input_data.get("message")
        preference_info = input_data.get("preference_info")

        # Add current message to conversation history
        self.conversation_history.append({
            "user_id": user_id,
            "message": current_message,
            "timestamp": datetime.now().isoformat()
        })
        self.conversation_count += 1

        # Store preference if provided
        if preference_info and preference_info.get("has_user_preference"):
            self._store_preference(user_id, preference_info)

        # Generate summary if needed
        if self.conversation_count >= 10:
            summary = await self._generate_summary()
            self.conversation_history = []  # Clear history after summary
            self.conversation_count = 0
        else:
            summary = None

        # Retrieve relevant memory
        relevant_memory = await self._retrieve_relevant_memory(user_id, current_message)

        return {
            "conversation_summary": summary,
            "relevant_memory": relevant_memory,
            "preferences": self._get_user_preferences(user_id)
        }

    def _store_preference(self, user_id: str, preference_info: Dict[str, Any]):
        pref_type = preference_info["preference_type"]
        pref_desc = preference_info["preference_description"]
        
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        
        self.preferences[user_id][pref_type] = {
            "description": pref_desc,
            "timestamp": datetime.now().isoformat()
        }

    async def _generate_summary(self) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Please summarize the following conversation history: {self.conversation_history}"}
        ]
        return await self._call_llm(messages)

    async def _retrieve_relevant_memory(self, user_id: str, current_message: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Given the current message: {current_message}, retrieve relevant information from: {self.conversation_history}"}
        ]
        relevant_info = await self._call_llm(messages)
        return {"relevant_info": relevant_info}

    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        return self.preferences.get(user_id, {}) 