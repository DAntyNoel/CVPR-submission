#!/usr/bin/env python3
"""Complete and summarize the audit sheet using canonical COCO labels."""

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


def mentions(text: Any, name: str) -> bool:
    name = clean_name(name)
    if not name:
        return False
    return f" {name} " in f" {clean_name(text)} "


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
        "audit_basis": "annotation-grounded COCO label consistency check",
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
