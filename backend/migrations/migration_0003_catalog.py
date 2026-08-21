"""M2A catalog/inventory/supplier indexes."""

VERSION = 3
NAME = "catalog_inventory_indexes"


async def upgrade(db) -> None:
    await db["products"].create_index("sku", unique=True)
    await db["products"].create_index("category")

    await db["inventory_items"].create_index([("facility_id", 1), ("product_id", 1)])
    await db["inventory_items"].create_index("product_id")
    await db["inventory_items"].create_index("organisation_id")

    await db["suppliers"].create_index("organisation_id")

    await db["supplier_availability"].create_index([("supplier_id", 1), ("product_id", 1)])
    await db["supplier_availability"].create_index("product_id")

    await db["facilities"].create_index("is_synthetic")
