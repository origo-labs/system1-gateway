from system1_gateway.config import GatewayConfig, IntentConfig
from system1_gateway.gateway import LocalGateway
from system1_gateway.models import Decision, Intent, Severity
from system1_gateway.policy import validate


def test_custom_threshold_changes_policy_result() -> None:
    decision = Decision(intent=Intent.BILLING_DUPLICATE, severity=Severity.MEDIUM,
                       route="billing_queue", requires_approval=False,
                       confidence=.8, action="route", rationale="test")
    assert validate(decision, .75).allowed is True
    assert validate(decision, .9).allowed is False
