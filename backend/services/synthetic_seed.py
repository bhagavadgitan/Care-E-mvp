"""Deterministic, idempotent synthetic network seeding (M2A).

Reproducible (fixed RNG seed). Seeding wipes only synthetic-tagged data and the
fully-synthetic catalog collections, then regenerates — so it never creates
uncontrolled duplicates and never touches M1 user-registered organisations.
"""
import random
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.database import get_database
from core.logging_config import get_logger
from domain.inventory_models import (
    InventoryItem,
    Product,
    Supplier,
    SupplierAvailability,
    StorageCondition,
)
from domain.models import ApprovalStatus, Organisation, OrganisationType
from repositories.mongo.catalog_repositories import (
    inventory_repository,
    product_repository,
    supplier_availability_repository,
    supplier_repository,
)
from repositories.mongo.facility_repository import facility_repository
from repositories.mongo.organisation_repository import organisation_repository

logger = get_logger("care_e.seed")

SEED = 42
FACILITY_CODES = ["HOSP-A", "HOSP-B", "HOSP-C", "HOSP-D", "HOSP-E"]
FACILITY_NAMES = ["Hospital A", "Hospital B", "Hospital C", "Hospital D", "Hospital E"]
GLOVES_SKU = "SKU-0001"

# (display category, storage condition, unit)
CATEGORIES = [
    ("Gloves", StorageCondition.AMBIENT, "box"),
    ("Syringes", StorageCondition.AMBIENT, "unit"),
    ("IV Sets", StorageCondition.AMBIENT, "unit"),
    ("Masks", StorageCondition.AMBIENT, "box"),
    ("Dressings", StorageCondition.AMBIENT, "unit"),
    ("Catheters", StorageCondition.AMBIENT, "unit"),
    ("Surgical Consumables", StorageCondition.AMBIENT, "unit"),
    ("Sutures", StorageCondition.AMBIENT, "unit"),
    ("Cold-Chain Reagents", StorageCondition.COLD, "vial"),
]


def _iso_in_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


async def _counts() -> dict:
    db = get_database()
    return {
        "facilities": await db["facilities"].count_documents({"is_synthetic": True}),
        "products": await db["products"].count_documents({}),
        "inventory": await db["inventory_items"].count_documents({}),
        "suppliers": await db["suppliers"].count_documents({}),
        "supplier_availability": await db["supplier_availability"].count_documents({}),
    }


async def _reset() -> None:
    db = get_database()
    await db["products"].delete_many({})
    await db["inventory_items"].delete_many({})
    await db["suppliers"].delete_many({})
    await db["supplier_availability"].delete_many({})
    await db["facilities"].delete_many({"is_synthetic": True})
    await db["organisations"].delete_many({"is_synthetic": True})


