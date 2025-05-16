from motor.motor_asyncio import AsyncIOMotorDatabase
from app.data_models.activity import Activity
from typing import Optional, List

class ActivityRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["activities"]

    async def create_activity(self, activity: Activity):
        await self.collection.insert_one(activity.dict())

    async def get_activity_by_id(self, activity_id: str) -> Optional[Activity]:
        data = await self.collection.find_one({"_id": activity_id})
        return Activity(**data) if data else None

    async def list_activities(self) -> List[Activity]:
        activities = []
        async for doc in self.collection.find():
            activities.append(Activity(**doc))
        return activities

    async def update_activity(self, activity_id: str, update_data: dict):
        await self.collection.update_one({"_id": activity_id}, {"$set": update_data})

    async def delete_activity(self, activity_id: str):
        await self.collection.delete_one({"_id": activity_id}) 