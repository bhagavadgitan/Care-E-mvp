"""Unit tests for the domain base document + ObjectId handling."""
from bson import ObjectId

from domain.base import BaseDocument, PyObjectId
from pydantic import BaseModel


class _Sample(BaseDocument):
    name: str


def test_to_mongo_drops_none_id():
    doc = _Sample(name="alpha").to_mongo()
    assert "_id" not in doc
    assert doc["name"] == "alpha"
    assert "created_at" in doc and "updated_at" in doc


def test_from_mongo_maps_object_id_to_str_id():
    oid = ObjectId()
    entity = _Sample.from_mongo({"_id": oid, "name": "beta"})
    assert entity is not None
    assert entity.id == str(oid)
    assert isinstance(entity.id, str)


def test_from_mongo_none_returns_none():
    assert _Sample.from_mongo(None) is None


def test_pyobjectid_coerces_objectid():
    class _M(BaseModel):
        ref: PyObjectId

    oid = ObjectId()
    assert _M(ref=oid).ref == str(oid)
