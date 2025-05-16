from app.data_models.conversation import Conversation
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

class ConversationRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["conversations"]

    async def create_conversation(self, conversation: Conversation):
        return await self.collection.insert_one(conversation.dict())

    async def list_conversations(self) -> List[dict]:
        return await self.collection.find().to_list(length=100)

    async def update_conversation(self, conversation_id, update_data: dict):
        return await self.collection.update_one({"_id": ObjectId(conversation_id)}, {"$set": update_data})

    async def delete_conversation(self, conversation_id):
        return await self.collection.delete_one({"_id": ObjectId(conversation_id)}) 