#!/usr/bin/env python3
"""Create a balanced hard COCO object-existence eval JSONL."""

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
    parser.add_argument("--instances", default="data/raw/coco/annotations/instances_train2017.json")
    parser.add_argument("--image-root", default="data/raw/coco/train2017")
    parser.add_argument("--image-field-root", default=None)
    parser.add_argument("--heldout-image-ids", default="data/eval/heldout_object_existence_image_ids.txt")
    parser.add_argument("--train", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--output", default="data/eval/coco_hard_object_existence.jsonl")
    parser.add_argument("--summary", default="data/eval/coco_hard_object_existence.summary.json")
    parser.add_argument("--max-pairs", type=int, default=500)
    parser.add_argument("--max-pairs-per-image", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-area-frac", type=float, default=0.01)
    parser.add_argument(
        "--keep-low-confidence-negatives",
        action="store_true",
        help="Keep negative objects that are commonly small or under-annotated.",
    )
    parser.add_argument("--allow-missing-images", action="store_true")
    args = parser.parse_args()

    instances_path = repo_path(args.instances)
    heldout_path = repo_path(args.heldout_image_ids)
    if not instances_path.exists():
        print(f"Missing COCO annotation file: {instances_path}", file=sys.stderr)
        return 2
    if not heldout_path.exists():
        print(f"Missing held-out image ids: {heldout_path}", file=sys.stderr)
        return 2

    payload = load_json(instances_path)
    rows, selected_pairs, candidate_count = build_rows(payload, args)
    if not rows:
        print("No hard COCO eval rows could be built.", file=sys.stderr)
        return 1

    count = write_jsonl(args.output, rows)
    target_counts = Counter(row["target"] for row in rows)
    train_ids = load_train_image_ids(args.train)
    eval_ids = {str(row["image_id"]) for row in rows}
    overlap = sorted(train_ids & eval_ids)
    summary = {
        "output": str(repo_path(args.output)),
        "source_instances": str(instances_path),
        "heldout_image_ids": str(heldout_path),
        "train_file": str(repo_path(args.train)),
        "hard_negative_strategy": "same_coarse_group_absent_object",
        "candidate_pairs": candidate_count,
        "selected_pairs": len(selected_pairs),
        "eval_records": count,
        "unique_images": len({row["image_id"] for row in rows}),
        "target_counts": dict(sorted(target_counts.items())),
        "max_pairs": args.max_pairs,
        "max_pairs_per_image": args.max_pairs_per_image,
        "min_area_frac": args.min_area_frac,
        "seed": args.seed,
        "train_eval_image_overlap": len(overlap),
        "train_eval_image_overlap_ids": overlap[:50],
        "excluded_low_confidence_negatives": (
            [] if args.keep_low_confidence_negatives else sorted(LOW_CONF_NEGATIVES)
        ),
        "top_positive_objects": Counter(pair["positive_object"] for pair in selected_pairs).most_common(20),
        "top_negative_objects": Counter(pair["negative_object"] for pair in selected_pairs).most_common(20),
        "top_hard_pairs": Counter(
            f"{pair['positive_object']}->{pair['negative_object']}" for pair in selected_pairs
        ).most_common(20),
    }
    write_json(args.summary, summary)

    print(f"Wrote {count} hard COCO eval rows to {repo_path(args.output)}")
    print(f"Wrote hard COCO summary to {repo_path(args.summary)}")
    print(f"Target counts: {dict(sorted(target_counts.items()))}")
    print(f"Train/eval image overlap: {len(overlap)}")
    return 0


def build_rows(
    payload: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    rng = random.Random(args.seed)
    heldout_ids = read_id_set(args.heldout_image_ids)
    image_root = repo_path(args.image_root)
    image_field_root = repo_path(args.image_field_root or args.image_root)

    categories = {
        int(category["id"]): clean_name(category["name"])
        for category in payload.get("categories", [])
    }
    images = {int(image["id"]): image for image in payload.get("images", [])}
    visible_by_image = collect_visible_objects(payload, categories, images, args.min_area_frac)

    candidates: list[dict[str, Any]] = []
    for image_id, image in images.items():
        canonical_id = canonical_image_id(image)
        if canonical_id not in heldout_ids and str(image_id) not in heldout_ids:
            continue
        filename = image.get("file_name") or f"{image_id:012d}.jpg"
        check_image_path = image_root / filename
        if not args.allow_missing_images and not check_image_path.exists():
            continue
        visible = set(visible_by_image.get(image_id, {}))
        if not visible:
            continue
        for pos in sorted(visible):
            for neg in hard_negative_candidates(pos, visible, args.keep_low_confidence_negatives):
                candidates.append(
                    {
                        "image": repo_relative(image_field_root / filename),
                        "image_id": canonical_id,
                        "positive_object": pos,
                        "negative_object": neg,
                    }
                )

    rng.shuffle(candidates)
    selected: list[dict[str, Any]] = []
    per_image_counts: Counter[str] = Counter()
    used_pairs: set[tuple[str, str, str]] = set()
    for pair in candidates:
        if len(selected) >= args.max_pairs:
            break
        image_id = pair["image_id"]
        if per_image_counts[image_id] >= args.max_pairs_per_image:
            continue
        key = (image_id, pair["positive_object"], pair["negative_object"])
        if key in used_pairs:
            continue
        used_pairs.add(key)
        per_image_counts[image_id] += 1
        selected.append(pair)

    rows: list[dict[str, Any]] = []
    for pair in selected:
        rows.append(make_eval_row(len(rows) + 1, pair, "yes", pair["positive_object"]))
        rows.append(make_eval_row(len(rows) + 1, pair, "no", pair["negative_object"]))
    return rows, selected, len(candidates)


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


def make_eval_row(idx: int, pair: dict[str, Any], target: str, obj: str) -> dict[str, Any]:
    return {
        "id": f"coco_hard_{idx:06d}",
        "source": "coco_hard",
        "pair_id": (
            f"{pair['image_id']}::{pair['positive_object']}::absent_{pair['negative_object']}"
        ),
        "image": pair["image"],
        "image_id": pair["image_id"],
        "question": f"Is there {article_phrase(obj)} in the image?",
        "target": target,
        "target_object": obj,
        "positive_object": pair["positive_object"],
        "negative_object": pair["negative_object"],
        "task_type": "object_existence",
        "hard_negative_strategy": "same_coarse_group_absent_object",
    }


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
