from system1_gateway.models import GatewayRequest, DecisionStatus
from system1_gateway.stream import baseline_envelope


def test_stream_envelope_is_serializable() -> None:
    result = baseline_envelope(GatewayRequest(text="My card was charged twice", source="support"))
    assert result.status is DecisionStatus.ACCEPTED
    assert result.model == "deterministic-p0-baseline"
    assert result.request_id
    assert result.source == "support"
