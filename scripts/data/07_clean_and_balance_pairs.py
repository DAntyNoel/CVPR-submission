#!/usr/bin/env python3
"""Clean and lightly rebalance canonical preference pairs before training."""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from typing import Any

from common import load_jsonl, repo_path, summarize_records, token_count, write_json, write_jsonl


DEFAULT_EXCLUDED_NEGATIVES = {
    "fork",
    "knife",
    "spoon",
    "remote",
    "cell phone",
    "toothbrush",
    "hair drier",
    "scissors",
    "sports ball",
    "tie",
    "handbag",
    "book",
    "clock",
    "mouse",
    "keyboard",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--output", default="data/processed/canonical_pairs_clean.jsonl")
    parser.add_argument("--stats-output", default="data/processed/stats_clean.json")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-positive-per-object", type=int, default=650)
    parser.add_argument("--max-negative-per-object", type=int, default=650)
    parser.add_argument("--max-answer-tokens", type=int, default=40)
    parser.add_argument("--allow-missing-images", action="store_true")
    parser.add_argument(
        "--keep-low-confidence-negatives",
        action="store_true",
        help="Keep rejected categories that are commonly small or under-annotated.",
    )
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        print(f"Missing canonical input: {input_path}", file=sys.stderr)
        return 2

    records = load_jsonl(input_path)
    selected, report = clean_and_select(records, args)
    if len(selected) < args.limit:
        print(
            f"Only selected {len(selected)} / {args.limit}; consider relaxing caps or generating a larger pool.",
            file=sys.stderr,
        )
        return 2

    selected = selected[: args.limit]
    for idx, record in enumerate(selected, start=1):
        record["id"] = f"clean_{record.get('source', 'pair')}_{idx:06d}"

    write_jsonl(args.output, selected)
    stats = summarize_records(selected)
    stats["cleaning_report"] = report
    write_json(args.stats_output, stats)
    print(f"Wrote {len(selected)} cleaned pairs to {repo_path(args.output)}")
    print(f"Wrote cleaning stats to {repo_path(args.stats_output)}")
    return 0


def clean_and_select(records: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(args.seed)
    shuffled = list(records)
    rng.shuffle(shuffled)

    rejected_reasons: Counter[str] = Counter()
    pos_counts: Counter[str] = Counter()
    neg_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []

    for record in shuffled:
        reason = rejection_reason(record, args)
        if reason:
            rejected_reasons[reason] += 1
            continue
        label = record.get("label") or {}
        pos = str(label.get("positive_object") or label.get("positive_attribute") or "unknown")
        neg = str(label.get("negative_object") or label.get("negative_attribute") or "unknown")
        if pos_counts[pos] >= args.max_positive_per_object:
            rejected_reasons["positive_cap"] += 1
            continue
        if neg_counts[neg] >= args.max_negative_per_object:
            rejected_reasons["negative_cap"] += 1
            continue
        selected.append(dict(record))
        pos_counts[pos] += 1
        neg_counts[neg] += 1
        if len(selected) >= args.limit:
            break

    return selected, {
        "input_total": len(records),
        "selected_total": len(selected),
        "rejected_reasons": dict(sorted(rejected_reasons.items())),
        "positive_counts_top20": pos_counts.most_common(20),
        "negative_counts_top20": neg_counts.most_common(20),
        "max_positive_per_object": args.max_positive_per_object,
        "max_negative_per_object": args.max_negative_per_object,
        "excluded_low_confidence_negatives": [] if args.keep_low_confidence_negatives else sorted(DEFAULT_EXCLUDED_NEGATIVES),
    }


def rejection_reason(record: dict[str, Any], args: argparse.Namespace) -> str | None:
    record_id = record.get("id", "unknown")
    required = (
        "id",
        "source",
        "image",
        "image_id",
        "task_type",
        "question",
        "chosen_answer",
        "rejected_answer",
        "evidence_hint_chosen",
        "evidence_hint_rejected",
        "label",
    )
    for key in required:
        if not record.get(key):
            return f"missing_{key}"
    if not args.allow_missing_images and not repo_path(record["image"]).exists():
        return "missing_image"
    if record["chosen_answer"] == record["rejected_answer"]:
        return "identical_answers"
    if token_count(record["chosen_answer"]) > args.max_answer_tokens:
        return "chosen_too_long"
    if token_count(record["rejected_answer"]) > args.max_answer_tokens:
        return "rejected_too_long"
    if "Evidence hint:" not in record["evidence_hint_chosen"]:
        return "bad_chosen_hint"
    if "Evidence hint:" not in record["evidence_hint_rejected"]:
        return "bad_rejected_hint"

    label = record.get("label") or {}
    if record.get("task_type") == "object_existence":
        pos = label.get("positive_object")
        neg = label.get("negative_object")
        visible = set(label.get("visible_objects") or [])
        if pos == neg:
            return "same_positive_negative"
        if neg in visible:
            return "negative_visible"
        if not args.keep_low_confidence_negatives and neg in DEFAULT_EXCLUDED_NEGATIVES:
            return "low_confidence_negative"

    if not str(record_id):
        return "bad_id"
    return None


if __name__ == "__main__":
    raise SystemExit(main())

