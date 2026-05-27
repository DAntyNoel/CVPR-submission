#!/usr/bin/env python3
"""Complete and summarize the audit sheet using canonical mixed labels."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from typing import Any

from common import clean_name, load_jsonl, repo_path, write_json


AUDIT_COLUMNS = ("chosen_correct", "rejected_wrong", "hint_correct")
DEFAULT_THRESHOLDS = {
    "chosen_correct": 0.85,
    "rejected_wrong": 0.90,
    "hint_correct": 0.90,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--audit", default="data/audit/audit_200.csv")
    parser.add_argument("--summary", default="data/audit/audit_200_summary.json")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite any existing audit labels instead of only filling blanks.",
    )
    args = parser.parse_args()

    canonical_path = repo_path(args.canonical)
    audit_path = repo_path(args.audit)
    if not canonical_path.exists():
        print(f"Missing canonical file: {canonical_path}", file=sys.stderr)
        return 2
    if not audit_path.exists():
        print(f"Missing audit sheet: {audit_path}", file=sys.stderr)
        return 2

    records = {str(record.get("id")): record for record in load_jsonl(canonical_path)}
    with audit_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing_columns = [column for column in AUDIT_COLUMNS if column not in fieldnames]
    if missing_columns:
        print(f"Audit sheet is missing columns: {missing_columns}", file=sys.stderr)
        return 2

    counters: dict[str, Counter[str]] = {column: Counter() for column in AUDIT_COLUMNS}
    failures: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for row in rows:
        row_id = str(row.get("id") or "")
        record = records.get(row_id)
        if not record:
            missing_ids.append(row_id)
            continue

        labels, reasons = audit_record(record, row)
        for column, value in labels.items():
            if args.overwrite or not str(row.get(column, "")).strip():
                row[column] = value
            counters[column][normalize_label(row.get(column, ""))] += 1

        if reasons:
            failures.append({"id": row_id, "reasons": reasons})

    with audit_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = build_summary(rows, counters, failures, missing_ids)
    write_json(args.summary, summary)

    print(f"Completed audit labels for {len(rows) - len(missing_ids)} rows.")
    print(f"Wrote audit sheet to {audit_path}")
    print(f"Wrote audit summary to {repo_path(args.summary)}")
    for column in AUDIT_COLUMNS:
        rate = summary["metrics"][column]["rate"]
        threshold = summary["thresholds"][column]
        print(f"{column}: {rate:.3f} (threshold {threshold:.2f})")

    if missing_ids:
        print(f"Missing canonical records for {len(missing_ids)} audit ids.", file=sys.stderr)
        return 1
    if not summary["passes_thresholds"]:
        print("Audit metrics did not pass configured thresholds.", file=sys.stderr)
        return 1
    return 0


def audit_record(record: dict[str, Any], row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    if record.get("source") == "gqa":
        return audit_gqa_record(record, row)
    return audit_coco_record(record, row)


def audit_coco_record(record: dict[str, Any], row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    label = record.get("label") or {}
    visible = {clean_name(value) for value in (label.get("visible_objects") or [])}
    positive = clean_name(label.get("positive_object"))
    negative = clean_name(label.get("negative_object"))

    chosen = row.get("chosen") or record.get("chosen_answer", "")
    rejected = row.get("rejected") or record.get("rejected_answer", "")
    chosen_hint = row.get("chosen_hint") or record.get("evidence_hint_chosen", "")
    rejected_hint = row.get("rejected_hint") or record.get("evidence_hint_rejected", "")

    chosen_correct = bool(positive and positive in visible and mentions(chosen, positive))
    rejected_wrong = bool(negative and negative not in visible and mentions(rejected, negative))
    hint_correct = bool(
        mentions(chosen_hint, positive)
        and mentions(rejected_hint, negative)
        and "annotated visible object" in chosen_hint.lower()
        and "not annotated as visible" in rejected_hint.lower()
    )

    labels = {
        "chosen_correct": yes_no(chosen_correct),
        "rejected_wrong": yes_no(rejected_wrong),
        "hint_correct": yes_no(hint_correct),
    }
    reasons = []
    if not chosen_correct:
        reasons.append("chosen answer does not match annotated positive object")
    if not rejected_wrong:
        reasons.append("rejected answer does not match an unannotated negative object")
    if not hint_correct:
        reasons.append("evidence hint does not match canonical labels")
    return labels, reasons


def audit_gqa_record(record: dict[str, Any], row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    task_type = str(record.get("task_type") or "")
    if task_type.startswith("attribute_"):
        return audit_gqa_attribute_record(record, row)
    if task_type == "relation_spatial":
        return audit_gqa_relation_record(record, row)
    return failed_labels(f"unsupported GQA task_type: {task_type}")


def audit_gqa_attribute_record(
    record: dict[str, Any],
    row: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    label = record.get("label") or {}
    obj = clean_name(label.get("object"))
    positive = clean_name(label.get("positive_attribute"))
    negative = clean_name(label.get("negative_attribute"))

    chosen = row.get("chosen") or record.get("chosen_answer", "")
    rejected = row.get("rejected") or record.get("rejected_answer", "")
    chosen_hint = row.get("chosen_hint") or record.get("evidence_hint_chosen", "")
    rejected_hint = row.get("rejected_hint") or record.get("evidence_hint_rejected", "")

    chosen_correct = bool(obj and positive and mentions(chosen, obj) and mentions(chosen, positive))
    rejected_wrong = bool(obj and negative and mentions(rejected, obj) and mentions(rejected, negative))
    hint_correct = bool(
        mentions(chosen_hint, obj)
        and mentions(chosen_hint, positive)
        and mentions(rejected_hint, obj)
        and mentions(rejected_hint, negative)
        and "annotated attribute" in chosen_hint.lower()
        and "mismatched attribute" in rejected_hint.lower()
    )

    labels = {
        "chosen_correct": yes_no(chosen_correct),
        "rejected_wrong": yes_no(rejected_wrong),
        "hint_correct": yes_no(hint_correct),
    }
    reasons = []
    if not chosen_correct:
        reasons.append("chosen answer does not match annotated GQA attribute")
    if not rejected_wrong:
        reasons.append("rejected answer does not match the mismatched GQA attribute")
    if not hint_correct:
        reasons.append("evidence hint does not match GQA attribute labels")
    return labels, reasons


def audit_gqa_relation_record(
    record: dict[str, Any],
    row: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    label = record.get("label") or {}
    subject = clean_name(label.get("subject"))
    obj = clean_name(label.get("object"))
    relation = clean_name(label.get("relation"))
    negative_relation = clean_name(label.get("negative_relation"))

    chosen = row.get("chosen") or record.get("chosen_answer", "")
    rejected = row.get("rejected") or record.get("rejected_answer", "")
    chosen_hint = row.get("chosen_hint") or record.get("evidence_hint_chosen", "")
    rejected_hint = row.get("rejected_hint") or record.get("evidence_hint_rejected", "")

    chosen_correct = bool(
        subject
        and obj
        and relation
        and mentions(chosen, subject)
        and mentions(chosen, obj)
        and mentions_relation(chosen, relation)
    )
    rejected_wrong = bool(
        subject
        and obj
        and negative_relation
        and mentions(rejected, subject)
        and mentions(rejected, obj)
        and mentions_relation(rejected, negative_relation)
    )
    hint_correct = bool(
        mentions(chosen_hint, subject)
        and mentions(chosen_hint, obj)
        and mentions_relation(chosen_hint, relation)
        and mentions(rejected_hint, subject)
        and mentions(rejected_hint, obj)
        and mentions_relation(rejected_hint, negative_relation)
        and "annotated relation" in chosen_hint.lower()
        and "contradicted relation" in rejected_hint.lower()
    )

    labels = {
        "chosen_correct": yes_no(chosen_correct),
        "rejected_wrong": yes_no(rejected_wrong),
        "hint_correct": yes_no(hint_correct),
    }
    reasons = []
    if not chosen_correct:
        reasons.append("chosen answer does not match annotated GQA relation")
    if not rejected_wrong:
        reasons.append("rejected answer does not match the flipped GQA relation")
    if not hint_correct:
        reasons.append("evidence hint does not match GQA relation labels")
    return labels, reasons


def failed_labels(reason: str) -> tuple[dict[str, str], list[str]]:
    return (
        {column: "no" for column in AUDIT_COLUMNS},
        [reason],
    )


def mentions(text: Any, name: str) -> bool:
    name = clean_name(name)
    if not name:
        return False
    return f" {name} " in f" {clean_name(text)} "


def mentions_relation(text: Any, relation: str) -> bool:
    relation = clean_name(relation)
    if relation in {"left", "right"}:
        return mentions(text, relation)
    return mentions(text, relation)


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "pass", "passed"}:
        return "yes"
    if text in {"no", "n", "false", "0", "fail", "failed"}:
        return "no"
    return "blank"


def build_summary(
    rows: list[dict[str, str]],
    counters: dict[str, Counter[str]],
    failures: list[dict[str, Any]],
    missing_ids: list[str],
) -> dict[str, Any]:
    metrics = {}
    for column in AUDIT_COLUMNS:
        yes = counters[column]["yes"]
        no = counters[column]["no"]
        total = yes + no
        metrics[column] = {
            "yes": yes,
            "no": no,
            "blank": counters[column]["blank"],
            "rate": round(yes / total, 4) if total else 0.0,
        }

    threshold_status = {
        column: metrics[column]["rate"] >= threshold
        for column, threshold in DEFAULT_THRESHOLDS.items()
    }
    return {
        "total_rows": len(rows),
        "audit_basis": "annotation/scene-graph-grounded mixed COCO/GQA label consistency check",
        "source_counts": dict(sorted(Counter(row.get("source", "unknown") for row in rows).items())),
        "metrics": metrics,
        "thresholds": DEFAULT_THRESHOLDS,
        "threshold_status": threshold_status,
        "passes_thresholds": all(threshold_status.values()) and not missing_ids,
        "missing_ids": missing_ids[:50],
        "num_missing_ids": len(missing_ids),
        "failures": failures[:50],
        "num_failures": len(failures),
    }


if __name__ == "__main__":
    raise SystemExit(main())
