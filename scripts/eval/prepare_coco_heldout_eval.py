#!/usr/bin/env python3
"""Create a balanced COCO held-out object-existence eval JSONL."""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from typing import Any

from common import article_phrase, load_jsonl, read_id_set, repo_path, write_json, write_jsonl


LOW_CONF_NEGATIVES = {
    "book",
    "cell phone",
    "clock",
    "fork",
    "hair drier",
    "handbag",
    "keyboard",
    "knife",
    "mouse",
    "remote",
    "scissors",
    "spoon",
    "sports ball",
    "tie",
    "toothbrush",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default="data/processed/canonical_coco_pool.jsonl")
    parser.add_argument("--heldout-image-ids", default="data/eval/heldout_object_existence_image_ids.txt")
    parser.add_argument("--output", default="data/eval/coco_heldout_object_existence.jsonl")
    parser.add_argument("--summary", default="data/eval/coco_heldout_object_existence.summary.json")
    parser.add_argument("--max-pairs", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--keep-low-confidence-negatives",
        action="store_true",
        help="Keep negative objects that are commonly small or under-annotated.",
    )
    args = parser.parse_args()

    pool_path = repo_path(args.pool)
    heldout_path = repo_path(args.heldout_image_ids)
    if not pool_path.exists():
        print(f"Missing COCO pool: {pool_path}", file=sys.stderr)
        return 2
    if not heldout_path.exists():
        print(f"Missing held-out image ids: {heldout_path}", file=sys.stderr)
        return 2

    heldout_ids = read_id_set(heldout_path)
    pool = load_jsonl(pool_path)
    candidates = [
        record
        for record in pool
        if record.get("image_id") in heldout_ids
        and (args.keep_low_confidence_negatives or negative_object(record) not in LOW_CONF_NEGATIVES)
    ]

    rng = random.Random(args.seed)
    rng.shuffle(candidates)

    rows: list[dict[str, Any]] = []
    used_keys: set[tuple[str, str, str]] = set()
    for record in candidates:
        if len(rows) >= args.max_pairs * 2:
            break
        pair = []
        for target, obj in (("yes", positive_object(record)), ("no", negative_object(record))):
            key = (str(record.get("image_id")), obj, target)
            if key in used_keys:
                pair = []
                break
            pair.append((target, obj, key))
        if len(pair) != 2 or len(rows) + 2 > args.max_pairs * 2:
            continue
        for target, obj, key in pair:
            used_keys.add(key)
            rows.append(make_eval_row(len(rows) + 1, record, target, obj))

    if not rows:
        print("No held-out eval rows could be built.", file=sys.stderr)
        return 1

    count = write_jsonl(args.output, rows)
    target_counts = Counter(row["target"] for row in rows)
    image_count = len({row["image_id"] for row in rows})
    summary = {
        "output": str(repo_path(args.output)),
        "source_pool": str(pool_path),
        "heldout_image_ids": str(heldout_path),
        "pool_records": len(pool),
        "candidate_records": len(candidates),
        "eval_records": count,
        "unique_images": image_count,
        "target_counts": dict(sorted(target_counts.items())),
        "max_pairs": args.max_pairs,
        "seed": args.seed,
        "excluded_low_confidence_negatives": (
            [] if args.keep_low_confidence_negatives else sorted(LOW_CONF_NEGATIVES)
        ),
    }
    write_json(args.summary, summary)

    print(f"Wrote {count} held-out eval rows to {repo_path(args.output)}")
    print(f"Wrote held-out eval summary to {repo_path(args.summary)}")
    print(f"Target counts: {dict(sorted(target_counts.items()))}")
    return 0


def make_eval_row(idx: int, record: dict[str, Any], target: str, obj: str) -> dict[str, Any]:
    return {
        "id": f"coco_heldout_{idx:06d}",
        "source": "coco_heldout",
        "source_id": record.get("id"),
        "image": record.get("image"),
        "image_id": record.get("image_id"),
        "question": f"Is there {article_phrase(obj)} in the image?",
        "target": target,
        "target_object": obj,
        "task_type": "object_existence",
    }


def positive_object(record: dict[str, Any]) -> str:
    return str((record.get("label") or {}).get("positive_object") or "")


def negative_object(record: dict[str, Any]) -> str:
    return str((record.get("label") or {}).get("negative_object") or "")


if __name__ == "__main__":
    raise SystemExit(main())
