#!/usr/bin/env python3
"""Export CEPO-Dual answer plus evidence-verifier DPO rows."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from typing import Any

from common import load_jsonl, repo_path, token_count, write_json, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/cepo/claim_evidence_canonical.jsonl")
    parser.add_argument("--answer-dpo", default="data/processed/cepo/answer_dpo_train.jsonl")
    parser.add_argument("--output-dir", default="data/processed/cepo_dual")
    parser.add_argument("--answer-count", type=int, default=6000)
    parser.add_argument("--supported-verifier-count", type=int, default=1000)
    parser.add_argument("--wrong-evidence-verifier-count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    canonical = load_jsonl(args.canonical)
    answer_rows = load_jsonl(args.answer_dpo)

    selected_answer = select_rows(answer_rows, args.answer_count, rng, "answer rows")
    answer_exports = [export_answer_row(row) for row in selected_answer]

    supported_candidates = [
        export_verifier_row(row, row["chosen_claims"][0], "supported", "supported_verifier")
        for row in canonical
        if row.get("task_type") != "wrong_evidence"
        and row.get("chosen_claims")
        and row["chosen_claims"][0].get("support") == "supported"
    ]
    wrong_candidates = [
        export_verifier_row(row, row["rejected_claims"][0], "wrong_evidence", "wrong_evidence_verifier")
        for row in canonical
        if row.get("rejected_claims")
        and row["rejected_claims"][0].get("support") == "wrong_evidence"
    ]

    supported_exports = select_rows(
        supported_candidates,
        args.supported_verifier_count,
        rng,
        "supported verifier rows",
    )
    wrong_exports = select_rows(
        wrong_candidates,
        args.wrong_evidence_verifier_count,
        rng,
        "wrong-evidence verifier rows",
    )

    records = answer_exports + supported_exports + wrong_exports
    validate_records(records)
    rng.shuffle(records)

    output_dir = repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "cepo_dual_dpo_train.jsonl"
    summary_path = output_dir / "cepo_dual_summary.json"
    write_jsonl(train_path, records)
    write_json(summary_path, build_summary(records, args))

    print(f"Wrote {len(records)} CEPO-Dual DPO rows to {train_path}")
    print(f"Wrote CEPO-Dual summary to {summary_path}")
    return 0


def select_rows(rows: list[dict[str, Any]], count: int, rng: random.Random, label: str) -> list[dict[str, Any]]:
    if count < 0:
        raise ValueError(f"{label}: requested count must be non-negative")
    if len(rows) < count:
        raise RuntimeError(f"{label}: only {len(rows)} candidates available; requested {count}")
    if len(rows) == count:
        return list(rows)
    rows = list(rows)
    rng.shuffle(rows)
    return rows[:count]


def export_answer_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"cepo_dual_answer_{row['id']}",
        "image": row["image"],
        "prompt": row["prompt"],
        "chosen": row["chosen"],
        "rejected": row["rejected"],
        "source": row.get("source"),
        "task_type": row.get("task_type"),
        "negative_type": row.get("negative_type"),
        "slice": "short_answer",
        "source_record_id": row["id"],
    }


def export_verifier_row(
    row: dict[str, Any],
    claim: dict[str, Any],
    target_support: str,
    slice_name: str,
) -> dict[str, Any]:
    rejected_support = "wrong_evidence" if target_support == "supported" else "supported"
    chosen = support_payload(claim, target_support)
    rejected = support_payload(claim, rejected_support)
    return {
        "id": f"cepo_dual_{slice_name}_{row['id']}",
        "image": row["image"],
        "prompt": verifier_prompt(row, claim),
        "chosen": json.dumps(chosen, ensure_ascii=False, sort_keys=True),
        "rejected": json.dumps(rejected, ensure_ascii=False, sort_keys=True),
        "source": row.get("source"),
        "task_type": "evidence_verifier",
        "base_task_type": row.get("base_task_type") or row.get("task_type"),
        "negative_type": "evidence_support_label",
        "slice": slice_name,
        "source_record_id": row["id"],
        "target_support": target_support,
        "claim_type": claim.get("type"),
    }


def support_payload(claim: dict[str, Any], support: str) -> dict[str, str]:
    payload = {"support": support}
    if claim.get("type") == "relation" and claim.get("relation"):
        payload["relation"] = str(claim["relation"])
    return payload


def verifier_prompt(row: dict[str, Any], claim: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<image>",
            f"Question: {row['question']}",
            f"Candidate claim: {claim['span']}",
            f"Candidate evidence: {candidate_evidence_text(claim)}",
            "Does the candidate evidence support the claim in the image?",
            "Answer:",
        ]
    )


def candidate_evidence_text(claim: dict[str, Any]) -> str:
    evidence = claim.get("evidence") or []
    if claim.get("type") == "relation":
        subject = evidence_label(evidence, "subject")
        obj = evidence_label(evidence, "object")
        relation = claim.get("relation") or "unknown"
        return f"subject={subject}; object={obj}; relation={relation}"

    label = evidence[0].get("label") if evidence and isinstance(evidence[0], dict) else "unknown"
    parts = [f"label={label}"]
    if claim.get("type") == "attribute" and claim.get("attribute"):
        parts.append(f"attribute={claim['attribute']}")
    return "; ".join(parts)


def evidence_label(evidence: list[dict[str, Any]], role: str) -> str:
    for item in evidence:
        if item.get("role") == role and item.get("label"):
            return str(item["label"])
    return "unknown"


def validate_records(records: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for row in records:
        record_id = str(row.get("id") or "")
        if not record_id:
            raise ValueError("record missing id")
        if record_id in ids:
            raise ValueError(f"duplicate id: {record_id}")
        ids.add(record_id)

        for key in ("image", "prompt", "chosen", "rejected", "slice"):
            if not row.get(key):
                raise ValueError(f"{record_id}: missing {key}")
        if row["chosen"] == row["rejected"]:
            raise ValueError(f"{record_id}: chosen and rejected are identical")
        if not repo_path(row["image"]).exists():
            raise FileNotFoundError(f"{record_id}: image does not exist: {row['image']}")

        if row.get("slice") != "short_answer":
            for side in ("chosen", "rejected"):
                payload = json.loads(row[side])
                if payload.get("support") not in {"supported", "wrong_evidence"}:
                    raise ValueError(f"{record_id}: invalid verifier support in {side}: {payload}")


def build_summary(records: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    slices = Counter(row.get("slice") for row in records)
    base_tasks = Counter(row.get("base_task_type") for row in records if row.get("base_task_type"))
    target_supports = Counter(row.get("target_support") for row in records if row.get("target_support"))
    return {
        "total": len(records),
        "seed": args.seed,
        "requested": {
            "answer_rows": args.answer_count,
            "supported_verifier_rows": args.supported_verifier_count,
            "wrong_evidence_verifier_rows": args.wrong_evidence_verifier_count,
        },
        "slice_counts": dict(sorted(slices.items())),
        "verifier_base_task_counts": dict(sorted(base_tasks.items())),
        "verifier_target_support_counts": dict(sorted(target_supports.items())),
        "avg_prompt_tokens": avg(token_count(row["prompt"]) for row in records),
        "avg_chosen_tokens": avg(token_count(row["chosen"]) for row in records),
        "avg_rejected_tokens": avg(token_count(row["rejected"]) for row in records),
    }


def avg(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
