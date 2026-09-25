from __future__ import annotations

import argparse
import json
import time

from .gateway import LocalGateway
from .policy import baseline_decision, validate


SCENARIOS = [
    "My card was charged twice for €49.00",
    "Please deploy checkout-service to production",
    "Warehouse temperature is 9 C",
    "Suspicious login from an unknown country",
    "Cancel my subscription",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="store_true", help="use local GLiNER2.5")
    args = parser.parse_args()
    gateway = LocalGateway() if args.model else None
    print("GLiNER System-1 Gateway | local inference: " + ("ON" if gateway else "OFF"))
    print("-" * 72)
    for text in SCENARIOS:
        started = time.perf_counter()
        if gateway:
            decision, model_ms = gateway.decide(text)
        else:
            decision, model_ms = baseline_decision(text), 0.0
        result = validate(decision)
        total_ms = (time.perf_counter() - started) * 1000
        print(json.dumps({"input": text, "intent": decision.intent,
                          "route": decision.route, "action": decision.action,
                          "confidence": round(decision.confidence, 3),
                          "policy_allowed": result.allowed,
                          "policy_reason": result.reason,
                          "latency_ms": round(model_ms or total_ms, 2)},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
