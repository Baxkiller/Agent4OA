import asyncio
from app.agent.main_flow import MainFlow
from app.agent.base_agent import AgentConfig

async def test_agent_flow():
    # Initialize configuration
    config = AgentConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000
    )
    
    # Initialize main flow
    main_flow = MainFlow(config)
    
    # Test case 1: User reading news with modern terms
    print("\nTest Case 1: User reading news with modern terms")
    result1 = await main_flow.process_user_input({
        "user_utterance": "I'm reading an article about cryptocurrency and NFTs. It's quite interesting!",
        "user_age": 65,
        "action": "reading"
    })
    print("Intent Analysis:", result1["intent_analysis"])
    print("Content Analysis:", result1["content_analysis"])
    print("Memory:", result1["memory"])
    print("Response:", result1["response"])
    
    # Test case 2: User trying to share personal information
    print("\nTest Case 2: User trying to share personal information")
    result2 = await main_flow.process_user_input({
        "user_utterance": "I want to share my bank account number 1234567890 with my friend.",
        "user_age": 70,
        "action": "typing"
    })
    print("Intent Analysis:", result2["intent_analysis"])
    print("Privacy Reminder:", result2["privacy_reminder"])
    print("Response:", result2["response"])
    
    # Test case 3: User showing emotional distress
    print("\nTest Case 3: User showing emotional distress")
    result3 = await main_flow.process_user_input({
        "user_utterance": "I'm feeling very lonely today. My children haven't called in weeks.",
        "user_age": 75,
        "action": "speaking"
    })
    print("Intent Analysis:", result3["intent_analysis"])
    print("Emotion Support:", result3["emotion_support"])
    print("Response:", result3["response"])

if __name__ == "__main__":
    asyncio.run(test_agent_flow()) 