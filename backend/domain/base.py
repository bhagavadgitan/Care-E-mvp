"""Base document model + ObjectId handling shared by all domain entities."""
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _validate_object_id(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        return v
    if v is None:
        return v
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[str, BeforeValidator(_validate_object_id)]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseDocument(BaseModel):
    """All persisted entities extend this. Maps Mongo `_id` <-> `id` (str)."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)

    @classmethod
    def from_mongo(cls, doc: Optional[dict]):
        if not doc:
            return None
        return cls(**doc)

    def to_mongo(self, exclude_none: bool = True) -> dict:
        # mode="json" serializes enums to their values and keeps types BSON-safe.
        data = self.model_dump(by_alias=True, exclude_none=exclude_none, mode="json")
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
