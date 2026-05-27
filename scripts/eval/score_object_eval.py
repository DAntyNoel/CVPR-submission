#!/usr/bin/env python3
"""Score yes/no eval generations and compute refusal rate."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from typing import Any

from common import load_jsonl, repo_path, write_json, write_jsonl


REFUSAL_PATTERNS = [
    r"\bnot sure\b",
    r"\bunclear\b",
    r"\bcannot determine\b",
    r"\bcan't determine\b",
    r"\bcannot tell\b",
    r"\bcan't tell\b",
    r"\bunable to determine\b",
    r"\binsufficient information\b",
    r"\bnot enough information\b",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw generation JSONL from run_vlm_inference.py")
    parser.add_argument("--metrics", default=None)
    parser.add_argument("--scored-output", default=None)
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        print(f"Missing generation file: {input_path}", file=sys.stderr)
        return 2

    rows = load_jsonl(input_path)
    scored = [score_row(row) for row in rows]
    metrics = compute_metrics(scored)

    metrics_path = args.metrics or default_metrics_path(args.input)
    write_json(metrics_path, metrics)
    if args.scored_output:
        write_jsonl(args.scored_output, scored)

    print(f"Scored {len(scored)} rows from {input_path}")
    print(f"Wrote metrics to {repo_path(metrics_path)}")
    print(
        "acc={accuracy:.4f} f1={f1:.4f} yes_bias={yes_bias:.4f} refusal={refusal_rate:.4f}".format(
            **metrics
        )
    )
    return 0


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    target = normalize_target(row.get("target"))
    generation = str(row.get("generation") or row.get("output") or "")
    pred, is_refusal = parse_prediction(generation)
    correct = bool(target in {"yes", "no"} and pred == target)
    out = dict(row)
    out["prediction"] = pred
    out["is_refusal"] = is_refusal
    out["is_correct"] = correct
    return out


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = Counter(row.get("prediction") for row in rows)
    correct = sum(1 for row in rows if row.get("is_correct"))
    tp = sum(1 for row in rows if row.get("target") == "yes" and row.get("prediction") == "yes")
    fp = sum(1 for row in rows if row.get("target") == "no" and row.get("prediction") == "yes")
    fn = sum(1 for row in rows if row.get("target") == "yes" and row.get("prediction") != "yes")
    tn = sum(1 for row in rows if row.get("target") == "no" and row.get("prediction") == "no")
    refusal = sum(1 for row in rows if row.get("is_refusal"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "total": total,
        "accuracy": round(correct / total, 6) if total else 0.0,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "yes_bias": round(counts["yes"] / total, 6) if total else 0.0,
        "refusal_rate": round(refusal / total, 6) if total else 0.0,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "prediction_counts": dict(sorted(counts.items())),
    }


def parse_prediction(text: str) -> tuple[str, bool]:
    norm = " ".join(text.strip().lower().split())
    if not norm:
        return "other", False
    if any(re.search(pattern, norm) for pattern in REFUSAL_PATTERNS):
        return "refusal", True
    first_token = re.match(r"^[^a-z0-9]*(yes|no|yeah|yep|nope)\b", norm)
    if first_token:
        token = first_token.group(1)
        return ("yes" if token in {"yes", "yeah", "yep"} else "no"), False
    if re.search(r"\b(there is no|there are no|do not see|don't see|cannot see|can't see)\b", norm):
        return "no", False
    if re.search(r"\b(there is|there are|i can see|visible)\b", norm):
        return "yes", False
    if re.search(r"\byes\b", norm):
        return "yes", False
    if re.search(r"\bno\b", norm):
        return "no", False
    return "other", False


def normalize_target(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "yes"
    if text in {"no", "n", "false", "0"}:
        return "no"
    return text


def default_metrics_path(input_path: str) -> str:
    path = str(input_path)
    if path.endswith(".jsonl"):
        return path[:-6] + ".metrics.json"
    return path + ".metrics.json"


if __name__ == "__main__":
    raise SystemExit(main())
