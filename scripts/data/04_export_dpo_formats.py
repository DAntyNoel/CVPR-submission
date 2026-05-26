#!/usr/bin/env python3
"""Export canonical pairs to Answer-DPO and Evidence-Hint DPO JSONL."""

from __future__ import annotations

import argparse
import sys

from common import load_jsonl, repo_path, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--answer-output", default="data/processed/answer_dpo_train.jsonl")
    parser.add_argument(
        "--evidence-output",
        default="data/processed/evidence_hint_dpo_train.jsonl",
    )
    parser.add_argument("--include-metadata", action="store_true")
    args = parser.parse_args()

    canonical_path = repo_path(args.input)
    if not canonical_path.exists():
        print(f"Missing canonical input: {canonical_path}", file=sys.stderr)
        return 2

    records = load_jsonl(canonical_path)
    answer_records = [export_answer(record, args.include_metadata) for record in records]
    evidence_records = [export_evidence(record, args.include_metadata) for record in records]

    answer_count = write_jsonl(args.answer_output, answer_records)
    evidence_count = write_jsonl(args.evidence_output, evidence_records)
    print(f"Wrote {answer_count} Answer-DPO records to {repo_path(args.answer_output)}")
    print(f"Wrote {evidence_count} Evidence-Hint DPO records to {repo_path(args.evidence_output)}")
    return 0


def prompt(record: dict) -> str:
    return f"<image>\nQuestion: {record['question']}\nAnswer:"


def base_record(record: dict, include_metadata: bool) -> dict:
    out = {
        "id": record["id"],
        "image": record["image"],
        "prompt": prompt(record),
    }
    if include_metadata:
        out.update(
            {
                "image_id": record.get("image_id"),
                "source": record.get("source"),
                "task_type": record.get("task_type"),
            }
        )
    return out


def export_answer(record: dict, include_metadata: bool) -> dict:
    out = base_record(record, include_metadata)
    out["chosen"] = record["chosen_answer"]
    out["rejected"] = record["rejected_answer"]
    return out


def export_evidence(record: dict, include_metadata: bool) -> dict:
    chosen_hint = record["evidence_hint_chosen"]
    rejected_hint = record["evidence_hint_rejected"]
    if "Evidence hint:" not in chosen_hint or "Evidence hint:" not in rejected_hint:
        raise ValueError(f"Missing evidence hint in canonical record {record.get('id')}")
    out = base_record(record, include_metadata)
    out["chosen"] = f"{record['chosen_answer']}\n{chosen_hint}"
    out["rejected"] = f"{record['rejected_answer']}\n{rejected_hint}"
    return out


if __name__ == "__main__":
    raise SystemExit(main())

