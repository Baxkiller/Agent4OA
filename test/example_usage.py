import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.data_models.user import User
from app.data_models.device import Device
from app.data_models.activity import Activity
from app.data_models.preference import Preference
from app.data_models.conversation import Conversation
from app.data_models.model_response import ModelResponse
from app.repositories.user_repository import UserRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.activity_repository import ActivityRepository
from app.repositories.preference_repository import PreferenceRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.model_response_repository import ModelResponseRepository
import datetime
import pytest

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    # 判断数据库是否存在
    # if "example_db" not in await client.list_database_names():
    #     client.drop_database("example_db")
    #     raise Exception("数据库不存在")
    db = client["example_db"]

    # User
    user_repo = UserRepository(db)
    user = User(user_id="u2", user_name="Tom", user_gender="M", user_created_at=datetime.datetime.utcnow(), device_id="d2")
    await user_repo.create_user(user)
    print(await user_repo.get_user_by_id("u2"))
    await user_repo.update_user("u2", {"user_name": "Jerry"})
    print(await user_repo.list_users())
    await user_repo.delete_user("u2")

    # Device
    device_repo = DeviceRepository(db)
    device = Device(device_id="d2", device_name="Honor 80", Android_version="13")
    await device_repo.create_device(device)
    print(await device_repo.get_device_by_id("d2"))
    await device_repo.update_device("d2", {"device_name": "Honor 80 Pro"})
    print(await device_repo.list_devices())
    await device_repo.delete_device("d2")

    # Activity
    activity_repo = ActivityRepository(db)
    activity = Activity(device_id="d2", action_type="tap", position="50,50", UI_element="input", action_time=datetime.datetime.utcnow(), app_name="DemoApp", app_package_name="com.demo", screenshot_path="/tmp/demo.png")
    await activity_repo.create_activity(activity)
    activities = await activity_repo.list_activities()
    print(activities)
    if activities:
        activity_id = (await activity_repo.collection.find_one({"action_type": "tap"}))["_id"]
        await activity_repo.update_activity(activity_id, {"action_type": "long_press"})
        print(await activity_repo.collection.find_one({"_id": activity_id}))
        await activity_repo.delete_activity(activity_id)

    # Preference
    preference_repo = PreferenceRepository(db)
    preference = Preference(user_id="u1", preference_type="app_usage", preference_value="WeChat")
    await preference_repo.create_preference(preference)
    preferences = await preference_repo.list_preferences()
    assert len(preferences) == 1
    doc = preferences[0]
    preference_id = doc["_id"]
    await preference_repo.update_preference(preference_id, {"preference_value": "Alipay"})
    updated = await preference_repo.collection.find_one({"_id": preference_id})
    assert updated["preference_value"] == "Alipay"
    print(await preference_repo.list_preferences())
    await preference_repo.delete_preference(preference_id)
    deleted = await preference_repo.collection.find_one({"_id": preference_id})
    assert deleted is None

    # Conversation
    conversation_repo = ConversationRepository(db)
    conversation = Conversation(user_id="u1", session_id="s1", speaker="user", message="Hello", created_at=datetime.datetime.utcnow())
    await conversation_repo.create_conversation(conversation)
    conversations = await conversation_repo.list_conversations()
    assert len(conversations) == 1
    doc = conversations[0]
    conversation_id = doc["_id"]
    await conversation_repo.update_conversation(conversation_id, {"message": "Hi"})
    updated = await conversation_repo.collection.find_one({"_id": conversation_id})
    assert updated["message"] == "Hi"
    conversation2 = Conversation(user_id="u1", session_id="s1", speaker="assistant", message="Hello, I'm your assistant", created_at=datetime.datetime.utcnow())
    await conversation_repo.create_conversation(conversation2)
    
    print(await conversation_repo.list_conversations())
    await conversation_repo.delete_conversation(conversation_id)
    deleted = await conversation_repo.collection.find_one({"_id": conversation_id})
    assert deleted is None

    # ModelResponse
    model_response_repo = ModelResponseRepository(db)
    model_response = ModelResponse(agent_id="a1", agent_content="response", to_user_id="u1", created_at=datetime.datetime.utcnow())
    await model_response_repo.create_model_response(model_response)
    responses = await model_response_repo.list_model_responses()
    assert len(responses) == 1
    doc = responses[0]
    response_id = doc["_id"]
    await model_response_repo.update_model_response(response_id, {"agent_content": "new response"})
    updated = await model_response_repo.collection.find_one({"_id": response_id})
    assert updated["agent_content"] == "new response"
    model_response2 = ModelResponse(agent_id="global", agent_content="Hello, I'm your assistant", to_user_id="u1", created_at=datetime.datetime.utcnow())
    model_response_repo.create_model_response(model_response2)
    print(await model_response_repo.list_model_responses())
    await model_response_repo.delete_model_response(response_id)
    deleted = await model_response_repo.collection.find_one({"_id": response_id})
    assert deleted is None

    client.drop_database("example_db")
    client.close()

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop

@pytest.fixture(scope="module")
async def test_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_db"]
    yield db
    client.drop_database("test_db")
    client.close()

@pytest.mark.asyncio
async def test_preference_crud(test_db):
    repo = PreferenceRepository(test_db)
    preference = Preference(user_id="u1", preference_type="app_usage", preference_value="WeChat")
    # Create
    await repo.create_preference(preference)
    # List
    preferences = await repo.list_preferences()
    assert len(preferences) == 1
    doc = preferences[0]
    preference_id = doc["_id"]
    # Update
    await repo.update_preference(preference_id, {"preference_value": "Alipay"})
    updated = await repo.collection.find_one({"_id": preference_id})
    assert updated["preference_value"] == "Alipay"
    # Delete
    await repo.delete_preference(preference_id)
    deleted = await repo.collection.find_one({"_id": preference_id})
    assert deleted is None

@pytest.mark.asyncio
async def test_conversation_crud(test_db):
    repo = ConversationRepository(test_db)
    conversation = Conversation(user_id="u1", session_id="s1", speaker="user", message="Hello", created_at=datetime.datetime.utcnow())
    # Create
    await repo.create_conversation(conversation)
    # List
    conversations = await repo.list_conversations()
    assert len(conversations) == 1
    doc = conversations[0]
    conversation_id = doc["_id"]
    # Update
    await repo.update_conversation(conversation_id, {"message": "Hi"})
    updated = await repo.collection.find_one({"_id": conversation_id})
    assert updated["message"] == "Hi"
    # Delete
    await repo.delete_conversation(conversation_id)
    deleted = await repo.collection.find_one({"_id": conversation_id})
    assert deleted is None

@pytest.mark.asyncio
async def test_model_response_crud(test_db):
    repo = ModelResponseRepository(test_db)
    model_response = ModelResponse(agent_id="a1", agent_content="response", to_user_id="u1", created_at=datetime.datetime.utcnow())
    # Create
    await repo.create_model_response(model_response)
    # List
    responses = await repo.list_model_responses()
    assert len(responses) == 1
    doc = responses[0]
    response_id = doc["_id"]
    # Update
    await repo.update_model_response(response_id, {"agent_content": "new response"})
    updated = await repo.collection.find_one({"_id": response_id})
    assert updated["agent_content"] == "new response"
    # Delete
    await repo.delete_model_response(response_id)
    deleted = await repo.collection.find_one({"_id": response_id})
    assert deleted is None

if __name__ == "__main__":
    asyncio.run(main()) 