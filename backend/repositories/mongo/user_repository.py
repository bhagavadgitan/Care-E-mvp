"""User repository (MongoDB)."""
from typing import Optional

from domain.models import User
from repositories.mongo.base_repository import MongoRepository


class UserRepository(MongoRepository[User]):
    collection_name = "users"
    model = User

    async def find_by_email(self, email: str) -> Optional[User]:
        doc = await self.collection.find_one({"email": email.lower()})
        return User.from_mongo(doc) if doc else None


user_repository = UserRepository()
