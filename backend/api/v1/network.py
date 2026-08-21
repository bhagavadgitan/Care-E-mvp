"""M2A read + seed endpoints for the synthetic network (admin-only).

Broad network visibility is an ADMIN capability (M1). Role/organisation-scoped
inventory access for hospital/supplier users is deferred to later milestones.
"""
from typing import Optional

from fastapi import APIRouter, Depends

from core.dependencies import get_admin
from core.exceptions import NotFoundError
from repositories.mongo.catalog_repositories import (
    inventory_repository,
    product_repository,
    supplier_availability_repository,
    supplier_repository,
)
from repositories.mongo.facility_repository import facility_repository
from services import synthetic_seed

router = APIRouter(tags=["synthetic-network"])


def _doc(model) -> dict:
    """Serialize a domain model with clean field names (id, not _id)."""
    return model.model_dump(mode="json")


def _inv_public(item) -> dict:
    return {
        "id": item.id,
        "organisation_id": item.organisation_id,
        "facility_id": item.facility_id,
        "product_id": item.product_id,
        "quantity_on_hand": item.quantity_on_hand,
        "reserved_quantity": item.reserved_quantity,
        "available_quantity": item.quantity_on_hand - item.reserved_quantity,
        "safety_stock": item.safety_stock,
        "expiry_date": item.expiry_date,
        "transfer_permitted": item.transfer_permitted,
    }


@router.get("/catalog/products")
async def list_products(category: Optional[str] = None, admin=Depends(get_admin)):
    query = {"category": category} if category else {}
    items = await product_repository.list(query, limit=500)
    return {"products": [_doc(p) for p in items], "count": len(items)}


@router.get("/catalog/products/{product_id}")
async def get_product(product_id: str, admin=Depends(get_admin)):
    product = await product_repository.get(product_id)
    if not product:
        raise NotFoundError(message="Product not found.")
    return {"product": _doc(product)}


@router.get("/network/facilities")
async def list_facilities(admin=Depends(get_admin)):
    items = await facility_repository.list({"is_synthetic": True}, limit=200)
    return {"facilities": [_doc(f) for f in items], "count": len(items)}


@router.get("/network/inventory")
async def list_inventory(
    facility_id: Optional[str] = None,
    product_id: Optional[str] = None,
    admin=Depends(get_admin),
):
    query = {}
    if facility_id:
        query["facility_id"] = facility_id
    if product_id:
        query["product_id"] = product_id
    items = await inventory_repository.list(query, limit=1000)
    return {"inventory": [_inv_public(i) for i in items], "count": len(items)}


@router.get("/network/suppliers")
async def list_suppliers(admin=Depends(get_admin)):
    items = await supplier_repository.list({}, limit=200)
    return {"suppliers": [_doc(s) for s in items], "count": len(items)}


@router.get("/network/supplier-availability")
async def list_supplier_availability(product_id: Optional[str] = None, admin=Depends(get_admin)):
    query = {"product_id": product_id} if product_id else {}
    items = await supplier_availability_repository.list(query, limit=1000)
    return {"supplier_availability": [_doc(a) for a in items], "count": len(items)}


@router.get("/synthetic/status")
async def synthetic_status(admin=Depends(get_admin)):
    return await synthetic_seed.status()


@router.post("/synthetic/seed")
async def synthetic_seed_endpoint(admin=Depends(get_admin)):
    """Idempotent: seed only if the synthetic network is empty."""
    await synthetic_seed.ensure_seeded()
    return {"status": "ok", "counts": await synthetic_seed.counts()}


@router.post("/synthetic/reset")
async def synthetic_reset_endpoint(admin=Depends(get_admin)):
    """Destructive: wipe synthetic data and regenerate deterministically."""
    counts = await synthetic_seed.seed()
    return {"status": "ok", "counts": counts}
