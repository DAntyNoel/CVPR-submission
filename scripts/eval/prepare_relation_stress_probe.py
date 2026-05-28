#!/usr/bin/env python3
"""Build a locked relation-only CEPO-Probe stress set from held-out GQA rows."""

from __future__ import annotations

import argparse
import random
from collections import Counter
from typing import Any

from common import load_jsonl, write_json, write_jsonl


DEFAULT_OUTPUT = (
    "v2/tasks/review-convergence-experiments/results/relation_stress/"
    "relation_stress_probe.jsonl"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/eval/gqa_simple_heldout.jsonl")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", default=None)
    parser.add_argument("--max-rows", type=int, default=240)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = load_jsonl(args.input)
    positive_relations = [
        row
        for row in rows
        if row.get("task_type") == "relation_spatial" and normalize_yes_no(row.get("target")) == "yes"
    ]
    candidates = []
    seen_sources: set[str] = set()
    for row in positive_relations:
        source_id = str(row.get("source_id") or row.get("id"))
        if source_id in seen_sources:
            continue
        label = row.get("label") or {}
        if normalize_entity(label.get("subject")) == normalize_entity(label.get("object")):
            continue
        seen_sources.add(source_id)
        candidates.append(make_stress_row(row, "subject_object_swap"))
        candidates.append(make_stress_row(row, "left_right_reversal"))

    selected = balanced_sample(candidates, args.max_rows, rng)
    for idx, row in enumerate(selected, start=1):
        row["id"] = f"relation_stress_{idx:06d}"

    summary_output = args.summary_output or args.output.replace(".jsonl", ".summary.json")
    write_jsonl(args.output, selected)
    write_json(
        summary_output,
        {
            "input": args.input,
            "output": args.output,
            "max_rows": args.max_rows,
            "seed": args.seed,
            "total": len(selected),
            "by_stress_type": dict(Counter(row["stress_type"] for row in selected)),
            "unique_images": len({row["image_id"] for row in selected}),
            "source_relation_rows": len(positive_relations),
            "candidate_rows": len(candidates),
        },
    )
    print(f"Wrote {len(selected)} relation-stress rows to {args.output}")
    print(f"Wrote summary to {summary_output}")
    return 0


def make_stress_row(row: dict[str, Any], stress_type: str) -> dict[str, Any]:
    label = row.get("label") or {}
    subject = normalize_entity(label.get("subject"))
    obj = normalize_entity(label.get("object"))
    relation = normalize_relation(label.get("relation"))
    if not subject or not obj or relation not in {"left_of", "right_of"}:
        raise ValueError(f"Malformed relation row: {row.get('id')}")

    if stress_type == "subject_object_swap":
        evidence_subject = obj
        evidence_object = subject
        evidence_relation = relation
    elif stress_type == "left_right_reversal":
        evidence_subject = subject
        evidence_object = obj
        evidence_relation = opposite_relation(relation)
    else:
        raise ValueError(f"Unknown stress_type: {stress_type}")

    natural_relation = relation.replace("_of", "")
    return {
        "benchmark": "relation_stress_probe",
        "source": row.get("source"),
        "source_id": row.get("source_id"),
        "image": row["image"],
        "image_id": row["image_id"],
        "question": (
            f"Visual question: Is the {subject} to the {natural_relation} of the {obj}?\n"
            f"Candidate claim: {subject} {relation} {obj}\n"
            "Candidate evidence: "
            f"subject={evidence_subject}; object={evidence_object}; relation={evidence_relation}\n"
            "Decide whether the candidate evidence supports the claim in the image."
        ),
        "target": "yes",
        "target_answer": "yes",
        "target_support": "wrong_evidence",
        "target_claim": f"{subject} {relation} {obj}",
        "target_evidence_label": None,
        "target_subject": evidence_subject,
        "target_object": evidence_object,
        "target_relation": evidence_relation,
        "task_type": "wrong_evidence",
        "base_task_type": "relation_spatial",
        "negative_type": stress_type,
        "stress_type": stress_type,
    }


def balanced_sample(rows: list[dict[str, Any]], desired: int, rng: random.Random) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(str(row["stress_type"]), []).append(row)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    selected: list[dict[str, Any]] = []
    keys = sorted(buckets)
    while len(selected) < desired and any(buckets.values()):
        for key in keys:
            if buckets[key] and len(selected) < desired:
                selected.append(buckets[key].pop())
    rng.shuffle(selected)
    return selected


def normalize_yes_no(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "yes"
    if text in {"no", "n", "false", "0"}:
        return "no"
    return text


def normalize_relation(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"left", "left_of"}:
        return "left_of"
    if text in {"right", "right_of"}:
        return "right_of"
    return text


def opposite_relation(value: str) -> str:
    if value == "left_of":
        return "right_of"
    if value == "right_of":
        return "left_of"
    raise ValueError(f"Unsupported relation: {value}")


def normalize_entity(value: Any) -> str:
    return str(value or "").strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
