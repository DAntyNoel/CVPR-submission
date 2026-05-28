#!/usr/bin/env python3
"""Score CEPO evidence-probe generations."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from typing import Any

from common import clean_name, load_jsonl, repo_path, write_json, write_jsonl


ANSWER_RE = re.compile(r"\b(yes|no|yeah|yep|nope)\b", re.IGNORECASE)
JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


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

    print(f"Scored {len(scored)} evidence-probe rows from {input_path}")
    print(f"Wrote metrics to {repo_path(metrics_path)}")
    print(
        (
            "answer_acc={answer_accuracy:.4f} support_acc={support_accuracy:.4f} "
            "evidence_acc={evidence_label_accuracy:.4f} relation_acc={relation_direction_accuracy:.4f} "
            "wrong_reject={wrong_evidence_rejection_accuracy:.4f} invalid_json={invalid_json_rate:.4f}"
        ).format(**metrics)
    )
    return 0


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    generation = str(row.get("generation") or row.get("output") or "")
    parsed = parse_generation(generation)
    target_answer = normalize_answer(row.get("target_answer") or row.get("target"))
    target_support = normalize_support(row.get("target_support"))
    pred_answer = normalize_answer(parsed.get("answer"))
    pred_support = normalize_support(parsed.get("support"))

    pred_evidence = clean_name(parsed.get("evidence_label") or parsed.get("evidence") or "")
    target_evidence = clean_name(row.get("target_evidence_label") or "")
    pred_claim = clean_name(parsed.get("claim") or "")
    target_claim = clean_name(row.get("target_claim") or "")
    pred_relation = normalize_relation(parsed.get("relation") or parsed.get("claim") or parsed.get("evidence") or generation)
    target_relation = normalize_relation(row.get("target_relation"))

    is_relation = row.get("base_task_type") == "relation_spatial"
    support_correct = bool(target_support and pred_support == target_support)
    wrong_rejected = bool(target_support == "wrong_evidence" and pred_support in {"wrong_evidence", "contradicted", "unsupported"})

    evidence_correct = False
    if is_relation:
        subject = clean_name(row.get("target_subject") or "")
        obj = clean_name(row.get("target_object") or "")
        text = clean_name(" ".join(str(parsed.get(key) or "") for key in ("claim", "evidence", "evidence_label")))
        evidence_correct = bool(subject and obj and subject in text and obj in text)
    elif target_evidence:
        evidence_correct = pred_evidence == target_evidence or target_evidence in pred_evidence

    relation_correct = True
    if is_relation:
        relation_correct = bool(target_relation and pred_relation == target_relation)

    out = dict(row)
    out.update(
        {
            "parsed_generation": parsed,
            "prediction": pred_answer,
            "predicted_support": pred_support,
            "predicted_evidence_label": pred_evidence,
            "predicted_relation": pred_relation,
            "answer_correct": bool(target_answer and pred_answer == target_answer),
            "support_correct": support_correct,
            "evidence_label_correct": evidence_correct,
            "claim_match": bool(target_claim and (target_claim in pred_claim or pred_claim in target_claim)),
            "relation_direction_correct": relation_correct,
            "wrong_evidence_rejected": wrong_rejected,
            "json_valid": bool(parsed.get("_json_valid")),
            "parse_failed": bool(parsed.get("_parse_failed")),
        }
    )
    return out


def parse_generation(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {"_json_valid": False, "_parse_failed": False}
    match = JSON_RE.search(text)
    if match:
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, dict):
                parsed.update(payload)
                parsed["_json_valid"] = True
                return parsed
        except json.JSONDecodeError:
            pass

    lowered = text.lower()
    answer_match = ANSWER_RE.search(lowered)
    if answer_match:
        parsed["answer"] = answer_match.group(1)

    for key in ("claim", "evidence_label", "evidence", "support", "relation"):
        value = parse_labeled_field(text, key)
        if value:
            parsed[key] = value

    inferred_support = False
    if "support" not in parsed:
        parsed["support"] = infer_support(lowered)
        inferred_support = True
    useful_support = not (inferred_support and parsed.get("support") == "unknown")
    useful_fields = any(key in parsed for key in ("answer", "claim", "evidence_label", "evidence")) or useful_support
    if not useful_fields:
        parsed["_parse_failed"] = True
    return parsed


def parse_labeled_field(text: str, key: str) -> str | None:
    label_pattern = re.escape(key).replace("_", r"[_\s-]?")
    pattern = re.compile(rf"{label_pattern}\s*[:=]\s*([^\n,;}}]+)", re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def infer_support(text: str) -> str:
    if re.search(r"\b(wrong|incorrect|mismatch|does not match|not the evidence|invalid)\b", text):
        return "wrong_evidence"
    if re.search(r"\b(contradict|contradicted|unsupported|not supported|no support)\b", text):
        return "contradicted"
    if re.search(r"\b(supported|correct|matches|match)\b", text):
        return "supported"
    return "unknown"


def normalize_answer(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "yeah", "yep"}:
        return "yes"
    if text in {"no", "n", "false", "0", "nope"}:
        return "no"
    match = ANSWER_RE.search(text)
    if match:
        token = match.group(1).lower()
        return "yes" if token in {"yes", "yeah", "yep"} else "no"
    return text


def normalize_support(value: Any) -> str:
    text = clean_name(value)
    text = text.replace("not supported", "unsupported")
    if text in {"supported", "support", "correct", "match", "matched"}:
        return "supported"
    if text in {"wrong evidence", "wrong_evidence", "incorrect", "mismatch", "mismatched"}:
        return "wrong_evidence"
    if text in {"contradicted", "contradiction", "unsupported", "not support"}:
        return "contradicted"
    if "wrong" in text or "mismatch" in text or "incorrect" in text:
        return "wrong_evidence"
    if "contradict" in text or "unsupported" in text:
        return "contradicted"
    if "support" in text or "correct" in text or "match" in text:
        return "supported"
    return text or "unknown"


def normalize_relation(value: Any) -> str:
    text = clean_name(value)
    if "left" in text:
        return "left_of"
    if "right" in text:
        return "right_of"
    return text


def compute_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    relation_rows = [row for row in rows if row.get("base_task_type") == "relation_spatial"]
    wrong_rows = [row for row in rows if row.get("target_support") == "wrong_evidence"]
    support_counts = Counter(row.get("predicted_support") for row in rows)
    return {
        "total": total,
        "answer_accuracy": rate(rows, "answer_correct"),
        "support_accuracy": rate(rows, "support_correct"),
        "evidence_label_accuracy": rate(rows, "evidence_label_correct"),
        "claim_match_rate": rate(rows, "claim_match"),
        "relation_direction_accuracy": rate(relation_rows, "relation_direction_correct"),
        "wrong_evidence_rejection_accuracy": rate(wrong_rows, "wrong_evidence_rejected"),
        "invalid_json_rate": rounded(sum(1 for row in rows if not row.get("json_valid")) / total if total else 0.0),
        "parse_failure_rate": rate(rows, "parse_failed"),
        "predicted_support_counts": dict(sorted(support_counts.items())),
        "by_base_task_type": grouped_metrics(rows, "base_task_type"),
        "by_target_support": grouped_metrics(rows, "target_support"),
    }


def grouped_metrics(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(field) or "unknown"), []).append(row)
    return {
        key: {
            "total": len(items),
            "answer_accuracy": rate(items, "answer_correct"),
            "support_accuracy": rate(items, "support_correct"),
            "evidence_label_accuracy": rate(items, "evidence_label_correct"),
            "wrong_evidence_rejection_accuracy": rate(items, "wrong_evidence_rejected"),
        }
        for key, items in sorted(grouped.items())
    }


def rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return rounded(sum(1 for row in rows if row.get(key)) / len(rows))


def rounded(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return round(value, 6)


def default_metrics_path(input_path: str) -> str:
    path = str(input_path)
    if path.endswith(".jsonl"):
        return path[:-6] + ".metrics.json"
    return path + ".metrics.json"


if __name__ == "__main__":
    raise SystemExit(main())
