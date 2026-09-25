from __future__ import annotations

import re
import time
import uuid

from .models import Decision, DecisionEnvelope, GatewayRequest, Intent, Severity
from .config import GatewayConfig
from .policy import ROUTES, status_for, validate


def extract_entities(text: str, config: GatewayConfig | None = None) -> dict[str, str]:
    entities: dict[str, str] = {}
    patterns = {
        "email": r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
        "ticket_id": r"\b(?:INC|TICKET|CASE)-\d+\b",
        "amount": r"(?:[$€£]\s*\d+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?\s*(?:USD|EUR|SEK))",
        "temperature": r"(?<![A-Za-z])-?\d+(?:\.\d+)?\s*°?\s*[CF]\b",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            entities[name] = match.group(0)
    for entity in (config.entities if config else []):
        try:
            match = re.search(entity.pattern, text, re.I)
        except re.error:
            continue
        if match:
            entities[entity.name] = match.groupdict().get(entity.name, match.group(0))
    return entities


class LocalGateway:
    def __init__(self, model_name: str = "fastino/gliner2.5-small-v1", config: GatewayConfig | None = None, classifier=None) -> None:
        if classifier is None:
            if model_name.lower().endswith("decide"):
                from gliner2 import AutoExtractor
                classifier = AutoExtractor.from_pretrained(model_name)
            else:
                from gliner2.classification import Classifier
                classifier = Classifier.from_pretrained(model_name, device="cpu")
        self.model = classifier
        self.model_name = model_name
        self._decide_api = model_name.lower().endswith("decide")
        self.config = config or GatewayConfig.default()
        self._warmed = False

    @property
    def ready(self) -> bool:
        return self._warmed

    def warmup(self) -> float:
        """Run one inference so callers can separate cold start from warm latency."""
        _, elapsed_ms = self.decide("warmup health check")
        self._warmed = True
        return elapsed_ms

    def decide(self, text: str) -> tuple[Decision, float]:
        started = time.perf_counter()
        task_outputs: dict[str, object] = {}
        model_spans: dict[str, list[dict]] = {}
        if self._decide_api:
            intent_task = type("Task", (), {"name": "intent", "labels": [item.name for item in self.config.intents]})()
            task_specs = [intent_task] + [task for task in self.config.tasks if task.name != "intent"]
            task_input = {task.name: task.labels for task in task_specs}
            result = self.model.classify_text(text, task_input, include_confidence=True)
            task_outputs = result
            entity_labels = [item.name for item in self.config.entities]
            if entity_labels:
                span_result = self.model.extract_entities(text, entity_labels, include_spans=True)
                model_spans = span_result.get("entities", {})
            task = result["intent"]
            label = task["label"] if isinstance(task, dict) else task
            confidence = float(task.get("confidence", 0.0)) if isinstance(task, dict) else 0.0
        else:
            from gliner2.classification import ClassificationSchema
            from gliner2.classification.schema import LabelSpec
            labels = [LabelSpec(item.name, item.description) for item in self.config.intents]
            schema = ClassificationSchema().single("intent", labels, instruction="Select the operational intent of this message.")
            result = self.model.classify("Message: " + text, schema)
            task = result["intent"]
            label = task.label
            confidence = float(task.probabilities.get(task.label, 0.0))
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            intent: str = Intent(label).value
        except ValueError:
            intent = label
        entities = extract_entities(text, self.config)
        constraints = self._check_constraints(task_outputs)
        lower = text.lower()
        # A deployment without an explicit production target is not a
        # production-deploy decision. Keep the semantic layer conservative.
        if intent == Intent.PRODUCTION_DEPLOY.value and not re.search(r"\b(prod|production|live)\b", lower):
            intent = Intent.UNKNOWN.value
        if intent == Intent.CANCELLATION.value and re.search(r"\b(change|upgrade|downgrade)\b", lower):
            intent = Intent.UNKNOWN.value
        if confidence < self.config.threshold_for(intent):
            intent = Intent.UNKNOWN.value
        severity = Severity.HIGH if intent in {Intent.COLD_CHAIN_ALERT.value, Intent.SUSPICIOUS_LOGIN.value} else Severity.MEDIUM
        configured = next((item for item in self.config.intents if item.name == intent), None)
        approval = configured.requires_approval if configured else False
        action = "request_approval" if approval else ("human_review" if intent == Intent.UNKNOWN.value else "route")
        return Decision(intent=intent, severity=severity, entities=entities,
                        route=configured.route if configured else ROUTES.get(intent, "human_triage"), requires_approval=approval,
                        confidence=confidence, action=action,
                        rationale="GLiNER2.5 local classification", tasks=task_outputs,
                        spans=model_spans, constraints=constraints), elapsed_ms

    def _check_constraints(self, outputs: dict[str, object]) -> dict[str, object]:
        violations = []
        for rule in self.config.constraints:
            task = outputs.get(rule.get("when_task"), {})
            value = task.get("label") if isinstance(task, dict) else task
            if value == rule.get("when_value"):
                target = outputs.get(rule.get("requires_task"), {})
                target_value = target.get("label") if isinstance(target, dict) else target
                if target_value != rule.get("requires_value"):
                    violations.append(rule)
        return {"feasible": not violations, "violations": violations}

    def decide_request(self, request: GatewayRequest) -> DecisionEnvelope:
        started = time.perf_counter()
        decision, inference_ms = self.decide(request.text)
        checked = validate(decision, self.config.threshold_for(decision.intent))
        return DecisionEnvelope(
            request_id=str(uuid.uuid4()), model=self.model_name,
            source=request.source,
            decision=checked.decision, allowed=checked.allowed,
            auto_executable=checked.auto_executable,
            status=status_for(checked),
            policy_reason=checked.reason, inference_ms=round(inference_ms, 6),
            total_ms=round((time.perf_counter() - started) * 1000, 6),
        )

    def decide_batch(self, requests: list[GatewayRequest]) -> list[DecisionEnvelope]:
        return [self.decide_request(request) for request in requests]


Gateway = LocalGateway
