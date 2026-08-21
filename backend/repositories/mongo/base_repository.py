"""Generic MongoDB repository implementing the Repository interface.

Concrete repositories (added in later milestones) subclass this by setting
`collection_name` and `model`. No business logic lives here.
"""
from typing import Generic, List, Optional, Type, TypeVar

from bson import ObjectId

from core.database import get_database
from domain.base import BaseDocument, utcnow_iso
from repositories.interfaces import Repository

T = TypeVar("T", bound=BaseDocument)


class MongoRepository(Repository[T], Generic[T]):
    collection_name: str = ""
    model: Type[T]

    def __init__(self, collection_name: Optional[str] = None, model: Optional[Type[T]] = None):
        if collection_name:
            self.collection_name = collection_name
        if model:
            self.model = model

    @property
    def collection(self):
        return get_database()[self.collection_name]

    @staticmethod
    def _oid(id: str):
        return ObjectId(id) if ObjectId.is_valid(id) else id

    async def create(self, entity: T) -> T:
        doc = entity.to_mongo()
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self.model.from_mongo(doc)

    async def get(self, id: str) -> Optional[T]:
        doc = await self.collection.find_one({"_id": self._oid(id)})
        return self.model.from_mongo(doc) if doc else None

    async def list(self, filters: Optional[dict] = None, limit: int = 100) -> List[T]:
        cursor = self.collection.find(filters or {}).limit(limit)
        return [self.model.from_mongo(d) async for d in cursor]

    async def update(self, id: str, changes: dict) -> Optional[T]:
        changes = {**changes, "updated_at": utcnow_iso()}
        await self.collection.update_one({"_id": self._oid(id)}, {"$set": changes})
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        result = await self.collection.delete_one({"_id": self._oid(id)})
        return result.deleted_count > 0
