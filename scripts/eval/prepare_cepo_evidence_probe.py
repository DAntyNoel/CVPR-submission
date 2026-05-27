#!/usr/bin/env python3
"""Prepare CEPO evidence-probe eval files from canonical claim-evidence data."""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from typing import Any

from common import load_jsonl, write_json, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/cepo/claim_evidence_canonical.jsonl")
    parser.add_argument("--supported-output", default="data/eval/cepo_evidence_probe.jsonl")
    parser.add_argument("--wrong-output", default="data/eval/cepo_wrong_evidence_probe.jsonl")
    parser.add_argument("--summary-output", default="data/eval/cepo_evidence_probe.summary.json")
    parser.add_argument("--supported-size", type=int, default=600)
    parser.add_argument("--wrong-size", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    records = load_jsonl(args.canonical)
    supported = build_supported_probe(records, args.supported_size, rng)
    wrong = build_wrong_probe(records, args.wrong_size, rng)

    write_jsonl(args.supported_output, supported)
    write_jsonl(args.wrong_output, wrong)
    summary = {
        "supported_total": len(supported),
        "wrong_total": len(wrong),
        "supported_by_task": count_by(supported, "base_task_type"),
        "wrong_by_task": count_by(wrong, "base_task_type"),
        "supported_output": args.supported_output,
        "wrong_output": args.wrong_output,
    }
    write_json(args.summary_output, summary)
    print(f"Wrote {len(supported)} supported evidence-probe rows to {args.supported_output}")
    print(f"Wrote {len(wrong)} wrong-evidence probe rows to {args.wrong_output}")
    print(f"Wrote summary to {args.summary_output}")
    return 0


def build_supported_probe(records: list[dict[str, Any]], desired: int, rng: random.Random) -> list[dict[str, Any]]:
    candidates = [row for row in records if row.get("task_type") != "wrong_evidence"]
    return balanced_sample([make_probe_row(row, "chosen_claims", "supported") for row in candidates], desired, rng)


def build_wrong_probe(records: list[dict[str, Any]], desired: int, rng: random.Random) -> list[dict[str, Any]]:
    candidates = [row for row in records if row.get("task_type") == "wrong_evidence"]
    return balanced_sample([make_probe_row(row, "rejected_claims", "wrong_evidence") for row in candidates], desired, rng)


def balanced_sample(rows: list[dict[str, Any]], desired: int, rng: random.Random) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("base_task_type") or row.get("task_type"))].append(row)
    for bucket in buckets.values():
        rng.shuffle(bucket)

    selected: list[dict[str, Any]] = []
    keys = sorted(buckets)
    while len(selected) < desired and any(buckets.values()):
        for key in keys:
            if buckets[key] and len(selected) < desired:
                selected.append(buckets[key].pop())
    rng.shuffle(selected)
    for idx, row in enumerate(selected, start=1):
        row["id"] = f"{row['id']}_probe_{idx:06d}"
    return selected[:desired]


def make_probe_row(row: dict[str, Any], claim_key: str, target_support: str) -> dict[str, Any]:
    one = row[claim_key][0]
    target = target_fields(one)
    visual_question = yes_no_question(row, one)
    candidate = candidate_text(one)
    question = (
        f"Visual question: {visual_question}\n"
        f"Candidate claim: {one['span']}\n"
        f"Candidate evidence: {candidate}\n"
        "Decide whether the candidate evidence supports the claim in the image."
    )
    return {
        "id": row["id"],
        "benchmark": "cepo_evidence_probe",
        "source": row.get("source"),
        "image": row["image"],
        "image_id": row["image_id"],
        "question": question,
        "target": "yes",
        "target_answer": "yes",
        "target_support": target_support,
        "target_claim": one["span"],
        "target_evidence_label": target["evidence_label"],
        "target_subject": target["subject"],
        "target_object": target["object"],
        "target_relation": target["relation"],
        "task_type": row.get("task_type"),
        "base_task_type": row.get("base_task_type", row.get("task_type")),
        "negative_type": row.get("negative_type"),
    }


def yes_no_question(row: dict[str, Any], one: dict[str, Any]) -> str:
    claim_type = one.get("type")
    if claim_type == "object":
        label = object_from_claim(one["span"])
        return f"Is there {article(label)} in the image?"
    if claim_type == "attribute":
        label, attr = attribute_from_claim(one["span"])
        attr = one.get("attribute") or attr
        return f"Is the {label} {attr}?"
    if claim_type == "relation":
        subject, relation, obj = relation_from_claim(one["span"])
        relation = relation.replace("_of", "")
        return f"Is the {subject} to the {relation} of the {obj}?"
    return str(row.get("question") or "")


def candidate_text(one: dict[str, Any]) -> str:
    evidence = one.get("evidence") or []
    if one.get("type") == "relation":
        fields = target_fields(one)
        return f"subject={fields['subject']}; object={fields['object']}; relation={fields['relation']}"
    label = evidence[0].get("label") if evidence else "none"
    if one.get("type") == "attribute":
        return f"label={label}; attribute={one.get('attribute')}"
    return f"label={label}"


def target_fields(one: dict[str, Any]) -> dict[str, str | None]:
    evidence = one.get("evidence") or []
    subject = next((item.get("label") for item in evidence if item.get("role") == "subject"), None)
    obj = next((item.get("label") for item in evidence if item.get("role") == "object"), None)
    target = next((item.get("label") for item in evidence if item.get("role") == "target"), None)
    return {
        "evidence_label": target,
        "subject": subject,
        "object": obj,
        "relation": one.get("relation"),
    }


def article(label: str | None) -> str:
    text = str(label or "object").strip()
    if text.endswith("s") and text != "bus":
        return text
    return f"{'an' if text[:1].lower() in {'a', 'e', 'i', 'o', 'u'} else 'a'} {text}"


def object_from_claim(text: str) -> str:
    normalized = str(text).strip()
    if normalized.endswith(" visible"):
        return normalized[: -len(" visible")].strip()
    return normalized.split()[0] if normalized.split() else "object"


def attribute_from_claim(text: str) -> tuple[str, str]:
    normalized = str(text).strip()
    if " is " in normalized:
        obj, attr = normalized.rsplit(" is ", 1)
        return obj.strip(), attr.strip()
    parts = normalized.split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return "object", "visible"


def relation_from_claim(text: str) -> tuple[str, str, str]:
    parts = str(text).strip().split()
    if len(parts) >= 3:
        return " ".join(parts[:-2]), parts[-2], parts[-1]
    return "object", "left_of", "object"


def last_claim_token(text: str) -> str:
    return str(text).split()[-1] if str(text).split() else "visible"


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
