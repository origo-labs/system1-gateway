from system1_gateway.models import Decision, DecisionStatus, Intent, Severity
from system1_gateway.policy import status_for, validate


def make_decision(**overrides):
    values = dict(intent=Intent.BILLING_DUPLICATE, severity=Severity.MEDIUM,
                  route="billing_queue", requires_approval=False,
                  confidence=0.9, action="route", rationale="test")
    values.update(overrides)
    return Decision(**values)


def test_low_confidence_abstains() -> None:
    result = validate(make_decision(confidence=0.2))
    assert status_for(result) is DecisionStatus.ABSTAINED


def test_high_severity_escalates() -> None:
    result = validate(make_decision(severity=Severity.CRITICAL))
    assert status_for(result) is DecisionStatus.ESCALATED


def test_safe_decision_is_accepted() -> None:
    result = validate(make_decision())
    assert status_for(result) is DecisionStatus.ACCEPTED
