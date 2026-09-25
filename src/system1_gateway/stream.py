from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from .gateway import LocalGateway
from .config import GatewayConfig
from .models import DecisionEnvelope, GatewayRequest
from .policy import baseline_decision, status_for, validate


def baseline_envelope(request: GatewayRequest) -> DecisionEnvelope:
    started = time.perf_counter()
    decision = baseline_decision(request.text)
    result = validate(decision)
    elapsed = (time.perf_counter() - started) * 1000
    return DecisionEnvelope(request_id=str(uuid.uuid4()), source=request.source,
                            model="deterministic-p0-baseline",
                            decision=decision, allowed=result.allowed,
                            status=status_for(result), policy_reason=result.reason,
                            inference_ms=round(elapsed, 6), total_ms=round(elapsed, 6))


def main() -> None:
    parser = argparse.ArgumentParser(description="Long-lived JSONL System-1 gateway")
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    config = GatewayConfig.load(args.config) if args.config else None
    gateway = LocalGateway(config=config) if args.model else None
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            request = GatewayRequest.model_validate(payload)
            envelope = gateway.decide_request(request) if gateway else baseline_envelope(request)
            print(envelope.model_dump_json(), flush=True)
        except Exception as exc:
            print(json.dumps({"error": str(exc)}), flush=True)


if __name__ == "__main__":
    main()
