#!/usr/bin/env python3
"""Build COCO object-existence preference pairs."""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import (
    article_phrase,
    clean_name,
    load_image_id_set,
    load_json,
    repo_path,
    repo_relative,
    weighted_choice,
    write_jsonl,
)


QUESTION_TEMPLATES = [
    "Is there {obj_phrase} in the image?",
    "Can you see {obj_phrase} in this image?",
    "Does the image contain {obj_phrase}?",
]

LOW_CONF_NEGATIVES = {
    "fork",
    "knife",
    "spoon",
    "remote",
    "cell phone",
    "toothbrush",
    "hair drier",
    "scissors",
    "sports ball",
    "tie",
    "handbag",
    "book",
    "clock",
    "mouse",
    "keyboard",
}

COARSE_GROUPS = [
    {
        "person",
    },
    {
        "bicycle",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
    },
    {
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
    },
    {
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
    },
    {
        "backpack",
        "umbrella",
        "handbag",
        "tie",
        "suitcase",
    },
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
    {
        "bottle",
        "wine glass",
        "cup",
        "fork",
        "knife",
        "spoon",
        "bowl",
    },
    {
        "banana",
        "apple",
        "sandwich",
        "orange",
        "broccoli",
        "carrot",
        "hot dog",
        "pizza",
        "donut",
        "cake",
    },
    {
        "chair",
        "couch",
        "potted plant",
        "bed",
        "dining table",
        "toilet",
    },
    {
        "tv",
        "laptop",
        "mouse",
        "remote",
        "keyboard",
        "cell phone",
    },
    {
        "microwave",
        "oven",
        "toaster",
        "sink",
        "refrigerator",
    },
    {
        "book",
        "clock",
        "vase",
        "scissors",
        "teddy bear",
        "hair drier",
        "toothbrush",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instances",
        default="data/raw/coco/annotations/instances_train2017.json",
        help="COCO instances_train2017.json",
    )
    parser.add_argument(
        "--image-root",
        default="data/raw/coco/train2017",
        help="Directory used to check image existence",
    )
    parser.add_argument(
        "--image-field-root",
        default=None,
        help="Directory prefix written into the output image field",
    )
    parser.add_argument("--output", default="data/processed/canonical_coco_main.jsonl")
    parser.add_argument("--limit", type=int, default=3500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-area-frac", type=float, default=0.01)
    parser.add_argument("--max-pairs-per-image", type=int, default=2)
    parser.add_argument("--allow-missing-images", action="store_true")
    parser.add_argument(
        "--exclude-image-ids",
        nargs="*",
        default=[],
        help="Optional JSON/JSONL/CSV/TXT files containing eval image ids to exclude",
    )
    args = parser.parse_args()

    instances_path = repo_path(args.instances)
    if not instances_path.exists():
        print(f"Missing COCO annotation file: {instances_path}", file=sys.stderr)
        return 2

    payload = load_json(instances_path)
    records = build_pairs(payload, args)
    count = write_jsonl(args.output, records)
    print(f"Wrote {count} COCO canonical pairs to {repo_path(args.output)}")
    if count < args.limit:
        print(
            f"Warning: requested {args.limit} pairs but only generated {count}.",
            file=sys.stderr,
        )
    return 0


def build_pairs(payload: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    rng = random.Random(args.seed)
    exclude_ids = load_image_id_set(args.exclude_image_ids)

    categories = {
        int(category["id"]): clean_name(category["name"])
        for category in payload.get("categories", [])
    }
    all_category_names = sorted(set(categories.values()))

    images = {int(image["id"]): image for image in payload.get("images", [])}
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
        if ann_area < args.min_area_frac * image_area:
            continue
        visible_by_image[image_id][category] = max(
            visible_by_image[image_id].get(category, 0.0),
            ann_area,
        )

    image_ids = list(images)
    rng.shuffle(image_ids)

    image_root = repo_path(args.image_root)
    image_field_root = repo_path(args.image_field_root or args.image_root)
    out: list[dict[str, Any]] = []

    for image_id in image_ids:
        if len(out) >= args.limit:
            break
        image = images[image_id]
        visible = visible_by_image.get(image_id, {})
        if len(visible) < 2:
            continue

        filename = image.get("file_name") or f"{image_id:012d}.jpg"
        canonical_image_id = f"coco_train2017_{Path(filename).stem}"
        if canonical_image_id in exclude_ids or str(image_id) in exclude_ids:
            continue

        check_image_path = image_root / filename
        if not args.allow_missing_images and not check_image_path.exists():
            continue
        output_image_path = repo_relative(image_field_root / filename)

        pos_objects = sorted(visible, key=lambda name: visible[name], reverse=True)
        pair_count = min(args.max_pairs_per_image, len(pos_objects))
        used_pos: set[str] = set()
        for _ in range(pair_count):
            if len(out) >= args.limit:
                break
            pos = choose_positive(pos_objects, visible, used_pos, rng)
            used_pos.add(pos)
            neg = choose_negative(pos, set(visible), all_category_names, rng)
            out.append(make_record(len(out) + 1, output_image_path, canonical_image_id, pos, neg, visible, rng))

    return out


def bbox_area(bbox: Any) -> float:
    if not isinstance(bbox, list) or len(bbox) < 4:
        return 0.0
    return max(float(bbox[2]), 0.0) * max(float(bbox[3]), 0.0)


def choose_positive(
    pos_objects: list[str],
    visible: dict[str, float],
    used_pos: set[str],
    rng: random.Random,
) -> str:
    candidates = [name for name in pos_objects if name not in used_pos]
    weights = [max(visible[name], 1.0) for name in candidates]
    return weighted_choice(candidates, weights, rng)


def choose_negative(
    positive: str,
    visible: set[str],
    all_categories: list[str],
    rng: random.Random,
) -> str:
    candidates = [name for name in all_categories if name not in visible]
    related = related_group(positive)
    weights: list[float] = []
    for name in candidates:
        weight = 1.0
        if name in related:
            weight *= 3.0
        if name in LOW_CONF_NEGATIVES:
            weight *= 0.35
        weights.append(weight)
    return weighted_choice(candidates, weights, rng)


def related_group(name: str) -> set[str]:
    for group in COARSE_GROUPS:
        if name in group:
            return group
    return set()


def make_record(
    idx: int,
    image_path: str,
    image_id: str,
    pos: str,
    neg: str,
    visible: dict[str, float],
    rng: random.Random,
) -> dict[str, Any]:
    pos_phrase = article_phrase(pos)
    neg_phrase = article_phrase(neg)
    question = rng.choice(QUESTION_TEMPLATES).format(obj_phrase=pos_phrase)
    return {
        "id": f"coco_obj_{idx:06d}",
        "source": "coco",
        "image": image_path,
        "image_id": image_id,
        "task_type": "object_existence",
        "question": question,
        "chosen_answer": f"Yes, there is {pos_phrase} in the image.",
        "rejected_answer": f"Yes, there is {neg_phrase} in the image.",
        "evidence_hint_chosen": f"Evidence hint: annotated visible object: {pos}.",
        "evidence_hint_rejected": (
            f"Evidence hint: unsupported object: {neg} is not annotated as visible."
        ),
        "label": {
            "positive_object": pos,
            "negative_object": neg,
            "visible_objects": sorted(visible),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())

