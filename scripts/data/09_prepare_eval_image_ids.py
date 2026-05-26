#!/usr/bin/env python3
"""Prepare held-out eval image ids that do not overlap with training ids."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

from common import ensure_parent, load_jsonl, repo_path, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--pool", default="data/processed/canonical_coco_pool.jsonl")
    parser.add_argument("--output", default="data/eval/heldout_object_existence_image_ids.txt")
    parser.add_argument("--report", default=None)
    parser.add_argument("--max-ids", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_path = repo_path(args.train)
    pool_path = repo_path(args.pool)
    if not train_path.exists():
        print(f"Missing training canonical file: {train_path}", file=sys.stderr)
        return 2
    if not pool_path.exists():
        print(f"Missing candidate pool file: {pool_path}", file=sys.stderr)
        return 2

    train_records = load_jsonl(train_path)
    pool_records = load_jsonl(pool_path)
    train_ids = image_ids(train_records)
    pool_ids = image_ids(pool_records)
    candidates = sorted(pool_ids - train_ids)
    if not candidates:
        print("No held-out image ids remain after removing train ids.", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(candidates)
    selected = candidates[: min(args.max_ids, len(candidates))]

    output_path = repo_path(args.output)
    ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        for image_id in selected:
            f.write(f"{image_id}\n")

    report_path = repo_path(args.report) if args.report else default_report_path(output_path)
    report = {
        "train_file": str(train_path),
        "pool_file": str(pool_path),
        "output_file": str(output_path),
        "train_records": len(train_records),
        "pool_records": len(pool_records),
        "train_unique_image_ids": len(train_ids),
        "pool_unique_image_ids": len(pool_ids),
        "candidate_heldout_image_ids": len(candidates),
        "selected_image_ids": len(selected),
        "max_ids": args.max_ids,
        "seed": args.seed,
        "train_eval_image_overlap": len(train_ids & set(selected)),
        "train_eval_image_overlap_ids": sorted(train_ids & set(selected))[:50],
    }
    write_json(report_path, report)

    print(f"Wrote {len(selected)} held-out eval image ids to {output_path}")
    print(f"Wrote eval id report to {report_path}")
    return 0


def image_ids(records: list[dict[str, Any]]) -> set[str]:
    return {str(record.get("image_id")) for record in records if record.get("image_id")}


def default_report_path(output_path: Path) -> Path:
    return output_path.with_suffix(".summary.json")


if __name__ == "__main__":
    raise SystemExit(main())
