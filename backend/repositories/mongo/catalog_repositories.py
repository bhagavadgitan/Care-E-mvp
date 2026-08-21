"""Repositories for the synthetic catalog/inventory/supplier collections."""
from typing import List, Optional

from domain.inventory_models import (
    InventoryItem,
    Product,
    Supplier,
    SupplierAvailability,
)
from repositories.mongo.base_repository import MongoRepository


class ProductRepository(MongoRepository[Product]):
    collection_name = "products"
    model = Product

    async def find_by_sku(self, sku: str) -> Optional[Product]:
        doc = await self.collection.find_one({"sku": sku})
        return Product.from_mongo(doc) if doc else None


class InventoryRepository(MongoRepository[InventoryItem]):
    collection_name = "inventory_items"
    model = InventoryItem

    async def find_one_by(self, facility_id: str, product_id: str) -> Optional[InventoryItem]:
        doc = await self.collection.find_one({"facility_id": facility_id, "product_id": product_id})
        return InventoryItem.from_mongo(doc) if doc else None


class SupplierRepository(MongoRepository[Supplier]):
    collection_name = "suppliers"
    model = Supplier


class SupplierAvailabilityRepository(MongoRepository[SupplierAvailability]):
    collection_name = "supplier_availability"
    model = SupplierAvailability

    async def list_by_product(self, product_id: str) -> List[SupplierAvailability]:
        return await self.list({"product_id": product_id}, limit=200)


product_repository = ProductRepository()
inventory_repository = InventoryRepository()
supplier_repository = SupplierRepository()
supplier_availability_repository = SupplierAvailabilityRepository()
