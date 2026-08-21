"""Facility repository (MongoDB)."""
from typing import List

from domain.models import Facility
from repositories.mongo.base_repository import MongoRepository


class FacilityRepository(MongoRepository[Facility]):
    collection_name = "facilities"
    model = Facility

    async def list_by_org(self, organisation_id: str, limit: int = 200) -> List[Facility]:
        return await self.list({"organisation_id": organisation_id}, limit=limit)


facility_repository = FacilityRepository()
