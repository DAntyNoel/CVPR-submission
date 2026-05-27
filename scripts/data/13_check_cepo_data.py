#!/usr/bin/env python3
"""Check CEPO canonical data, DPO exports, and train/eval leakage."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any

from common import load_image_id_set, load_jsonl, repo_path, summarize_records, token_count, write_json


DEFAULT_EVAL_IMAGE_ID_FILES = [
    "data/eval/coco_heldout_object_existence.jsonl",
    "data/eval/coco_hard_object_existence.jsonl",
    "data/eval/base_error_mined_object_existence.jsonl",
    "data/eval/gqa_simple_heldout.jsonl",
    "data/eval/pope_coco_random.jsonl",
    "data/eval/pope_coco_popular.jsonl",
    "data/eval/pope_coco_adversarial.jsonl",
    "data/eval/amber_discriminative.jsonl",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/cepo/claim_evidence_canonical.jsonl")
    parser.add_argument("--answer-dpo", default="data/processed/cepo/answer_dpo_train.jsonl")
    parser.add_argument("--cepo-dpo", default="data/processed/cepo/cepo_latent_dpo_train.jsonl")
    parser.add_argument("--eval-image-ids", nargs="*", default=DEFAULT_EVAL_IMAGE_ID_FILES)
    parser.add_argument("--report", default="data/processed/cepo/check_report.json")
    parser.add_argument("--expected-total", type=int, default=6000)
    parser.add_argument("--max-answer-tokens", type=int, default=80)
    parser.add_argument("--allow-missing-images", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    paths = [repo_path(args.canonical), repo_path(args.answer_dpo), repo_path(args.cepo_dpo)]
    for path in paths:
        if not path.exists():
            errors.append(f"missing file: {path}")
    if errors:
        print_report(errors, warnings)
        return 2

    canonical = load_jsonl(args.canonical)
    answer_dpo = load_jsonl(args.answer_dpo)
    cepo_dpo = load_jsonl(args.cepo_dpo)

    check_canonical(canonical, args, errors, warnings)
    check_dpo_exports(canonical, answer_dpo, cepo_dpo, errors)
    leakage = check_leakage(canonical, args.eval_image_ids, errors, warnings)

    summary = summarize_records(canonical)
    summary.update(
        {
            "num_errors": len(errors),
            "num_warnings": len(warnings),
            "errors": errors[:200],
            "warnings": warnings[:200],
            "task_type_counts": dict(sorted(Counter(row.get("task_type") for row in canonical).items())),
            "negative_type_counts": dict(sorted(Counter(row.get("negative_type") for row in canonical).items())),
            "base_task_type_counts": dict(sorted(Counter(row.get("base_task_type") for row in canonical).items())),
            "same_answer_rows": sum(1 for row in canonical if row.get("chosen_answer") == row.get("rejected_answer")),
            "leakage": leakage,
        }
    )
    write_json(args.report, summary)
    print_report(errors, warnings)
    print(f"Checked {len(canonical)} CEPO canonical records.")
    print(f"Wrote check report to {repo_path(args.report)}")
    return 1 if errors else 0


def check_canonical(
    rows: list[dict[str, Any]],
    args: argparse.Namespace,
    errors: list[str],
    warnings: list[str],
) -> None:
    if len(rows) != args.expected_total:
        warnings.append(f"expected {args.expected_total} rows but found {len(rows)}")

    ids: set[str] = set()
    task_counts = Counter(row.get("task_type") for row in rows)
    negative_counts = Counter(row.get("negative_type") for row in rows)
    for idx, row in enumerate(rows, start=1):
        record_id = str(row.get("id") or f"line-{idx}")
        if record_id in ids:
            errors.append(f"{record_id}: duplicate id")
        ids.add(record_id)

        for key in (
            "source",
            "image",
            "image_id",
            "task_type",
            "question",
            "chosen_answer",
            "rejected_answer",
            "answer_dpo_rejected_answer",
            "chosen_claims",
            "rejected_claims",
            "negative_type",
        ):
            if not row.get(key):
                errors.append(f"{record_id}: missing {key}")

        if row.get("image") and not args.allow_missing_images and not repo_path(row["image"]).exists():
            errors.append(f"{record_id}: image path does not exist: {row['image']}")

        if token_count(row.get("chosen_answer", "")) > args.max_answer_tokens:
            errors.append(f"{record_id}: chosen answer exceeds {args.max_answer_tokens} tokens")
        if token_count(row.get("rejected_answer", "")) > args.max_answer_tokens:
            errors.append(f"{record_id}: rejected answer exceeds {args.max_answer_tokens} tokens")
        if row.get("chosen_answer") == row.get("answer_dpo_rejected_answer"):
            errors.append(f"{record_id}: Answer-DPO chosen/rejected are identical")

        check_claims(record_id, row, errors)
        check_semantics(record_id, row, errors)

    expected = {
        "object_existence": 2000,
        "attribute_color": None,
        "attribute_material": None,
        "relation_spatial": 1500,
        "wrong_evidence": 1000,
    }
    if task_counts.get("object_existence") != expected["object_existence"]:
        warnings.append(f"object_existence count is {task_counts.get('object_existence')}, expected 2000")
    if task_counts.get("relation_spatial") != expected["relation_spatial"]:
        warnings.append(f"relation_spatial count is {task_counts.get('relation_spatial')}, expected 1500")
    if task_counts.get("wrong_evidence") != expected["wrong_evidence"]:
        warnings.append(f"wrong_evidence count is {task_counts.get('wrong_evidence')}, expected 1000")
    attr_count = task_counts.get("attribute_color", 0) + task_counts.get("attribute_material", 0)
    if attr_count != 1500:
        warnings.append(f"attribute count is {attr_count}, expected 1500")
    if negative_counts.get("evidence_wrong") != task_counts.get("wrong_evidence"):
        errors.append("wrong_evidence task count does not match evidence_wrong negative count")


def check_claims(record_id: str, row: dict[str, Any], errors: list[str]) -> None:
    for side in ("chosen_claims", "rejected_claims"):
        claims = row.get(side)
        if not isinstance(claims, list) or not claims:
            errors.append(f"{record_id}: {side} must be a non-empty list")
            continue
        for claim in claims:
            for key in ("span", "type", "support", "evidence"):
                if key not in claim:
                    errors.append(f"{record_id}: {side} claim missing {key}")
            evidence = claim.get("evidence")
            if not isinstance(evidence, list):
                errors.append(f"{record_id}: {side} evidence must be a list")
                continue
            if claim.get("type") == "relation":
                roles = {item.get("role") for item in evidence if isinstance(item, dict)}
                if not {"subject", "object"}.issubset(roles):
                    errors.append(f"{record_id}: relation claim missing subject/object evidence")
            elif not evidence:
                errors.append(f"{record_id}: non-relation claim has empty evidence")


def check_semantics(record_id: str, row: dict[str, Any], errors: list[str]) -> None:
    task_type = row.get("task_type")
    negative_type = row.get("negative_type")
    chosen_answer = row.get("chosen_answer")
    rejected_answer = row.get("rejected_answer")
    if task_type == "wrong_evidence":
        if chosen_answer != rejected_answer:
            errors.append(f"{record_id}: wrong-evidence row must keep chosen/rejected answer identical")
        supports = {claim.get("support") for claim in row.get("rejected_claims", [])}
        if "wrong_evidence" not in supports:
            errors.append(f"{record_id}: wrong-evidence rejected claim must use support=wrong_evidence")
    else:
        if chosen_answer == rejected_answer:
            errors.append(f"{record_id}: non-wrong-evidence row has identical answers")
        if negative_type == "evidence_wrong":
            errors.append(f"{record_id}: evidence_wrong negative used outside wrong_evidence task")

    label = row.get("label") or {}
    if negative_type == "attribute_mismatch" and label.get("positive_attribute") == label.get("negative_attribute"):
        errors.append(f"{record_id}: positive and negative attributes are identical")
    if negative_type == "relation_reversal" and label.get("relation") == label.get("negative_relation"):
        errors.append(f"{record_id}: relation and negative relation are identical")


def check_dpo_exports(
    canonical: list[dict[str, Any]],
    answer_dpo: list[dict[str, Any]],
    cepo_dpo: list[dict[str, Any]],
    errors: list[str],
) -> None:
    canonical_ids = {row.get("id") for row in canonical}
    answer_ids = {row.get("id") for row in answer_dpo}
    cepo_ids = {row.get("id") for row in cepo_dpo}
    if canonical_ids != answer_ids:
        errors.append("Answer-DPO ids do not match canonical ids")
    if canonical_ids != cepo_ids:
        errors.append("CEPO-Latent ids do not match canonical ids")
    if len(answer_dpo) != len(canonical):
        errors.append("Answer-DPO length does not match canonical length")
    if len(cepo_dpo) != len(canonical):
        errors.append("CEPO-Latent length does not match canonical length")

    for row in answer_dpo:
        record_id = row.get("id")
        if "Claims:" in str(row.get("chosen", "")) or "Claims:" in str(row.get("rejected", "")):
            errors.append(f"{record_id}: Answer-DPO export contains Claims block")
        if row.get("chosen") == row.get("rejected"):
            errors.append(f"{record_id}: Answer-DPO export has identical chosen/rejected")
    for row in cepo_dpo:
        record_id = row.get("id")
        if "Claims:" not in str(row.get("chosen", "")):
            errors.append(f"{record_id}: CEPO chosen missing Claims block")
        if "Claims:" not in str(row.get("rejected", "")):
            errors.append(f"{record_id}: CEPO rejected missing Claims block")


def check_leakage(
    rows: list[dict[str, Any]],
    eval_paths: list[str],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    if not eval_paths:
        warnings.append("no eval image-id files provided; skipped leakage check")
        return {"overlap_count": None, "overlap_first20": [], "eval_image_id_files": []}
    eval_ids = load_image_id_set(eval_paths)
    train_ids = {str(row.get("image_id")) for row in rows if row.get("image_id")}
    overlap = sorted(train_ids & eval_ids)
    if overlap:
        errors.append(f"train/eval image overlap: {len(overlap)} ids, first={overlap[:20]}")
    return {
        "train_image_ids": len(train_ids),
        "eval_image_ids": len(eval_ids),
        "overlap_count": len(overlap),
        "overlap_first20": overlap[:20],
        "eval_image_id_files": eval_paths,
    }


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
        print("No blocking CEPO data quality errors found.")


if __name__ == "__main__":
    raise SystemExit(main())
