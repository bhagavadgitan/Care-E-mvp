"""Minimal application-level audit trail for important state-changing actions."""
from typing import Any, Dict, Optional

from domain.models import AuditEvent, User
from repositories.mongo.audit_repository import audit_repository


async def record_event(
    action: str,
    *,
    actor: Optional[User] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    organisation_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    event = AuditEvent(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        organisation_id=organisation_id or (actor.organisation_id if actor else None),
        meta=meta or {},
    )
    await audit_repository.create(event)