async def seed() -> dict:
    """Reset + regenerate the synthetic network. Idempotent (stable counts)."""
    if settings.DATA_MODE != "SYNTHETIC":
        raise RuntimeError("Seeding/reset is only permitted in SYNTHETIC data mode.")
    rng = random.Random(SEED)
    await _reset()

    # --- Hospital organisation + 5 facilities ---
    hospital_org = await organisation_repository.create(
        Organisation(
            name="CARE-E Synthetic Health Network (DEMO)",
            organisation_type=OrganisationType.HOSPITAL,
            approval_status=ApprovalStatus.APPROVED,
            is_synthetic=True,
        )
    )
    facility_ids = []
    for code, name in zip(FACILITY_CODES, FACILITY_NAMES):
        fac = await facility_repository.create(_facility(hospital_org.id, code, name))
        facility_ids.append(fac.id)
    fac_by_code = dict(zip(FACILITY_CODES, facility_ids))

    # --- 100 products (index 0 = canonical Surgical Gloves) ---
    products = [
        Product(
            sku=GLOVES_SKU,
            name="Surgical Gloves",
            category="Gloves",
            specification="Sterile, latex-free (DEMO)",
            unit="box",
            storage_condition=StorageCondition.AMBIENT,
        )
    ]
    for i in range(1, 100):
        cat, storage, unit = CATEGORIES[i % len(CATEGORIES)]
        products.append(
            Product(
                sku=f"SKU-{i + 1:04d}",
                name=f"{cat} Type {i}",
                category=cat,
                specification="Synthetic demonstration item",
                unit=unit,
                storage_condition=storage,
            )
        )
    product_docs = [p.to_mongo() for p in products]
    res = await product_repository.collection.insert_many(product_docs)
    product_ids = [str(_id) for _id in res.inserted_ids]  # index-aligned with `products`
    gloves_id = product_ids[0]

    # --- Inventory: canonical gloves records (A,B,C,D,E) + random non-gloves ---
    inv_docs = []

    def inv(fac_code, on_hand, reserved, safety, transfer, expiry_days, product_id=gloves_id):
        return InventoryItem(
            organisation_id=hospital_org.id,
            facility_id=fac_by_code[fac_code],
            product_id=product_id,
            quantity_on_hand=on_hand,
            reserved_quantity=reserved,
            safety_stock=safety,
            expiry_date=_iso_in_days(expiry_days),
            transfer_permitted=transfer,
        ).to_mongo()

    # Canonical scenario (Surgical Gloves):
    inv_docs.append(inv("HOSP-A", 1500, 300, 300, True, 400))   # feasible internal candidate (avail 1200)
    inv_docs.append(inv("HOSP-B", 200, 0, 100, True, 400))      # insufficient quantity (avail 200)
    inv_docs.append(inv("HOSP-C", 100, 100, 200, True, 400))    # requester, depleted (avail 0)
    inv_docs.append(inv("HOSP-D", 1000, 0, 900, True, 400))     # safety-stock violation (1000-800 < 900)
    inv_docs.append(inv("HOSP-E", 1500, 0, 300, False, 400))    # transfer not permitted

    # Random non-gloves inventory: every (product[1:], facility) pair = 99 * 5 = 495 -> total 500.
    for pid in product_ids[1:]:
        for fac_code in FACILITY_CODES:
            on_hand = rng.randint(0, 2000)
            reserved = rng.randint(0, on_hand)
            safety = rng.randint(0, 300)
            transfer = rng.random() < 0.8
            expiry_days = rng.choice([10, 20, 45, 120, 365, 700])
            inv_docs.append(inv(fac_code, on_hand, reserved, safety, transfer, expiry_days, product_id=pid))

    await inventory_repository.collection.insert_many(inv_docs)

    # --- 20 suppliers + availability ---
    supplier_ids = []
    for n in range(1, 21):
        sup_org = await organisation_repository.create(
            Organisation(
                name=f"Supplier {n:02d} (DEMO)",
                organisation_type=OrganisationType.SUPPLIER,
                approval_status=ApprovalStatus.APPROVED,
                is_synthetic=True,
            )
        )
        sup = await supplier_repository.create(
            Supplier(organisation_id=sup_org.id, name=f"Supplier {n:02d} (DEMO)")
        )
        supplier_ids.append(sup.id)

    avail_docs = []
    # Canonical supplier options for gloves (different cost/time trade-offs).
    avail_docs.append(
        SupplierAvailability(supplier_id=supplier_ids[0], product_id=gloves_id,
                             available_quantity=2000, unit_cost=1.20, lead_time_hours=6).to_mongo()
    )
    avail_docs.append(
        SupplierAvailability(supplier_id=supplier_ids[1], product_id=gloves_id,
                             available_quantity=1500, unit_cost=0.85, lead_time_hours=24).to_mongo()
    )
    # Random availability for remaining suppliers.
    for sid in supplier_ids:
        for pid in rng.sample(product_ids, k=rng.randint(5, 15)):
            avail_docs.append(
                SupplierAvailability(
                    supplier_id=sid,
                    product_id=pid,
                    available_quantity=rng.randint(100, 5000),
                    unit_cost=round(rng.uniform(0.3, 25.0), 2),
                    lead_time_hours=rng.choice([6, 12, 24, 48, 72]),
                ).to_mongo()
            )
    await supplier_availability_repository.collection.insert_many(avail_docs)

    counts = await _counts()
    logger.info("Synthetic network seeded: %s", counts)
    return counts


def _facility(org_id, code, name):
    from domain.models import Facility

    return Facility(
        organisation_id=org_id,
        name=f"{name} (DEMO)",
        code=code,
        facility_type="HOSPITAL",
        location="Synthetic Region",
        is_synthetic=True,
    )


async def ensure_seeded() -> None:
    """Seed on startup only if the synthetic network is empty."""
    if await get_database()["products"].count_documents({}) == 0:
        await seed()


async def counts() -> dict:
    return await _counts()


async def status() -> dict:
    """Data-inspection helper (NOT the resolution engine): echo canonical values."""
    db = get_database()
    counts = await _counts()
    gloves = await db["products"].find_one({"sku": GLOVES_SKU})
    canonical = None
    if gloves:
        pid = str(gloves["_id"])
        facs = {}
        async for f in db["facilities"].find({"is_synthetic": True}):
            facs[f.get("code")] = f

        async def candidate(code):
            fac = facs.get(code)
            if not fac:
                return None
            doc = await db["inventory_items"].find_one({"facility_id": str(fac["_id"]), "product_id": pid})
            if not doc:
                return None
            return {
                "facility": code,
                "quantity_on_hand": doc["quantity_on_hand"],
                "reserved_quantity": doc["reserved_quantity"],
                "available_quantity": doc["quantity_on_hand"] - doc["reserved_quantity"],
                "safety_stock": doc["safety_stock"],
                "transfer_permitted": doc["transfer_permitted"],
                "expiry_date": doc.get("expiry_date"),
            }

        supplier_options = []
        async for a in (
            db["supplier_availability"]
            .find({"product_id": pid})
            .sort([("lead_time_hours", 1), ("unit_cost", 1)])
            .limit(5)
        ):
            supplier_options.append(
                {
                    "supplier_id": a["supplier_id"],
                    "available_quantity": a["available_quantity"],
                    "unit_cost": a["unit_cost"],
                    "lead_time_hours": a["lead_time_hours"],
                }
            )

        canonical = {
            "product": gloves["name"],
            "product_sku": GLOVES_SKU,
            "required_quantity": 800,
            "required_within_hours": 12,
            "requesting_facility": "HOSP-C",
            "candidates": {c: await candidate(c) for c in ["HOSP-A", "HOSP-B", "HOSP-D", "HOSP-E"]},
            "supplier_options": supplier_options,
        }

    return {"data_mode": "SYNTHETIC", "counts": counts, "canonical_scenario": canonical}
