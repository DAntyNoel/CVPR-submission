#!/usr/bin/env python3
"""Create a COCO object-existence candidate pool for base-error mining."""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    article_phrase,
    clean_name,
    load_json,
    load_jsonl,
    read_id_set,
    repo_path,
    repo_relative,
    write_json,
    write_jsonl,
)


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

COARSE_GROUPS = [
    {"person"},
    {"bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat"},
    {"traffic light", "fire hydrant", "stop sign", "parking meter", "bench"},
    {"bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"},
    {"backpack", "umbrella", "handbag", "tie", "suitcase"},
    {
        "frisbee",
        "skis",
        "snowboard",
        "sports ball",
        "kite",
        "baseball bat",
        "baseball glove",
        "skateboard",
        "surfboard",
        "tennis racket",
    },
    {"bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl"},
    {"banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake"},
    {"chair", "couch", "potted plant", "bed", "dining table", "toilet"},
    {"tv", "laptop", "mouse", "remote", "keyboard", "cell phone"},
    {"microwave", "oven", "toaster", "sink", "refrigerator"},
    {"book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default="data/processed/canonical_coco_pool.jsonl")
    parser.add_argument("--instances", default="data/raw/coco/annotations/instances_train2017.json")
    parser.add_argument("--image-root", default="data/raw/coco/train2017")
    parser.add_argument("--image-field-root", default=None)
    parser.add_argument("--heldout-image-ids", default="data/eval/heldout_object_existence_image_ids.txt")
    parser.add_argument("--train", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--output", default="data/eval/base_error_mining_candidates.jsonl")
    parser.add_argument("--summary", default="data/eval/base_error_mining_candidates.summary.json")
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--max-pairs-per-image", type=int, default=8)
    parser.add_argument("--min-area-frac", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--keep-low-confidence-negatives",
        action="store_true",
        help="Keep negative objects that are commonly small or under-annotated.",
    )
    parser.add_argument("--allow-missing-images", action="store_true")
    args = parser.parse_args()

    if args.max_rows < 2:
        print("--max-rows must be at least 2.", file=sys.stderr)
        return 2

    pool_path = repo_path(args.pool)
    instances_path = repo_path(args.instances)
    heldout_path = repo_path(args.heldout_image_ids)
    if not pool_path.exists():
        print(f"Missing COCO pool: {pool_path}", file=sys.stderr)
        return 2
    if not instances_path.exists():
        print(f"Missing COCO annotation file: {instances_path}", file=sys.stderr)
        return 2
    if not heldout_path.exists():
        print(f"Missing held-out image ids: {heldout_path}", file=sys.stderr)
        return 2

    heldout_ids = read_id_set(heldout_path)
    pool_pairs, pool_skipped = build_pool_pairs(args, heldout_ids)
    hard_pairs, hard_skipped = build_hard_pairs(args, heldout_ids)
    pairs_by_strategy = group_by_strategy(pool_pairs + hard_pairs)

    rows, selected_pairs, selection_skips = select_rows(pairs_by_strategy, args)
    if not rows:
        print("No base-error mining candidates could be built.", file=sys.stderr)
        return 1

    train_ids = load_train_image_ids(args.train)
    eval_ids = {str(row["image_id"]) for row in rows}
    overlap = sorted(train_ids & eval_ids)
    summary = build_summary(
        args=args,
        rows=rows,
        selected_pairs=selected_pairs,
        pool_pairs=pool_pairs,
        hard_pairs=hard_pairs,
        pool_skipped=pool_skipped,
        hard_skipped=hard_skipped,
        selection_skips=selection_skips,
        overlap=overlap,
    )
    if overlap:
        write_json(args.summary, summary)
        print(
            f"Refusing to write candidate JSONL because train/eval image overlap is {len(overlap)}. "
            f"Summary written to {repo_path(args.summary)}",
            file=sys.stderr,
        )
        return 1

    count = write_jsonl(args.output, rows)
    summary["eval_records"] = count
    write_json(args.summary, summary)

    print(f"Wrote {count} base-error mining candidate rows to {repo_path(args.output)}")
    print(f"Wrote candidate summary to {repo_path(args.summary)}")
    print(f"Target counts: {summary['target_counts']}")
    print(f"Strategy counts: {summary['candidate_strategy_counts']}")
    print(f"Train/eval image overlap: {len(overlap)}")
    return 0


def build_pool_pairs(args: argparse.Namespace, heldout_ids: set[str]) -> tuple[list[dict[str, Any]], Counter[str]]:
    skipped: Counter[str] = Counter()
    pairs: list[dict[str, Any]] = []
    for record in load_jsonl(args.pool):
        image_id = str(record.get("image_id") or "")
        if image_id not in heldout_ids:
            skipped["not_heldout"] += 1
            continue
        image = str(record.get("image") or "")
        if image and not args.allow_missing_images and not repo_path(image).exists():
            skipped["missing_image"] += 1
            continue
        label = record.get("label") or {}
        pos = clean_name(label.get("positive_object"))
        neg = clean_name(label.get("negative_object"))
        if not pos or not neg:
            skipped["missing_object"] += 1
            continue
        if not args.keep_low_confidence_negatives and neg in LOW_CONF_NEGATIVES:
            skipped["low_confidence_negative"] += 1
            continue
        pairs.append(
            {
                "source": "coco_pool",
                "source_id": record.get("id"),
                "image": image,
                "image_id": image_id,
                "positive_object": pos,
                "negative_object": neg,
                "candidate_strategy": "heldout_pool_absent_object",
            }
        )
    return pairs, skipped


def build_hard_pairs(args: argparse.Namespace, heldout_ids: set[str]) -> tuple[list[dict[str, Any]], Counter[str]]:
    skipped: Counter[str] = Counter()
    payload = load_json(args.instances)
    image_root = repo_path(args.image_root)
    image_field_root = repo_path(args.image_field_root or args.image_root)
    categories = {
        int(category["id"]): clean_name(category["name"])
        for category in payload.get("categories", [])
    }
    images = {int(image["id"]): image for image in payload.get("images", [])}
    visible_by_image = collect_visible_objects(payload, categories, images, args.min_area_frac)
    pairs: list[dict[str, Any]] = []

    for raw_image_id, image in images.items():
        image_id = canonical_image_id(image)
        if image_id not in heldout_ids and str(raw_image_id) not in heldout_ids:
            skipped["not_heldout"] += 1
            continue
        filename = image.get("file_name") or f"{raw_image_id:012d}.jpg"
        check_image_path = image_root / filename
        if not args.allow_missing_images and not check_image_path.exists():
            skipped["missing_image"] += 1
            continue
        visible = set(visible_by_image.get(raw_image_id, {}))
        if not visible:
            skipped["no_visible_objects"] += 1
            continue
        for pos in sorted(visible):
            for neg in hard_negative_candidates(pos, visible, args.keep_low_confidence_negatives):
                pairs.append(
                    {
                        "source": "coco_instances",
                        "source_id": raw_image_id,
                        "image": repo_relative(image_field_root / filename),
                        "image_id": image_id,
                        "positive_object": pos,
                        "negative_object": neg,
                        "candidate_strategy": "same_coarse_group_absent_object",
                    }
                )
    return pairs, skipped


def select_rows(
    pairs_by_strategy: dict[str, list[dict[str, Any]]],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    rng = random.Random(args.seed)
    for pairs in pairs_by_strategy.values():
        rng.shuffle(pairs)

    strategy_names = sorted(pairs_by_strategy)
    strategy_offsets = {strategy: 0 for strategy in strategy_names}
    selected_pairs: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    used_eval_keys: set[tuple[str, str, str]] = set()
    used_pair_keys: set[tuple[str, str, str, str]] = set()
    per_image_counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    max_pairs = args.max_rows // 2

    while len(selected_pairs) < max_pairs:
        progressed = False
        for strategy in strategy_names:
            pairs = pairs_by_strategy[strategy]
            while strategy_offsets[strategy] < len(pairs):
                pair = pairs[strategy_offsets[strategy]]
                strategy_offsets[strategy] += 1
                progressed = True
                if try_add_pair(
                    pair=pair,
                    selected_pairs=selected_pairs,
                    rows=rows,
                    used_eval_keys=used_eval_keys,
                    used_pair_keys=used_pair_keys,
                    per_image_counts=per_image_counts,
                    max_pairs=max_pairs,
                    max_pairs_per_image=args.max_pairs_per_image,
                    skipped=skipped,
                ):
                    break
            if len(selected_pairs) >= max_pairs:
                break
        if not progressed:
            break

    return rows, selected_pairs, skipped


def try_add_pair(
    pair: dict[str, Any],
    selected_pairs: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    used_eval_keys: set[tuple[str, str, str]],
    used_pair_keys: set[tuple[str, str, str, str]],
    per_image_counts: Counter[str],
    max_pairs: int,
    max_pairs_per_image: int,
    skipped: Counter[str],
) -> bool:
    if len(selected_pairs) >= max_pairs:
        skipped["max_pairs_reached"] += 1
        return False

    image_id = str(pair["image_id"])
    pos = str(pair["positive_object"])
    neg = str(pair["negative_object"])
    pair_key = (image_id, pos, neg, str(pair["candidate_strategy"]))
    if pair_key in used_pair_keys:
        skipped["duplicate_pair"] += 1
        return False
    if per_image_counts[image_id] >= max_pairs_per_image:
        skipped["max_pairs_per_image"] += 1
        return False

    row_specs = (("yes", pos), ("no", neg))
    eval_keys = {(image_id, target, obj) for target, obj in row_specs}
    if used_eval_keys & eval_keys:
        skipped["duplicate_image_target_object"] += 1
        return False

    rows.extend(make_eval_rows(len(rows), pair))
    selected_pairs.append(pair)
    used_pair_keys.add(pair_key)
    used_eval_keys.update(eval_keys)
    per_image_counts[image_id] += 1
    return True


def make_eval_rows(start_idx: int, pair: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for offset, (target, obj) in enumerate((("yes", pair["positive_object"]), ("no", pair["negative_object"])), start=1):
        rows.append(
            {
                "id": f"base_error_mining_cand_{start_idx + offset:06d}",
                "source": "coco_base_error_mining",
                "candidate_source": pair["source"],
                "source_id": pair.get("source_id"),
                "pair_id": (
                    f"{pair['image_id']}::{pair['positive_object']}::absent_{pair['negative_object']}::"
                    f"{pair['candidate_strategy']}"
                ),
                "image": pair["image"],
                "image_id": pair["image_id"],
                "question": f"Is there {article_phrase(obj)} in the image?",
                "target": target,
                "target_object": obj,
                "target_text": target,
                "task_type": "object_existence",
                "candidate_strategy": pair["candidate_strategy"],
                "positive_object": pair["positive_object"],
                "negative_object": pair["negative_object"],
            }
        )
    return rows


def build_summary(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    selected_pairs: list[dict[str, Any]],
    pool_pairs: list[dict[str, Any]],
    hard_pairs: list[dict[str, Any]],
    pool_skipped: Counter[str],
    hard_skipped: Counter[str],
    selection_skips: Counter[str],
    overlap: list[str],
) -> dict[str, Any]:
    target_counts = Counter(row["target"] for row in rows)
    strategy_counts = Counter(row["candidate_strategy"] for row in rows)
    pair_strategy_counts = Counter(pair["candidate_strategy"] for pair in selected_pairs)
    return {
        "output": str(repo_path(args.output)),
        "source_pool": str(repo_path(args.pool)),
        "source_instances": str(repo_path(args.instances)),
        "heldout_image_ids": str(repo_path(args.heldout_image_ids)),
        "train_file": str(repo_path(args.train)),
        "max_rows": args.max_rows,
        "max_pairs_per_image": args.max_pairs_per_image,
        "min_area_frac": args.min_area_frac,
        "seed": args.seed,
        "candidate_pair_counts_before_selection": {
            "heldout_pool_absent_object": len(pool_pairs),
            "same_coarse_group_absent_object": len(hard_pairs),
            "total": len(pool_pairs) + len(hard_pairs),
        },
        "selected_pairs": len(selected_pairs),
        "eval_records": len(rows),
        "unique_images": len({row["image_id"] for row in rows}),
        "target_counts": dict(sorted(target_counts.items())),
        "candidate_strategy_counts": dict(sorted(strategy_counts.items())),
        "pair_strategy_counts": dict(sorted(pair_strategy_counts.items())),
        "top_target_objects": Counter(row["target_object"] for row in rows).most_common(30),
        "top_positive_objects": Counter(pair["positive_object"] for pair in selected_pairs).most_common(30),
        "top_negative_objects": Counter(pair["negative_object"] for pair in selected_pairs).most_common(30),
        "train_eval_image_overlap": len(overlap),
        "train_eval_image_overlap_ids": overlap[:50],
        "excluded_low_confidence_negatives": (
            [] if args.keep_low_confidence_negatives else sorted(LOW_CONF_NEGATIVES)
        ),
        "pool_skipped": dict(sorted(pool_skipped.items())),
        "hard_skipped": dict(sorted(hard_skipped.items())),
        "selection_skipped": dict(sorted(selection_skips.items())),
    }


def group_by_strategy(pairs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        out[str(pair["candidate_strategy"])].append(pair)
    return dict(out)


def collect_visible_objects(
    payload: dict[str, Any],
    categories: dict[int, str],
    images: dict[int, dict[str, Any]],
    min_area_frac: float,
) -> dict[int, dict[str, float]]:
    visible_by_image: dict[int, dict[str, float]] = defaultdict(dict)
    for ann in payload.get("annotations", []):
        if int(ann.get("iscrowd", 0)) == 1:
            continue
        image_id = int(ann["image_id"])
        image = images.get(image_id)
        category = categories.get(int(ann["category_id"]))
        if not image or not category:
            continue
        image_area = float(image.get("width", 0)) * float(image.get("height", 0))
        if image_area <= 0:
            continue
        ann_area = float(ann.get("area") or bbox_area(ann.get("bbox")))
        if ann_area < min_area_frac * image_area:
            continue
        visible_by_image[image_id][category] = max(
            visible_by_image[image_id].get(category, 0.0),
            ann_area,
        )
    return visible_by_image


def hard_negative_candidates(
    positive: str,
    visible: set[str],
    keep_low_confidence_negatives: bool,
) -> list[str]:
    for group in COARSE_GROUPS:
        if positive in group:
            negatives = sorted(group - visible)
            if not keep_low_confidence_negatives:
                negatives = [name for name in negatives if name not in LOW_CONF_NEGATIVES]
            return negatives
    return []


def load_train_image_ids(path: str) -> set[str]:
    train_path = repo_path(path)
    if not train_path.exists():
        return set()
    return {str(record.get("image_id")) for record in load_jsonl(train_path) if record.get("image_id")}


def canonical_image_id(image: dict[str, Any]) -> str:
    filename = image.get("file_name") or f"{int(image['id']):012d}.jpg"
    return f"coco_train2017_{Path(filename).stem}"


def bbox_area(bbox: Any) -> float:
    if not isinstance(bbox, list) or len(bbox) < 4:
        return 0.0
    return max(float(bbox[2]), 0.0) * max(float(bbox[3]), 0.0)


if __name__ == "__main__":
    raise SystemExit(main())
