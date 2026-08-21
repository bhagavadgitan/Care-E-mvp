"""M2A catalog / inventory / supplier domain models (synthetic network)."""
from enum import Enum
from typing import Optional

from domain.base import BaseDocument


class StorageCondition(str, Enum):
    AMBIENT = "AMBIENT"
    COLD = "COLD"
    FROZEN = "FROZEN"
    CONTROLLED = "CONTROLLED"


class Product(BaseDocument):
    sku: str
    name: str
    category: str
    specification: Optional[str] = None
    unit: str = "unit"
    storage_condition: StorageCondition = StorageCondition.AMBIENT
    status: str = "ACTIVE"


class InventoryItem(BaseDocument):
    organisation_id: str
    facility_id: str
    product_id: str
    quantity_on_hand: int = 0
    reserved_quantity: int = 0
    safety_stock: int = 0
    expiry_date: Optional[str] = None
    transfer_permitted: bool = True
    # available_quantity is DERIVED (quantity_on_hand - reserved_quantity), never persisted.


class Supplier(BaseDocument):
    organisation_id: str
    name: str
    status: str = "ACTIVE"


class SupplierAvailability(BaseDocument):
    supplier_id: str
    product_id: str
    available_quantity: int = 0
    unit_cost: float = 0.0
    lead_time_hours: int = 24
    status: str = "ACTIVE"
