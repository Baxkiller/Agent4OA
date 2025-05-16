from motor.motor_asyncio import AsyncIOMotorDatabase
from app.data_models.device import Device
from typing import Optional, List

class DeviceRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["devices"]

    async def create_device(self, device: Device):
        await self.collection.insert_one(device.dict())

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        data = await self.collection.find_one({"device_id": device_id})
        return Device(**data) if data else None

    async def list_devices(self) -> List[Device]:
        devices = []
        async for doc in self.collection.find():
            devices.append(Device(**doc))
        return devices

    async def update_device(self, device_id: str, update_data: dict):
        await self.collection.update_one({"device_id": device_id}, {"$set": update_data})

    async def delete_device(self, device_id: str):
        await self.collection.delete_one({"device_id": device_id}) 