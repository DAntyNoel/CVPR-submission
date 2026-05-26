#!/usr/bin/env python3
"""Run lightweight data quality checks and train/eval image-overlap checks."""

from __future__ import annotations

import argparse
from collections import Counter
import sys

from common import (
    load_image_id_set,
    load_jsonl,
    repo_path,
    summarize_records,
    token_count,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--answer-dpo", default="data/processed/answer_dpo_train.jsonl")
    parser.add_argument("--evidence-dpo", default="data/processed/evidence_hint_dpo_train.jsonl")
    parser.add_argument("--eval-image-ids", nargs="*", default=[])
    parser.add_argument("--max-answer-tokens", type=int, default=40)
    parser.add_argument("--allow-missing-images", action="store_true")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    canonical_path = repo_path(args.canonical)
    answer_path = repo_path(args.answer_dpo)
    evidence_path = repo_path(args.evidence_dpo)
    for path in (canonical_path, answer_path, evidence_path):
        if not path.exists():
            errors.append(f"missing file: {path}")
    if errors:
        print_report(errors, warnings)
        return 2

    canonical = load_jsonl(canonical_path)
    answer = load_jsonl(answer_path)
    evidence = load_jsonl(evidence_path)

    check_canonical(canonical, args, errors, warnings)
    check_dpo(canonical, answer, evidence, errors)
    check_overlap(canonical, args.eval_image_ids, errors, warnings)

    summary = summarize_records(canonical)
    summary["num_errors"] = len(errors)
    summary["num_warnings"] = len(warnings)
    summary["errors"] = errors[:200]
    summary["warnings"] = warnings[:200]

    report_path = args.report
    if report_path:
        write_json(report_path, summary)

    print_report(errors, warnings)
    print(f"Checked {len(canonical)} canonical records.")
    if report_path:
        print(f"Wrote check report to {repo_path(report_path)}")
    return 1 if errors else 0


def check_canonical(
    records: list[dict],
    args: argparse.Namespace,
    errors: list[str],
    warnings: list[str],
) -> None:
    seen_ids: set[str] = set()
    task_counts = Counter(record.get("task_type") for record in records)
    for idx, record in enumerate(records, start=1):
        record_id = str(record.get("id") or f"line-{idx}")
        if record_id in seen_ids:
            errors.append(f"duplicate id: {record_id}")
        seen_ids.add(record_id)

        for key in (
            "image",
            "image_id",
            "question",
            "chosen_answer",
            "rejected_answer",
            "evidence_hint_chosen",
            "evidence_hint_rejected",
        ):
            if not record.get(key):
                errors.append(f"{record_id}: missing {key}")

        image = record.get("image")
        if image and not args.allow_missing_images and not repo_path(image).exists():
            errors.append(f"{record_id}: image path does not exist: {image}")

        chosen = record.get("chosen_answer", "")
        rejected = record.get("rejected_answer", "")
        if chosen == rejected:
            errors.append(f"{record_id}: chosen and rejected are identical")
        if token_count(chosen) > args.max_answer_tokens:
            errors.append(f"{record_id}: chosen exceeds {args.max_answer_tokens} tokens")
        if token_count(rejected) > args.max_answer_tokens:
            errors.append(f"{record_id}: rejected exceeds {args.max_answer_tokens} tokens")
        if "Evidence hint:" not in record.get("evidence_hint_chosen", ""):
            errors.append(f"{record_id}: chosen hint missing Evidence hint prefix")
        if "Evidence hint:" not in record.get("evidence_hint_rejected", ""):
            errors.append(f"{record_id}: rejected hint missing Evidence hint prefix")
        check_label(record_id, record, errors)

    total = len(records)
    if total:
        object_frac = task_counts.get("object_existence", 0) / total
        if not 0.55 <= object_frac <= 0.85:
            warnings.append(
                f"object_existence ratio is {object_frac:.3f}; target is roughly 0.70"
            )


def check_label(record_id: str, record: dict, errors: list[str]) -> None:
    label = record.get("label") or {}
    task_type = record.get("task_type")
    if task_type == "object_existence":
        pos = label.get("positive_object")
        neg = label.get("negative_object")
        visible = set(label.get("visible_objects") or [])
        if pos == neg:
            errors.append(f"{record_id}: positive and negative object are identical")
        if neg in visible:
            errors.append(f"{record_id}: rejected object is annotated visible: {neg}")
    elif str(task_type).startswith("attribute_"):
        if label.get("positive_attribute") == label.get("negative_attribute"):
            errors.append(f"{record_id}: positive and negative attributes are identical")
    elif task_type == "relation_spatial":
        if label.get("relation") == label.get("negative_relation"):
            errors.append(f"{record_id}: positive and negative relations are identical")


def check_dpo(
    canonical: list[dict],
    answer: list[dict],
    evidence: list[dict],
    errors: list[str],
) -> None:
    canonical_ids = {record.get("id") for record in canonical}
    answer_ids = {record.get("id") for record in answer}
    evidence_ids = {record.get("id") for record in evidence}
    if answer_ids != canonical_ids:
        errors.append("Answer-DPO ids do not match canonical ids")
    if evidence_ids != canonical_ids:
        errors.append("Evidence-Hint DPO ids do not match canonical ids")
    if len(answer) != len(canonical):
        errors.append("Answer-DPO length does not match canonical length")
    if len(evidence) != len(canonical):
        errors.append("Evidence-Hint DPO length does not match canonical length")

    for record in answer:
        record_id = record.get("id")
        text = "\n".join(str(record.get(key, "")) for key in ("prompt", "chosen", "rejected"))
        if "Evidence hint:" in text:
            errors.append(f"{record_id}: Answer-DPO contains Evidence hint")

    for record in evidence:
        record_id = record.get("id")
        prompt = str(record.get("prompt", ""))
        if "Evidence hint:" in prompt:
            errors.append(f"{record_id}: Evidence-Hint prompt contains Evidence hint")
        if "Evidence hint:" not in str(record.get("chosen", "")):
            errors.append(f"{record_id}: Evidence-Hint chosen missing Evidence hint")
        if "Evidence hint:" not in str(record.get("rejected", "")):
            errors.append(f"{record_id}: Evidence-Hint rejected missing Evidence hint")


def check_overlap(
    canonical: list[dict],
    eval_image_id_paths: list[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not eval_image_id_paths:
        warnings.append("no eval image-id files provided; skipped leakage overlap check")
        return
    eval_ids = load_image_id_set(eval_image_id_paths)
    train_ids = {str(record.get("image_id")) for record in canonical}
    overlap = sorted(train_ids & eval_ids)
    if overlap:
        errors.append(f"train/eval image overlap: {len(overlap)} ids, first={overlap[:20]}")


def print_report(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print("ERRORS:")
        for error in errors[:50]:
            print(f"  - {error}")
        if len(errors) > 50:
            print(f"  ... {len(errors) - 50} more")
    if warnings:
        print("WARNINGS:")
        for warning in warnings[:50]:
            print(f"  - {warning}")
        if len(warnings) > 50:
            print(f"  ... {len(warnings) - 50} more")
    if not errors:
        print("No blocking data quality errors found.")


if __name__ == "__main__":
    raise SystemExit(main())
