import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.data_models.device import Device
from app.repositories.device_repository import DeviceRepository

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
async def test_device_crud(test_db):
    repo = DeviceRepository(test_db)
    device = Device(device_id="d1", device_name="Phone", Android_version="12")
    # Create
    await repo.create_device(device)
    # Read
    fetched = await repo.get_device_by_id("d1")
    assert fetched is not None
    assert fetched.device_name == "Phone"
    # Update
    await repo.update_device("d1", {"device_name": "Tablet"})
    updated = await repo.get_device_by_id("d1")
    assert updated.device_name == "Tablet"
    # List
    devices = await repo.list_devices()
    assert len(devices) == 1
    # Delete
    await repo.delete_device("d1")
    assert await repo.get_device_by_id("d1") is None 