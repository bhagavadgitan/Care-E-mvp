"""Audit event repository (MongoDB, append-only)."""
from domain.models import AuditEvent
from repositories.mongo.base_repository import MongoRepository


class AuditRepository(MongoRepository[AuditEvent]):
    collection_name = "audit_events"
    model = AuditEvent


audit_repository = AuditRepository()
