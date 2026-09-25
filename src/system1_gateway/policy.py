from __future__ import annotations

from .models import Decision, DecisionStatus, Intent, PolicyResult, Severity


ROUTES = {
    Intent.BILLING_DUPLICATE: "billing_queue",
    Intent.PRODUCTION_DEPLOY: "release_management",
    Intent.COLD_CHAIN_ALERT: "facilities_on_call",
    Intent.SUSPICIOUS_LOGIN: "security_operations",
    Intent.CANCELLATION: "retention_queue",
    Intent.UNKNOWN: "human_triage",
}

DEFAULT_CONFIDENCE_THRESHOLD = 0.75
LOW_RISK_AUTO_ROUTES = {Intent.BILLING_DUPLICATE.value: "billing_queue"}


def auto_executable(decision: Decision) -> bool:
    """Return whether policy permits an action without human approval."""
    return (decision.intent in LOW_RISK_AUTO_ROUTES
            and decision.route == LOW_RISK_AUTO_ROUTES[decision.intent]
            and not decision.requires_approval
            and decision.severity in {Severity.LOW, Severity.MEDIUM})


def validate(decision: Decision, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> PolicyResult:
    """Apply deterministic guardrails after semantic interpretation."""
    if decision.intent == Intent.UNKNOWN.value:
        return PolicyResult(allowed=False, auto_executable=False, decision=decision, reason="unsupported intent")
    if decision.confidence < confidence_threshold:
        return PolicyResult(allowed=False, auto_executable=False, decision=decision, reason="low confidence")
    if decision.intent in {Intent.PRODUCTION_DEPLOY.value, Intent.CANCELLATION.value}:
        if not decision.requires_approval:
            return PolicyResult(allowed=False, auto_executable=False, decision=decision, reason="approval required")
    if decision.severity in {Severity.HIGH, Severity.CRITICAL}:
        return PolicyResult(allowed=False, auto_executable=False, decision=decision, reason="human escalation required")
    return PolicyResult(allowed=True, auto_executable=auto_executable(decision), decision=decision)


def status_for(result: PolicyResult) -> DecisionStatus:
    if result.allowed:
        return DecisionStatus.ACCEPTED
    if result.reason in {"low confidence", "unsupported intent"}:
        return DecisionStatus.ABSTAINED
    return DecisionStatus.ESCALATED


def baseline_decision(text: str) -> Decision:
    """Small deterministic stand-in used to exercise the contract in P0."""
    lower = text.lower()
    if "charged twice" in lower or "duplicate charge" in lower or "two charges" in lower:
        intent, severity, entities = Intent.BILLING_DUPLICATE, Severity.MEDIUM, {}
        action, approval, confidence = "route", False, 0.95
    elif "deploy" in lower and "production" in lower:
        intent, severity, entities = Intent.PRODUCTION_DEPLOY, Severity.MEDIUM, {}
        action, approval, confidence = "request_approval", True, 0.94
    elif "temperature" in lower or "cold chain" in lower:
        intent, severity, entities = Intent.COLD_CHAIN_ALERT, Severity.HIGH, {}
        action, approval, confidence = "page_on_call", False, 0.93
    elif "suspicious login" in lower or "login" in lower and "unknown" in lower:
        intent, severity, entities = Intent.SUSPICIOUS_LOGIN, Severity.HIGH, {}
        action, approval, confidence = "lock_and_escalate", False, 0.92
    elif "cancel" in lower or "cancellation" in lower:
        intent, severity, entities = Intent.CANCELLATION, Severity.MEDIUM, {}
        action, approval, confidence = "request_approval", True, 0.91
    else:
        intent, severity, entities = Intent.UNKNOWN, Severity.LOW, {}
        action, approval, confidence = "human_review", False, 0.20
    return Decision(intent=intent, severity=severity, entities=entities,
                    route=ROUTES[intent], requires_approval=approval,
                    confidence=confidence, action=action,
                    rationale="P0 deterministic contract baseline")
