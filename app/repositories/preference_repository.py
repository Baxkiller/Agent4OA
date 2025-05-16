from app.data_models.preference import Preference
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

class PreferenceRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["preferences"]

    async def create_preference(self, preference: Preference):
        return await self.collection.insert_one(preference.dict())

    async def list_preferences(self) -> List[dict]:
        return await self.collection.find().to_list(length=100)

    async def update_preference(self, preference_id, update_data: dict):
        return await self.collection.update_one({"_id": ObjectId(preference_id)}, {"$set": update_data})

    async def delete_preference(self, preference_id):
        return await self.collection.delete_one({"_id": ObjectId(preference_id)}) 