import argparse
import json
from collections import Counter
from pathlib import Path

from .policy import baseline_decision, validate


def evaluate(rows: list[dict]) -> dict:
    expected = [str(row["intent"]) for row in rows]
    decisions = [validate(baseline_decision(row["text"])) for row in rows]
    predicted = [result.decision.intent for result in decisions]
    labels = sorted(set(expected) | set(predicted))
    per_intent = {}
    for label in labels:
        tp = sum(p == label and y == label for p, y in zip(predicted, expected))
        fp = sum(p == label and y != label for p, y in zip(predicted, expected))
        fn = sum(p != label and y == label for p, y in zip(predicted, expected))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_intent[label] = {"support": sum(y == label for y in expected), "precision": precision,
                             "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    confusion = {label: dict(Counter(p for p, y in zip(predicted, expected) if y == label)) for label in labels}
    accepted = [result.allowed for result in decisions]
    executable = [result.auto_executable for result in decisions]
    return {"samples": len(rows), "accuracy": sum(p == y for p, y in zip(predicted, expected)) / len(rows) if rows else 0.0,
            "coverage": sum(accepted) / len(accepted) if accepted else 0.0,
            "auto_route_coverage": sum(executable) / len(executable) if executable else 0.0,
            "selective_accuracy": sum(p == y for p, y, a in zip(predicted, expected, accepted) if a) / sum(accepted) if any(accepted) else 0.0,
            "per_intent": per_intent, "confusion": confusion}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a labeled System-1 fixture")
    parser.add_argument("input", type=Path, nargs="?", default=Path("fixtures/p0.jsonl"))
    parser.add_argument("--model", action="store_true", help="evaluate the local GLiNER classifier")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    if args.model:
        from .gateway import LocalGateway
        gateway = LocalGateway()
        decisions = []
        for row in rows:
            decision, _ = gateway.decide(row["text"])
            decisions.append(validate(decision))
        expected = [str(row["intent"]) for row in rows]
        predicted = [result.decision.intent for result in decisions]
        metrics = {"samples": len(rows), "accuracy": sum(p == y for p, y in zip(predicted, expected)) / len(rows) if rows else 0.0,
                   "coverage": sum(result.allowed for result in decisions) / len(decisions) if decisions else 0.0,
                   "auto_route_coverage": sum(result.auto_executable for result in decisions) / len(decisions) if decisions else 0.0}
        report = {"fixture": str(args.input), "policy": "model+policy", "metrics": metrics}
    else:
        report = {"fixture": str(args.input), "policy": "baseline.v1", "metrics": evaluate(rows)}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
