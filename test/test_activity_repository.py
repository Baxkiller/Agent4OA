import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.data_models.activity import Activity
from app.repositories.activity_repository import ActivityRepository
import datetime

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop

@pytest.fixture(scope="module")
async def test_db():
    client = AsyncIOMotorClient("mongodb://localhost:27107")
    db = client["test_db"]
    yield db
    client.drop_database("test_db")
    client.close()

@pytest.mark.asyncio
async def test_activity_crud(test_db):
    repo = ActivityRepository(test_db)
    activity = Activity(action_type="click", position="100,200", UI_element="button", action_time=datetime.datetime.utcnow(), app_name="App", app_package_name="com.app", screenshot_path="/tmp/shot.png")
    # Create
    await repo.create_activity(activity)
    # List
    activities = await repo.list_activities()
    assert len(activities) == 1
    # Update (by _id, get _id from MongoDB)
    doc = await repo.collection.find_one({"action_type": "click"})
    activity_id = doc["_id"]
    await repo.update_activity(activity_id, {"action_type": "swipe"})
    updated = await repo.collection.find_one({"_id": activity_id})
    assert updated["action_type"] == "swipe"
    # Delete
    await repo.delete_activity(activity_id)
    deleted = await repo.collection.find_one({"_id": activity_id})
    assert deleted is None 