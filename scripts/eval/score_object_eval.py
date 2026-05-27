#!/usr/bin/env python3
"""Score yes/no eval generations and diagnostic behavior metrics."""

from __future__ import annotations

import argparse
import math
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

EVIDENCE_CUE_RE = re.compile(
    r"\b(evidence|visible|visually|see|seen|image|picture|photo|shown|because)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[A-Za-z0-9']+")
DEFAULT_GROUP_FIELDS = ("benchmark", "source", "dimension", "task_type", "target", "target_text")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw generation JSONL from run_vlm_inference.py")
    parser.add_argument("--metrics", default=None)
    parser.add_argument("--scored-output", default=None)
    parser.add_argument(
        "--group-fields",
        nargs="*",
        default=list(DEFAULT_GROUP_FIELDS),
        help="Fields used for subgroup metrics. Use an empty list to disable.",
    )
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=20,
        help="Minimum rows required before a subgroup is reported.",
    )
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        print(f"Missing generation file: {input_path}", file=sys.stderr)
        return 2

    rows = load_jsonl(input_path)
    scored = [score_row(row) for row in rows]
    metrics = compute_metrics(scored, group_fields=args.group_fields, min_group_size=args.min_group_size)

    metrics_path = args.metrics or default_metrics_path(args.input)
    write_json(metrics_path, metrics)
    if args.scored_output:
        write_jsonl(args.scored_output, scored)

    print(f"Scored {len(scored)} rows from {input_path}")
    print(f"Wrote metrics to {repo_path(metrics_path)}")
    print(
        (
            "acc={accuracy:.4f} bal_acc={balanced_accuracy:.4f} f1={f1:.4f} "
            "fpr={false_positive_rate:.4f} fnr={false_negative_rate:.4f} "
            "yes_bias={yes_bias:.4f} refusal={refusal_rate:.4f} other={other_rate:.4f}"
        ).format(
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
    out["target"] = target
    out["prediction"] = pred
    out["is_refusal"] = is_refusal
    out["is_correct"] = correct
    out["generation_word_count"] = word_count(generation)
    out["has_evidence_cue"] = bool(EVIDENCE_CUE_RE.search(generation))
    return out


def compute_metrics(
    rows: list[dict[str, Any]],
    group_fields: list[str] | tuple[str, ...] | None = None,
    min_group_size: int = 20,
) -> dict[str, Any]:
    metrics = compute_base_metrics(rows)
    if group_fields:
        groups = compute_group_metrics(rows, group_fields, min_group_size)
        if groups:
            metrics["groups"] = groups
    return metrics


def compute_base_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = Counter(row.get("prediction") for row in rows)
    target_counts = Counter(row.get("target") for row in rows)
    correct = sum(1 for row in rows if row.get("is_correct"))
    tp = sum(1 for row in rows if row.get("target") == "yes" and row.get("prediction") == "yes")
    fp = sum(1 for row in rows if row.get("target") == "no" and row.get("prediction") == "yes")
    fn = sum(1 for row in rows if row.get("target") == "yes" and row.get("prediction") != "yes")
    tn = sum(1 for row in rows if row.get("target") == "no" and row.get("prediction") == "no")
    yes_to_no = sum(1 for row in rows if row.get("target") == "yes" and row.get("prediction") == "no")
    actual_yes = target_counts["yes"]
    actual_no = target_counts["no"]
    refusal = sum(1 for row in rows if row.get("is_refusal"))
    other = counts["other"]
    invalid = refusal + other
    word_counts = [int(row.get("generation_word_count") or 0) for row in rows]
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, actual_yes)
    specificity = safe_div(tn, actual_no)
    f1 = safe_div(2 * precision * recall, precision + recall)
    negative_precision = safe_div(tn, tn + yes_to_no)
    negative_f1 = safe_div(2 * negative_precision * specificity, negative_precision + specificity)
    if actual_yes and actual_no:
        balanced_accuracy = (recall + specificity) / 2
    elif actual_yes:
        balanced_accuracy = recall
    elif actual_no:
        balanced_accuracy = specificity
    else:
        balanced_accuracy = 0.0
    return {
        "total": total,
        "accuracy": rounded(safe_div(correct, total)),
        "balanced_accuracy": rounded(balanced_accuracy),
        "precision": rounded(precision),
        "recall": rounded(recall),
        "specificity": rounded(specificity),
        "f1": rounded(f1),
        "negative_precision": rounded(negative_precision),
        "negative_f1": rounded(negative_f1),
        "false_positive_rate": rounded(safe_div(fp, actual_no)),
        "false_negative_rate": rounded(safe_div(fn, actual_yes)),
        "true_positive_rate": rounded(recall),
        "true_negative_rate": rounded(specificity),
        "yes_bias": rounded(safe_div(counts["yes"], total)),
        "no_bias": rounded(safe_div(counts["no"], total)),
        "refusal_rate": rounded(safe_div(refusal, total)),
        "other_rate": rounded(safe_div(other, total)),
        "invalid_prediction_rate": rounded(safe_div(invalid, total)),
        "evidence_cue_rate": rounded(safe_div(sum(1 for row in rows if row.get("has_evidence_cue")), total)),
        "avg_generation_words": rounded(sum(word_counts) / total if total else 0.0),
        "max_generation_words": max(word_counts) if word_counts else 0,
        "long_answer_rate": rounded(safe_div(sum(1 for count in word_counts if count > 10), total)),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "prediction_counts": dict(sorted(counts.items())),
        "target_counts": dict(sorted(target_counts.items())),
    }


def compute_group_metrics(
    rows: list[dict[str, Any]],
    fields: list[str] | tuple[str, ...],
    min_group_size: int,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for field in fields:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            value = extract_field(row, field)
            if value in (None, ""):
                continue
            grouped.setdefault(str(value), []).append(row)
        field_metrics = {
            value: compute_base_metrics(items)
            for value, items in sorted(grouped.items())
            if len(items) >= min_group_size
        }
        if field_metrics:
            out[field] = field_metrics
    return out


def extract_field(row: dict[str, Any], field: str) -> Any:
    value: Any = row
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def rounded(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return round(value, 6)


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
