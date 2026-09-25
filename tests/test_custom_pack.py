from system1_gateway.config import GatewayConfig
from system1_gateway.gateway import LocalGateway, extract_entities


class FakeTask:
    label = "password_reset"
    probabilities = {"password_reset": 0.96}


class FakeClassifier:
    def classify(self, text, schema):
        return {"intent": FakeTask()}


class FakeDecide:
    def classify_text(self, text, tasks, include_confidence=False):
        return {"intent": {"label": "production_deploy", "confidence": 0.96},
                "urgency": {"label": "high", "confidence": 0.88}}

    def extract_entities(self, text, labels, include_spans=False):
        return {"entities": {"service": [{"text": "checkout", "start": 14, "end": 22}]}}


def test_custom_pack_drives_route_without_real_weights() -> None:
    config = GatewayConfig.model_validate({"intents": [
        {"name": "password_reset", "description": "A password reset request", "route": "identity_support"},
        {"name": "unknown", "description": "Unsupported content", "route": "human_triage"},
    ]})
    decision, _ = LocalGateway(config=config, classifier=FakeClassifier()).decide("Reset my password")
    assert decision.intent == "password_reset"
    assert decision.route == "identity_support"


def test_custom_pack_extracts_declared_entity() -> None:
    config = GatewayConfig.model_validate({"intents": [
        {"name": "production_deploy", "description": "A production deployment", "route": "release"},
        {"name": "unknown", "description": "Unsupported content", "route": "human_triage"},
    ], "entities": [{"name": "service", "description": "Deployed service", "pattern": r"deploy (?P<service>[A-Za-z0-9_-]+)"}]})
    decision, _ = LocalGateway(config=config, classifier=FakeClassifier()).decide("deploy checkout")
    assert decision.entities["service"] == "checkout"


def test_default_pack_extracts_multiword_service() -> None:
    config = GatewayConfig.default()
    assert extract_entities("Please deploy beta payments frontend to production", config)["service"] == "beta payments frontend"


def test_decide_adapter_keeps_tasks_and_spans() -> None:
    config = GatewayConfig.model_validate({"intents": [
        {"name": "production_deploy", "description": "A production deployment", "route": "release"},
        {"name": "unknown", "description": "Unsupported content", "route": "human_triage"},
    ], "tasks": [{"name": "urgency", "labels": ["low", "high"]}], "entities": [
        {"name": "service", "description": "A deployed service", "pattern": r"deploy (?P<service>\w+)"}
    ]})
    gateway = LocalGateway(model_name="fastino/GLiNER2.5-Decide", config=config, classifier=FakeDecide())
    decision, _ = gateway.decide("Please deploy checkout")
    assert decision.tasks["urgency"]["label"] == "high"
    assert decision.spans["service"][0]["text"] == "checkout"
