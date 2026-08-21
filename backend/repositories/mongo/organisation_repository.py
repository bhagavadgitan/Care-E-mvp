"""Organisation repository (MongoDB)."""
from typing import List, Optional

from domain.models import Organisation
from repositories.mongo.base_repository import MongoRepository


class OrganisationRepository(MongoRepository[Organisation]):
    collection_name = "organisations"
    model = Organisation

    async def list_by_status(self, status: Optional[str] = None, limit: int = 200) -> List[Organisation]:
        query = {"approval_status": status} if status else {}
        return await self.list(query, limit=limit)


organisation_repository = OrganisationRepository()
