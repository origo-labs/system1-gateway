from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .gateway import LocalGateway
from .policy import baseline_decision, validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (Path(__file__).parents[2] / "fixtures/p0.jsonl").read_text().splitlines()]
    gateway = LocalGateway() if args.model else None
    cold_start_ms = 0.0
    if gateway:
        started = time.perf_counter()
        gateway.warmup()
        cold_start_ms = (time.perf_counter() - started) * 1000
    latencies: list[float] = []
    correct = safe = abstained = 0
    confidence_error = 0.0
    for row in rows:
        started = time.perf_counter()
        decision = gateway.decide(row["text"])[0] if gateway else baseline_decision(row["text"])
        result = validate(decision)
        latencies.append((time.perf_counter() - started) * 1000)
        correct += decision.intent == row["intent"]
        safe += result.allowed or decision.intent in {"unknown", "cold_chain_alert", "suspicious_login"}
        abstained += result.reason in {"low confidence", "unsupported intent"}
        confidence_error += abs(decision.confidence - float(decision.intent == row["intent"]))
    ordered = sorted(latencies)
    report = {"model": "gliner2.5-small" if gateway else "contract-baseline",
              "samples": len(rows), "intent_accuracy": correct / len(rows),
              "policy_safety_rate": safe / len(rows),
              "abstention_rate": abstained / len(rows),
              "mean_confidence_error": confidence_error / len(rows),
              "cold_start_ms": cold_start_ms,
              "latency_ms": {"p50": ordered[len(ordered)//2],
                             "p95": ordered[min(len(ordered)-1, int(.95*len(ordered)))],
                             "p99": ordered[min(len(ordered)-1, int(.99*len(ordered)))]},
              "throughput_per_second": len(rows) / (sum(latencies) / 1000) }
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
