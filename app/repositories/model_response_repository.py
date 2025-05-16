from app.data_models.model_response import ModelResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

class ModelResponseRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["model_responses"]

    async def create_model_response(self, model_response: ModelResponse):
        return await self.collection.insert_one(model_response.dict())

    async def list_model_responses(self) -> List[dict]:
        return await self.collection.find().to_list(length=100)

    async def update_model_response(self, response_id, update_data: dict):
        return await self.collection.update_one({"_id": ObjectId(response_id)}, {"$set": update_data})

    async def delete_model_response(self, response_id):
        return await self.collection.delete_one({"_id": ObjectId(response_id)}) 