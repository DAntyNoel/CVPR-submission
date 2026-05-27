#!/usr/bin/env python3
"""Mine a locked diagnostic eval set from Base model object-existence errors."""

from __future__ import annotations

import argparse
import csv
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import load_json, load_jsonl, repo_path, write_json, write_jsonl
from score_object_eval import score_row


ERROR_TYPES = ("false_positive", "false_negative")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="results/eval/generations/base_error_mining_candidates/mixed/base.jsonl",
        help="Base generation JSONL from the candidate pool.",
    )
    parser.add_argument("--output", default="data/eval/base_error_mined_object_existence.jsonl")
    parser.add_argument("--summary", default="data/eval/base_error_mined_object_existence.summary.json")
    parser.add_argument("--audit-output", default="data/audit/base_error_mined_audit.csv")
    parser.add_argument("--train", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--max-rows", type=int, default=600)
    parser.add_argument("--audit-sample-size", type=int, default=150)
    parser.add_argument("--max-per-category", type=int, default=80)
    parser.add_argument("--max-per-strategy", type=int, default=360)
    parser.add_argument("--max-per-image", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--include-invalid",
        action="store_true",
        help="Allow non yes/no Base errors into the locked set. Off by default.",
    )
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Missing Base generation file: {input_path}")

    scored_rows = [annotate_error(score_row(row)) for row in load_jsonl(input_path)]
    selected = select_locked_rows(scored_rows, args)
    if not selected:
        raise SystemExit("No eligible Base errors found for the locked diagnostic set.")

    locked_rows = [make_locked_row(idx, row) for idx, row in enumerate(selected, start=1)]
    count = write_jsonl(args.output, locked_rows)
    write_audit_csv(args.audit_output, selected, args)

    metadata = load_generation_metadata(input_path)
    overlap = sorted(load_train_image_ids(args.train) & {str(row.get("image_id")) for row in locked_rows})
    summary = build_summary(
        args=args,
        scored_rows=scored_rows,
        selected_rows=locked_rows,
        source_rows=selected,
        metadata=metadata,
        overlap=overlap,
        written_count=count,
    )
    write_json(args.summary, summary)

    print(f"Wrote {count} mined diagnostic rows to {repo_path(args.output)}")
    print(f"Wrote mined summary to {repo_path(args.summary)}")
    print(f"Wrote audit sheet to {repo_path(args.audit_output)}")
    print(f"Selected error types: {summary['base_error_type_counts']}")
    print(f"Train/eval image overlap: {len(overlap)}")
    return 0


def annotate_error(row: dict[str, Any]) -> dict[str, Any]:
    target = str(row.get("target") or "")
    prediction = str(row.get("prediction") or "")
    out = dict(row)
    out["base_prediction"] = prediction
    out["base_is_correct"] = bool(row.get("is_correct"))
    if target == "no" and prediction == "yes":
        out["base_error_type"] = "false_positive"
    elif target == "yes" and prediction == "no":
        out["base_error_type"] = "false_negative"
    elif target in {"yes", "no"} and prediction != target:
        out["base_error_type"] = "invalid_error"
    else:
        out["base_error_type"] = "correct"
    return out


def select_locked_rows(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    rng = random.Random(args.seed)
    eligible = [
        row
        for row in rows
        if row.get("base_error_type") in ERROR_TYPES
        or (args.include_invalid and row.get("base_error_type") == "invalid_error")
    ]
    by_type = {error_type: [row for row in eligible if row.get("base_error_type") == error_type] for error_type in ERROR_TYPES}
    for error_rows in by_type.values():
        rng.shuffle(error_rows)

    target_total = min(args.max_rows, len(eligible))
    fp_target = target_total // 2
    fn_target = target_total - fp_target
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    counters = SelectionCounters()

    for error_type, limit in (("false_positive", fp_target), ("false_negative", fn_target)):
        for row in by_type[error_type]:
            if counters.error_type[error_type] >= limit:
                break
            try_add(row, selected, selected_ids, counters, args)

    if len(selected) < target_total:
        remainder = [row for row in eligible if str(row.get("id")) not in selected_ids]
        rng.shuffle(remainder)
        for row in remainder:
            if len(selected) >= target_total:
                break
            try_add(row, selected, selected_ids, counters, args)

    selected.sort(key=lambda row: str(row.get("id") or ""))
    return selected


def try_add(
    row: dict[str, Any],
    selected: list[dict[str, Any]],
    selected_ids: set[str],
    counters: "SelectionCounters",
    args: argparse.Namespace,
) -> bool:
    row_id = str(row.get("id") or "")
    if not row_id or row_id in selected_ids:
        return False
    category = str(row.get("target_object") or row.get("target_text") or "unknown")
    strategy = str(row.get("candidate_strategy") or "unknown")
    image_id = str(row.get("image_id") or "unknown")
    if counters.category[category] >= args.max_per_category:
        return False
    if counters.strategy[strategy] >= args.max_per_strategy:
        return False
    if counters.image[image_id] >= args.max_per_image:
        return False

    selected.append(row)
    selected_ids.add(row_id)
    counters.category[category] += 1
    counters.strategy[strategy] += 1
    counters.image[image_id] += 1
    counters.error_type[str(row.get("base_error_type"))] += 1
    return True


class SelectionCounters:
    def __init__(self) -> None:
        self.category: Counter[str] = Counter()
        self.strategy: Counter[str] = Counter()
        self.image: Counter[str] = Counter()
        self.error_type: Counter[str] = Counter()


def make_locked_row(idx: int, row: dict[str, Any]) -> dict[str, Any]:
    keep_fields = [
        "image",
        "image_id",
        "question",
        "target",
        "target_object",
        "target_text",
        "task_type",
        "candidate_strategy",
        "positive_object",
        "negative_object",
        "pair_id",
    ]
    out = {
        "id": f"base_error_mined_{idx:06d}",
        "source": "base_error_mined_coco_object_existence",
        "source_candidate_id": row.get("id"),
    }
    for field in keep_fields:
        if field in row:
            out[field] = row.get(field)
    out["base_prediction"] = row.get("base_prediction")
    out["base_error_type"] = row.get("base_error_type")
    return out


def write_audit_csv(path: str, selected: list[dict[str, Any]], args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    audit_rows = list(selected)
    rng.shuffle(audit_rows)
    audit_rows = audit_rows[: min(args.audit_sample_size, len(audit_rows))]
    output_path = repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "image",
        "image_id",
        "question",
        "target",
        "target_object",
        "candidate_strategy",
        "base_prediction",
        "base_error_type",
        "generation",
        "image_exists",
        "question_clear",
        "target_label_trusted",
        "base_wrong_confirmed",
        "audit_decision",
        "noise_notes",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in audit_rows:
            image = str(row.get("image") or "")
            writer.writerow(
                {
                    "id": row.get("id"),
                    "image": image,
                    "image_id": row.get("image_id"),
                    "question": row.get("question"),
                    "target": row.get("target"),
                    "target_object": row.get("target_object"),
                    "candidate_strategy": row.get("candidate_strategy"),
                    "base_prediction": row.get("base_prediction"),
                    "base_error_type": row.get("base_error_type"),
                    "generation": row.get("generation"),
                    "image_exists": repo_path(image).exists() if image else False,
                    "question_clear": "",
                    "target_label_trusted": "",
                    "base_wrong_confirmed": "",
                    "audit_decision": "",
                    "noise_notes": "",
                }
            )


def build_summary(
    args: argparse.Namespace,
    scored_rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    overlap: list[str],
    written_count: int,
) -> dict[str, Any]:
    wrong_rows = [row for row in scored_rows if not row.get("base_is_correct")]
    eligible = [row for row in scored_rows if row.get("base_error_type") in ERROR_TYPES]
    selected_error_counts = Counter(row.get("base_error_type") for row in selected_rows)
    return {
        "output": str(repo_path(args.output)),
        "candidate_pool_path": metadata.get("eval_file"),
        "base_generation_path": str(repo_path(args.input)),
        "base_generation_metadata": str(default_metadata_path(repo_path(args.input))),
        "audit_output": str(repo_path(args.audit_output)),
        "mining_date": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "selection_rules": {
            "max_rows": args.max_rows,
            "target_false_positive_share": 0.5,
            "target_false_negative_share": 0.5,
            "include_invalid": args.include_invalid,
            "max_per_category": args.max_per_category,
            "max_per_strategy": args.max_per_strategy,
            "max_per_image": args.max_per_image,
        },
        "source_rows": len(scored_rows),
        "base_wrong_rows": len(wrong_rows),
        "eligible_yes_no_base_errors": len(eligible),
        "invalid_error_rows": sum(1 for row in scored_rows if row.get("base_error_type") == "invalid_error"),
        "selected_rows": written_count,
        "unique_images": len({row.get("image_id") for row in selected_rows}),
        "target_counts": dict(sorted(Counter(row.get("target") for row in selected_rows).items())),
        "base_error_type_counts": dict(sorted(selected_error_counts.items())),
        "base_candidate_error_type_counts": dict(
            sorted(Counter(row.get("base_error_type") for row in scored_rows).items())
        ),
        "category_distribution": Counter(row.get("target_object") for row in selected_rows).most_common(50),
        "candidate_strategy_distribution": dict(
            sorted(Counter(row.get("candidate_strategy") for row in selected_rows).items())
        ),
        "train_eval_image_overlap": len(overlap),
        "train_eval_image_overlap_ids": overlap[:50],
        "audit_sample_size": min(args.audit_sample_size, len(source_rows)),
        "audit_pass_rate": None,
    }


def load_generation_metadata(input_path: Path) -> dict[str, Any]:
    metadata_path = default_metadata_path(input_path)
    if not metadata_path.exists():
        return {}
    payload = load_json(metadata_path)
    return payload if isinstance(payload, dict) else {}


def default_metadata_path(input_path: Path) -> Path:
    return input_path.with_suffix(".metadata.json")


def load_train_image_ids(path: str) -> set[str]:
    train_path = repo_path(path)
    if not train_path.exists():
        return set()
    return {str(record.get("image_id")) for record in load_jsonl(train_path) if record.get("image_id")}


if __name__ == "__main__":
    raise SystemExit(main())
