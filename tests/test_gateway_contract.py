from system1_gateway.models import GatewayRequest
from system1_gateway.policy import baseline_decision, validate


def test_baseline_contract_is_safe_for_approval_gated_action() -> None:
    decision = baseline_decision("Please deploy checkout to production")
    result = validate(decision)
    assert result.allowed is True
    assert decision.requires_approval is True


def test_request_requires_nonempty_text() -> None:
    request = GatewayRequest(text="hello", source="test")
    assert request.source == "test"
