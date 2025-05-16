from motor.motor_asyncio import AsyncIOMotorDatabase
from app.data_models.user import User
from typing import Optional, List

class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]

    async def create_user(self, user: User):
        await self.collection.insert_one(user.dict())

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        data = await self.collection.find_one({"user_id": user_id})
        return User(**data) if data else None

    async def list_users(self) -> List[User]:
        users = []
        async for doc in self.collection.find():
            users.append(User(**doc))
        return users

    async def update_user(self, user_id: str, update_data: dict):
        await self.collection.update_one({"user_id": user_id}, {"$set": update_data})

    async def delete_user(self, user_id: str):
        await self.collection.delete_one({"user_id": user_id}) 