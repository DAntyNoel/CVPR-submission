#!/usr/bin/env python3
"""Complete and summarize the CEPO claim-evidence audit sheet.

This is an annotation-consistency audit, not an independent image relabeling
pass. It checks that sampled rows are internally consistent with the canonical
claim/evidence labels used to build ClaimEvidence-6K.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from typing import Any

from common import clean_name, load_jsonl, repo_path, write_json


AUDIT_COLUMNS = (
    "chosen_answer_correct",
    "rejected_answer_wrong",
    "chosen_evidence_correct",
    "rejected_error_correct",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/cepo/claim_evidence_canonical.jsonl")
    parser.add_argument("--audit", default="data/processed/cepo/claim_evidence_audit_200.csv")
    parser.add_argument("--summary", default="data/processed/cepo/claim_evidence_audit_200_summary.json")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    canonical_path = repo_path(args.canonical)
    audit_path = repo_path(args.audit)
    if not canonical_path.exists():
        print(f"Missing canonical file: {canonical_path}", file=sys.stderr)
        return 2
    if not audit_path.exists():
        print(f"Missing audit sheet: {audit_path}", file=sys.stderr)
        return 2

    records = {str(row.get("id")): row for row in load_jsonl(canonical_path)}
    with audit_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing_columns = [column for column in AUDIT_COLUMNS if column not in fieldnames]
    if missing_columns:
        print(f"Audit sheet is missing columns: {missing_columns}", file=sys.stderr)
        return 2

    missing_ids: list[str] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        row_id = str(row.get("id") or "")
        record = records.get(row_id)
        if record is None:
            missing_ids.append(row_id)
            continue
        labels, reasons = audit_record(record, row)
        for column, value in labels.items():
            if args.overwrite or not str(row.get(column) or "").strip():
                row[column] = value
        if reasons:
            failures.append({"id": row_id, "reasons": reasons})

    with audit_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, failures, missing_ids)
    write_json(args.summary, summary)

    print(f"Completed CEPO audit labels for {len(rows) - len(missing_ids)} rows.")
    print(f"Wrote audit sheet to {audit_path}")
    print(f"Wrote audit summary to {repo_path(args.summary)}")
    for column, values in summary["metrics"].items():
        print(f"{column}: {values['yes']}/{values['audited']} = {values['rate']:.3f}")

    if missing_ids:
        print(f"Missing canonical records for {len(missing_ids)} audit ids.", file=sys.stderr)
        return 1
    if failures:
        print(f"Found {len(failures)} audit consistency failures.", file=sys.stderr)
        return 1
    return 0


def audit_record(record: dict[str, Any], row: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    chosen_claim = first_claim(record, "chosen_claims")
    rejected_claim = first_claim(record, "rejected_claims")
    negative_type = str(record.get("negative_type") or "")

    labels = {
        "chosen_answer_correct": yes_no(answer_matches_claim(row.get("chosen_answer"), chosen_claim)),
        "rejected_answer_wrong": "na"
        if negative_type == "evidence_wrong"
        else yes_no(answer_matches_claim(row.get("rejected_answer"), rejected_claim)),
        "chosen_evidence_correct": yes_no(evidence_matches_claim(row.get("chosen_evidence"), chosen_claim)),
        "rejected_error_correct": yes_no(rejected_error_matches(negative_type, row, rejected_claim)),
    }

    reasons = []
    if labels["chosen_answer_correct"] != "yes":
        reasons.append("chosen answer does not match chosen claim")
    if labels["rejected_answer_wrong"] == "no":
        reasons.append("rejected answer does not match rejected claim")
    if labels["chosen_evidence_correct"] != "yes":
        reasons.append("chosen evidence does not match chosen claim")
    if labels["rejected_error_correct"] != "yes":
        reasons.append("rejected error type does not match canonical negative")
    return labels, reasons


def first_claim(record: dict[str, Any], key: str) -> dict[str, Any]:
    claims = record.get(key) or []
    if not claims:
        return {}
    claim = claims[0]
    return claim if isinstance(claim, dict) else {}


def answer_matches_claim(answer: Any, claim: dict[str, Any]) -> bool:
    text = clean_name(answer)
    span = clean_name(claim.get("span"))
    claim_type = claim.get("type")
    if not text or not span:
        return False
    if claim_type == "object":
        return mentions(text, span.replace(" visible", ""))
    if claim_type == "attribute":
        obj, attr = split_attribute_span(span)
        return mentions(text, obj) and mentions(text, attr)
    if claim_type == "relation":
        subject, relation, obj = split_relation_span(span)
        return mentions(text, subject) and mentions(text, obj) and relation_in_text(text, relation)
    return False


def evidence_matches_claim(evidence_text: Any, claim: dict[str, Any]) -> bool:
    text = clean_audit_text(evidence_text)
    if not text:
        return False
    expected = [clean_name(item.get("label")) for item in claim.get("evidence") or [] if isinstance(item, dict)]
    if not expected or not all(mentions(text, label) for label in expected):
        return False
    if claim.get("type") == "attribute":
        return mentions(text, claim.get("attribute"))
    if claim.get("type") == "relation":
        return relation_in_text(text, claim.get("relation"))
    return True


def rejected_error_matches(negative_type: str, row: dict[str, str], claim: dict[str, Any]) -> bool:
    support = clean_name(row.get("rejected_support") or claim.get("support"))
    rejected_evidence = row.get("rejected_evidence")
    if negative_type == "evidence_wrong":
        return support == "wrong evidence" and evidence_matches_claim(rejected_evidence, claim)
    if negative_type in {"answer_wrong", "attribute_mismatch", "relation_reversal"}:
        return support == "contradicted" and evidence_matches_claim(rejected_evidence, claim)
    return False


def split_attribute_span(span: str) -> tuple[str, str]:
    if " is " in span:
        obj, attr = span.split(" is ", 1)
        return obj.strip(), attr.strip()
    parts = span.split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return span, ""


def split_relation_span(span: str) -> tuple[str, str, str]:
    for relation in ("left of", "right of", "left_of", "right_of"):
        clean_relation = clean_name(relation)
        marker = f" {clean_relation} "
        if marker in f" {span} ":
            before, after = span.split(clean_relation, 1)
            return before.strip(), clean_relation, after.strip()
    parts = span.split()
    if len(parts) >= 3:
        return parts[0], parts[1], " ".join(parts[2:])
    return span, "", ""


def relation_in_text(text: Any, relation: Any) -> bool:
    text = clean_audit_text(text)
    relation = clean_name(relation)
    if relation in {"left", "left of", "left_of"}:
        return "left" in text
    if relation in {"right", "right of", "right_of"}:
        return "right" in text
    return bool(relation and relation in text)


def mentions(text: Any, phrase: Any) -> bool:
    phrase = clean_name(phrase)
    text = clean_audit_text(text)
    return bool(phrase and f" {phrase} " in f" {text} ")


def clean_audit_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("=", " ").replace(";", " ").replace(",", " ")
    return clean_name(text)


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def summarize(
    rows: list[dict[str, str]],
    failures: list[dict[str, Any]],
    missing_ids: list[str],
) -> dict[str, Any]:
    column_counts: dict[str, Counter[str]] = {column: Counter() for column in AUDIT_COLUMNS}
    by_task: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: {column: Counter() for column in AUDIT_COLUMNS})
    for row in rows:
        task_type = row.get("task_type") or "unknown"
        for column in AUDIT_COLUMNS:
            value = clean_name(row.get(column)) or "blank"
            column_counts[column][value] += 1
            by_task[task_type][column][value] += 1

    metrics = {column: metric_from_counts(counts) for column, counts in column_counts.items()}
    task_metrics = {
        task: {column: metric_from_counts(counts) for column, counts in columns.items()}
        for task, columns in sorted(by_task.items())
    }
    return {
        "audit_type": "annotation_consistency",
        "total_rows": len(rows),
        "metrics": metrics,
        "by_task_type": task_metrics,
        "failures": failures,
        "missing_ids": missing_ids,
        "passes_annotation_consistency": not failures and not missing_ids,
    }


def metric_from_counts(counts: Counter[str]) -> dict[str, Any]:
    yes = counts["yes"]
    no = counts["no"]
    audited = yes + no
    return {
        "yes": yes,
        "no": no,
        "na": counts["na"],
        "blank": counts["blank"],
        "audited": audited,
        "rate": round(yes / audited, 6) if audited else 0.0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
