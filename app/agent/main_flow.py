from typing import Dict, Any
import asyncio
from .intent_content_parser import IntentAndContentParserAgent
from .content_analysis_agents import HarmfulContentDetector, FakeContentDetector, ReminanceContentDetector
from .memory_agent import MemoryAgent
from .response_generator import ResponseGenerator
from .base_agent import AgentConfig

class MainFlow:
    def __init__(self, config: AgentConfig):
        self.config = config
        # Initialize all agents
        self.intent_parser = IntentAndContentParserAgent(config)
        self.harmful_detector = HarmfulContentDetector(config)
        self.fake_detector = FakeContentDetector(config)
        self.reminance_detector = ReminanceContentDetector(config)
        self.memory_agent = MemoryAgent(config)
        self.response_generator = ResponseGenerator(config)

    async def _run_content_analysis(self, content_input: Dict[str, Any]) -> Dict[str, Any]:
        """Run content analysis tasks in parallel."""
        tasks = [
            self.harmful_detector.process(content_input),
            self.fake_detector.process(content_input),
            self.reminance_detector.process(content_input)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        content_analysis_results = {}
        harmful_result, fake_result, reminance_result = results
        
        if not isinstance(harmful_result, Exception):
            content_analysis_results["harmful_content"] = {
                "is_harmful": harmful_result[0],
                "description": harmful_result[1]
            }
        if not isinstance(fake_result, Exception):
            content_analysis_results["fake_content"] = {
                "is_fake": fake_result[0],
                "description": fake_result[1]
            }
        if not isinstance(reminance_result, Exception):
            content_analysis_results["reminiscent_content"] = {
                "is_reminiscent": reminance_result[0],
                "description": reminance_result[1]
            }
            
        return content_analysis_results

    async def _run_memory_and_response(self, input_data: Dict[str, Any], intent_analysis: Dict[str, Any], content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Run memory and response tasks in sequence."""
        # First get memory
        memory_result = await self.memory_agent.process({
            "user_utterance": input_data.get("user_utterance", ""),
            "user_preference": intent_analysis.get("user_preference", {}),
            "context": intent_analysis
        })
        
        if isinstance(memory_result, Exception):
            memory_result = {"memory": None, "error": str(memory_result)}
        
        # Then generate response
        response = await self.response_generator.process({
            "user_utterance": input_data.get("user_utterance", ""),
            "memory": memory_result.get("memory"),
            "intent_analysis": intent_analysis,
            "content_analysis": content_analysis,
            "user_age": input_data.get("user_age", 60)
        })
        
        return {
            "memory": memory_result.get("memory"),
            "response": response
        }

    async def process_user_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Step 1: Get initial intent analysis
        intent_analysis = await self.intent_parser.process(input_data)
        
        # Step 2: Create tasks for parallel processing
        tasks = []
        
        # Content analysis task (if needed)
        if intent_analysis.get("scanning_text_or_video", False):
            content_input = {
                "content": input_data.get("user_utterance", ""),
                "screenshot": input_data.get("screenshot", None),
                "user_age": input_data.get("user_age", 60)
            }
            content_analysis_task = self._run_content_analysis(content_input)
            tasks.append(content_analysis_task)
        else:
            content_analysis_task = asyncio.create_task(asyncio.sleep(0))  # Empty task
            tasks.append(content_analysis_task)
        
        # Memory and response task
        memory_response_task = self._run_memory_and_response(
            input_data, 
            intent_analysis,
            {}  # Empty content analysis for now
        )
        tasks.append(memory_response_task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        content_analysis_results = results[0] if not isinstance(results[0], Exception) else {}
        memory_response_results = results[1] if not isinstance(results[1], Exception) else {"memory": None, "response": None}
        
        # Combine all results
        return {
            "intent_analysis": intent_analysis,
            "content_analysis": content_analysis_results,
            "memory": memory_response_results.get("memory"),
            "response": memory_response_results.get("response"),
            "privacy_reminder": intent_analysis.get("privacy_content_release", {}).get("need_privacy_reminder", ""),
            "emotion_support": intent_analysis.get("emotion_support", {})
        } 