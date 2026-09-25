from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Intent(StrEnum):
    BILLING_DUPLICATE = "billing_duplicate_charge"
    PRODUCTION_DEPLOY = "production_deploy"
    COLD_CHAIN_ALERT = "cold_chain_alert"
    SUSPICIOUS_LOGIN = "suspicious_login"
    CANCELLATION = "cancellation_request"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(StrEnum):
    ACCEPTED = "accepted"
    ABSTAINED = "abstained"
    ESCALATED = "escalated"


class GatewayRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = "cli"


class Decision(BaseModel):
    # String rather than a closed enum so domain packs can add intents.
    # Built-in values remain available through ``Intent`` constants.
    intent: str
    severity: Severity
    entities: dict[str, Any] = Field(default_factory=dict)
    route: str
    requires_approval: bool
    confidence: float = Field(ge=0.0, le=1.0)
    action: str
    rationale: str


class PolicyResult(BaseModel):
    allowed: bool
    auto_executable: bool = False
    decision: Decision
    reason: str | None = None


class DecisionEnvelope(BaseModel):
    """Stable result returned by long-lived gateway integrations."""

    request_id: str
    source: str = "unknown"
    schema_version: str = "system1.v1"
    model: str
    decision: Decision
    allowed: bool
    auto_executable: bool = False
    status: DecisionStatus
    policy_reason: str | None = None
    inference_ms: float
    total_ms: float
