from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from .models import DecisionEnvelope


class ActionRequest(BaseModel):
    action: str = Field(min_length=1)
    route: str = Field(min_length=1)
    arguments: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))


class ActionReceipt(BaseModel):
    idempotency_key: str
    action: str
    status: str
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionAdapter(Protocol):
    def execute(self, request: ActionRequest) -> ActionReceipt: ...


class DryRunAdapter:
    """Default adapter: records intent but never causes an external side effect."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def execute(self, request: ActionRequest) -> ActionReceipt:
        if request.idempotency_key in self._seen:
            return ActionReceipt(idempotency_key=request.idempotency_key,
                                 action=request.action, status="already_seen",
                                 detail="Duplicate action suppressed")
        self._seen.add(request.idempotency_key)
        return ActionReceipt(idempotency_key=request.idempotency_key,
                             action=request.action, status="dry_run",
                             detail=f"Would route to {request.route}")


def action_request(envelope: DecisionEnvelope) -> ActionRequest | None:
    """Build an action only for policy-approved decisions."""
    if not envelope.allowed or envelope.status.value != "accepted":
        return None
    return ActionRequest(action=envelope.decision.action,
                         route=envelope.decision.route,
                         arguments={key: str(value) for key, value in envelope.decision.entities.items()})
