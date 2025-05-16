import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.data_models.user import User
from app.repositories.user_repository import UserRepository
import datetime

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
async def test_user_crud(test_db):
    repo = UserRepository(test_db)
    user = User(user_id="u1", user_name="Alice", user_gender="F", user_created_at=datetime.datetime.utcnow(), device_id="d1")
    # Create
    await repo.create_user(user)
    # Read
    fetched = await repo.get_user_by_id("u1")
    assert fetched is not None
    assert fetched.user_name == "Alice"
    # Update
    await repo.update_user("u1", {"user_name": "Bob"})
    updated = await repo.get_user_by_id("u1")
    assert updated.user_name == "Bob"
    # List
    users = await repo.list_users()
    assert len(users) == 1
    # Delete
    await repo.delete_user("u1")
    assert await repo.get_user_by_id("u1") is None 