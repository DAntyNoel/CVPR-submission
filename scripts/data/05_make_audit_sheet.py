#!/usr/bin/env python3
"""Create a human audit CSV from canonical preference pairs."""

from __future__ import annotations

import argparse
import csv
import random
import sys

from common import ensure_parent, load_jsonl, repo_path


HEADERS = [
    "id",
    "source",
    "image",
    "question",
    "chosen",
    "rejected",
    "chosen_hint",
    "rejected_hint",
    "chosen_correct",
    "rejected_wrong",
    "hint_correct",
    "note",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--output", default="data/audit/audit_200.csv")
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        print(f"Missing canonical input: {input_path}", file=sys.stderr)
        return 2

    records = load_jsonl(input_path)
    rng = random.Random(args.seed)
    sample_size = min(args.sample_size, len(records))
    sampled = rng.sample(records, sample_size) if sample_size < len(records) else list(records)

    output_path = repo_path(args.output)
    ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for record in sampled:
            writer.writerow(
                {
                    "id": record.get("id", ""),
                    "source": record.get("source", ""),
                    "image": record.get("image", ""),
                    "question": record.get("question", ""),
                    "chosen": record.get("chosen_answer", ""),
                    "rejected": record.get("rejected_answer", ""),
                    "chosen_hint": record.get("evidence_hint_chosen", ""),
                    "rejected_hint": record.get("evidence_hint_rejected", ""),
                    "chosen_correct": "",
                    "rejected_wrong": "",
                    "hint_correct": "",
                    "note": "",
                }
            )
    print(f"Wrote {sample_size} audit rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

