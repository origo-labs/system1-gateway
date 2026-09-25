from system1_gateway.actions import DryRunAdapter, action_request
from system1_gateway.models import Decision, DecisionEnvelope, DecisionStatus, Intent, Severity


def envelope(allowed=True, status=DecisionStatus.ACCEPTED):
    return DecisionEnvelope(
        request_id="r1", model="test", decision=Decision(
            intent=Intent.BILLING_DUPLICATE, severity=Severity.MEDIUM,
            route="billing_queue", requires_approval=False, confidence=.9,
            action="route", rationale="test"), allowed=allowed, status=status,
        inference_ms=1, total_ms=1)


def test_default_adapter_is_side_effect_free() -> None:
    request = action_request(envelope())
    assert request is not None
    receipt = DryRunAdapter().execute(request)
    assert receipt.status == "dry_run"


def test_rejected_decision_cannot_create_action() -> None:
    assert action_request(envelope(False, DecisionStatus.ESCALATED)) is None


def test_duplicate_action_is_suppressed() -> None:
    request = action_request(envelope())
    adapter = DryRunAdapter()
    assert adapter.execute(request).status == "dry_run"
    assert adapter.execute(request).status == "already_seen"
