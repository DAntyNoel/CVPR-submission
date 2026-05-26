#!/usr/bin/env python3
"""Merge source-specific canonical pairs into a versioned training set."""

from __future__ import annotations

import argparse
import random
import shutil
import sys

from common import (
    load_image_id_set,
    load_jsonl,
    repo_path,
    summarize_records,
    write_json,
    write_jsonl,
)


class NotEnoughRecordsError(RuntimeError):
    """Raised when a requested split cannot be filled from available pairs."""


TARGETS = {
    "smoke": {"coco": 1500, "gqa": 500},
    "main": {"coco": 3500, "gqa": 1500},
    "expanded": {"coco": 6000, "gqa": 4000},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=sorted(TARGETS), default="main")
    parser.add_argument("--coco", default="data/processed/canonical_coco_main.jsonl")
    parser.add_argument("--gqa", default="data/processed/canonical_gqa_main.jsonl")
    parser.add_argument("--output", default=None)
    parser.add_argument("--stats-output", default=None)
    parser.add_argument("--target-coco", type=int, default=None)
    parser.add_argument("--target-gqa", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-short", action="store_true")
    parser.add_argument(
        "--fallback-coco-only",
        action="store_true",
        help="Use extra COCO pairs to fill the GQA target when GQA data is missing or short.",
    )
    parser.add_argument(
        "--write-default",
        action="store_true",
        help="Also write data/processed/canonical_pairs.jsonl.",
    )
    parser.add_argument("--eval-image-ids", nargs="*", default=[])
    args = parser.parse_args()

    target = dict(TARGETS[args.version])
    if args.target_coco is not None:
        target["coco"] = args.target_coco
    if args.target_gqa is not None:
        target["gqa"] = args.target_gqa

    rng = random.Random(args.seed)
    try:
        coco_records = load_if_exists(args.coco)
        gqa_records = load_if_exists(args.gqa)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not gqa_records and target["gqa"] > 0 and not args.fallback_coco_only:
        print("GQA input is empty; pass --fallback-coco-only or provide GQA pairs.", file=sys.stderr)
        return 2

    try:
        selected_coco, unused_coco = sample_records(coco_records, target["coco"], rng, args.allow_short)
        selected_gqa, _ = sample_records(
            gqa_records,
            target["gqa"],
            rng,
            args.allow_short or args.fallback_coco_only,
        )
    except NotEnoughRecordsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    desired_total = target["coco"] + target["gqa"]
    if args.fallback_coco_only and len(selected_coco) + len(selected_gqa) < desired_total:
        fill_needed = desired_total - len(selected_coco) - len(selected_gqa)
        try:
            fill, _ = sample_records(unused_coco, fill_needed, rng, args.allow_short)
        except NotEnoughRecordsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        selected_coco.extend(fill)

    selected = selected_coco + selected_gqa
    rng.shuffle(selected)

    if len(selected) < desired_total and not args.allow_short:
        print(
            f"Only selected {len(selected)} / {desired_total} records; pass --allow-short to write anyway.",
            file=sys.stderr,
        )
        return 2

    output = args.output or f"data/processed/canonical_pairs_{args.version}.jsonl"
    count = write_jsonl(output, selected)
    print(f"Wrote {count} merged canonical pairs to {repo_path(output)}")

    if args.write_default:
        default_path = repo_path("data/processed/canonical_pairs.jsonl")
        default_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_path(output), default_path)
        print(f"Wrote default canonical copy to {default_path}")

    stats_output = args.stats_output or f"data/processed/stats_{args.version}.json"
    stats = summarize_records(selected)
    stats["target"] = target
    eval_ids = load_image_id_set(args.eval_image_ids)
    train_ids = {str(record.get("image_id")) for record in selected}
    stats["train_eval_image_overlap"] = len(train_ids & eval_ids)
    stats["train_eval_image_overlap_ids"] = sorted(train_ids & eval_ids)[:50]
    write_json(stats_output, stats)
    print(f"Wrote stats to {repo_path(stats_output)}")
    return 0


def load_if_exists(path: str) -> list[dict]:
    full_path = repo_path(path)
    if not full_path.exists():
        return []
    return load_jsonl(full_path)


def sample_records(
    records: list[dict],
    desired: int,
    rng: random.Random,
    allow_short: bool,
) -> tuple[list[dict], list[dict]]:
    shuffled = list(records)
    rng.shuffle(shuffled)
    if len(shuffled) < desired and not allow_short:
        raise NotEnoughRecordsError(
            f"Need {desired} records from {len(records)} available; pass --allow-short or generate more."
        )
    selected = shuffled[: min(desired, len(shuffled))]
    unused = shuffled[min(desired, len(shuffled)) :]
    return selected, unused


if __name__ == "__main__":
    raise SystemExit(main())
