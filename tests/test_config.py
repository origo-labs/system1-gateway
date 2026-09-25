from system1_gateway.config import GatewayConfig
from pydantic import ValidationError


def test_default_config_is_valid_and_complete() -> None:
    config = GatewayConfig.default()
    assert config.schema_version == "system1.v1"
    assert {item.name for item in config.intents} >= {"unknown", "production_deploy"}


def test_duplicate_intents_are_rejected() -> None:
    try:
        GatewayConfig.model_validate({"intents": [
            {"name": "unknown", "description": "a", "route": "triage"},
            {"name": "unknown", "description": "b", "route": "triage"},
        ]})
    except ValidationError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("duplicate intent names should fail validation")
