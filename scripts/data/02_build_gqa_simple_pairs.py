#!/usr/bin/env python3
"""Build simple GQA attribute and spatial-relation preference pairs."""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import (
    be_verb,
    clean_name,
    load_image_id_set,
    load_json,
    repo_path,
    repo_relative,
    weighted_choice,
    write_jsonl,
)


COLORS = [
    "black",
    "blue",
    "brown",
    "gray",
    "green",
    "orange",
    "pink",
    "purple",
    "red",
    "white",
    "yellow",
]

COLOR_ALIASES = {
    "grey": "gray",
    "silver": "gray",
}

MATERIALS = [
    "brick",
    "ceramic",
    "cloth",
    "fabric",
    "glass",
    "leather",
    "metal",
    "paper",
    "plastic",
    "rubber",
    "stone",
    "wooden",
]

CONFUSABLE_ATTRS = {
    ("gray", "white"),
    ("gray", "black"),
    ("white", "gray"),
    ("white", "yellow"),
    ("brown", "orange"),
    ("orange", "brown"),
}

RELATION_FLIPS = {
    "left": "right",
    "right": "left",
    "above": "below",
    "below": "above",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scene-graphs",
        default="data/raw/gqa/train_sceneGraphs.json",
        help="GQA train_sceneGraphs.json",
    )
    parser.add_argument(
        "--image-root",
        default="data/raw/gqa/images",
        help="Directory used to check GQA image existence",
    )
    parser.add_argument(
        "--image-field-root",
        default=None,
        help="Directory prefix written into the output image field",
    )
    parser.add_argument("--output", default="data/processed/canonical_gqa_main.jsonl")
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-pairs-per-image", type=int, default=2)
    parser.add_argument("--max-relation-frac", type=float, default=0.30)
    parser.add_argument("--allow-missing-images", action="store_true")
    parser.add_argument("--attributes-only", action="store_true")
    parser.add_argument(
        "--exclude-image-ids",
        nargs="*",
        default=[],
        help="Optional JSON/JSONL/CSV/TXT files containing eval image ids to exclude",
    )
    args = parser.parse_args()

    sg_path = repo_path(args.scene_graphs)
    if not sg_path.exists():
        print(f"Missing GQA scene graph file: {sg_path}", file=sys.stderr)
        return 2

    scene_graphs = load_json(sg_path)
    records = build_pairs(scene_graphs, args)
    count = write_jsonl(args.output, records)
    print(f"Wrote {count} GQA canonical pairs to {repo_path(args.output)}")
    if count < args.limit:
        print(
            f"Warning: requested {args.limit} pairs but only generated {count}.",
            file=sys.stderr,
        )
    return 0


def build_pairs(scene_graphs: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    rng = random.Random(args.seed)
    exclude_ids = load_image_id_set(args.exclude_image_ids)
    image_root = repo_path(args.image_root)
    image_field_root = repo_path(args.image_field_root or args.image_root)

    attr_candidates: list[dict[str, Any]] = []
    relation_candidates: list[dict[str, Any]] = []

    for raw_image_id, graph in scene_graphs.items():
        image_id = f"gqa_train_{raw_image_id}"
        if image_id in exclude_ids or str(raw_image_id) in exclude_ids:
            continue
        image_path = find_gqa_image(image_root, image_field_root, str(raw_image_id), args.allow_missing_images)
        if image_path is None:
            continue

        objects = graph.get("objects") or {}
        clean_objects = normalize_objects(objects)
        for object_id, obj in clean_objects.items():
            obj_name = obj["name"]
            for attr_type, attr in iter_simple_attributes(obj.get("attributes", [])):
                attr_candidates.append(
                    {
                        "image": image_path,
                        "image_id": image_id,
                        "object_id": object_id,
                        "object": obj_name,
                        "attribute_type": attr_type,
                        "attribute": attr,
                    }
                )

            if args.attributes_only:
                continue
            for relation in obj.get("relations", []):
                rel = normalize_relation(relation.get("name"))
                target_id = str(relation.get("object", ""))
                target = clean_objects.get(target_id)
                if not rel or not target:
                    continue
                relation_candidates.append(
                    {
                        "image": image_path,
                        "image_id": image_id,
                        "subject_id": object_id,
                        "subject": obj_name,
                        "object_id": target_id,
                        "object": target["name"],
                        "relation": rel,
                    }
                )

    rng.shuffle(attr_candidates)
    rng.shuffle(relation_candidates)

    relation_target = 0 if args.attributes_only else int(args.limit * args.max_relation_frac)
    per_image_counts: dict[str, int] = defaultdict(int)
    selected_rel = take_candidates(
        relation_candidates,
        relation_target,
        per_image_counts,
        args.max_pairs_per_image,
        make_relation_record,
        rng,
    )
    remaining = args.limit - len(selected_rel)
    selected_attr = take_candidates(
        attr_candidates,
        remaining,
        per_image_counts,
        args.max_pairs_per_image,
        make_attribute_record,
        rng,
    )

    selected = selected_attr + selected_rel
    rng.shuffle(selected)
    for idx, record in enumerate(selected, start=1):
        suffix = "rel" if record["task_type"] == "relation_spatial" else "attr"
        record["id"] = f"gqa_{suffix}_{idx:06d}"
    return selected[: args.limit]


def normalize_objects(objects: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for object_id, obj in objects.items():
        name = clean_name(obj.get("name"))
        if not name:
            continue
        out[str(object_id)] = {
            "name": name,
            "attributes": obj.get("attributes") or [],
            "relations": obj.get("relations") or [],
        }
    return out


def find_gqa_image(
    check_root: Path,
    field_root: Path,
    image_id: str,
    allow_missing: bool,
) -> str | None:
    for suffix in (".jpg", ".jpeg", ".png"):
        check_path = check_root / f"{image_id}{suffix}"
        if check_path.exists():
            return repo_relative(field_root / f"{image_id}{suffix}")
    if allow_missing:
        return repo_relative(field_root / f"{image_id}.jpg")
    return None


def iter_simple_attributes(attributes: list[Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_attr in attributes:
        attr = clean_name(raw_attr)
        attr = COLOR_ALIASES.get(attr, attr)
        if attr in COLORS:
            key = ("color", attr)
        elif attr in MATERIALS:
            key = ("material", attr)
        else:
            continue
        if key not in seen:
            out.append(key)
            seen.add(key)
    return out


def normalize_relation(name: Any) -> str | None:
    rel = clean_name(name)
    if rel in {"left", "left of", "to the left of"} or "left of" in rel:
        return "left"
    if rel in {"right", "right of", "to the right of"} or "right of" in rel:
        return "right"
    if rel in {"above", "above of"} or rel == "over":
        return "above"
    if rel in {"below", "below of", "under", "underneath"}:
        return "below"
    return None


def take_candidates(
    candidates: list[dict[str, Any]],
    desired: int,
    per_image_counts: dict[str, int],
    max_pairs_per_image: int,
    factory,
    rng: random.Random,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()
    for candidate in candidates:
        if len(selected) >= desired:
            break
        image_id = candidate["image_id"]
        if per_image_counts[image_id] >= max_pairs_per_image:
            continue
        key = tuple(sorted(candidate.items()))
        if key in seen_keys:
            continue
        record = factory(candidate, rng)
        if record is None:
            continue
        selected.append(record)
        seen_keys.add(key)
        per_image_counts[image_id] += 1
    return selected


def make_attribute_record(candidate: dict[str, Any], rng: random.Random) -> dict[str, Any] | None:
    attr_type = candidate["attribute_type"]
    pos_attr = candidate["attribute"]
    vocab = COLORS if attr_type == "color" else MATERIALS
    neg_attr = choose_negative_attribute(pos_attr, vocab, rng)
    obj = candidate["object"]
    verb = be_verb(obj)
    question = f"What {attr_type} is the {obj}?" if attr_type != "color" else f"What color is the {obj}?"
    return {
        "source": "gqa",
        "image": candidate["image"],
        "image_id": candidate["image_id"],
        "task_type": f"attribute_{attr_type}",
        "question": question,
        "chosen_answer": f"The {obj} {verb} {pos_attr}.",
        "rejected_answer": f"The {obj} {verb} {neg_attr}.",
        "evidence_hint_chosen": f"Evidence hint: annotated attribute of {obj}: {pos_attr}.",
        "evidence_hint_rejected": f"Evidence hint: mismatched attribute for {obj}: {neg_attr}.",
        "label": {
            "object": obj,
            "attribute_type": attr_type,
            "positive_attribute": pos_attr,
            "negative_attribute": neg_attr,
        },
    }


def choose_negative_attribute(pos_attr: str, vocab: list[str], rng: random.Random) -> str:
    candidates = [attr for attr in vocab if attr != pos_attr]
    weights = []
    for attr in candidates:
        weight = 1.0
        if (pos_attr, attr) in CONFUSABLE_ATTRS:
            weight *= 0.35
        weights.append(weight)
    return weighted_choice(candidates, weights, rng)


def make_relation_record(candidate: dict[str, Any], rng: random.Random) -> dict[str, Any] | None:
    rel = candidate["relation"]
    neg_rel = RELATION_FLIPS.get(rel)
    if not neg_rel:
        return None
    subject = candidate["subject"]
    obj = candidate["object"]
    question_relation = question_relation_phrase(rel)
    answer_relation = answer_relation_phrase(rel, obj)
    negative_answer_relation = answer_relation_phrase(neg_rel, obj)
    return {
        "source": "gqa",
        "image": candidate["image"],
        "image_id": candidate["image_id"],
        "task_type": "relation_spatial",
        "question": f"What is {question_relation} the {obj}?",
        "chosen_answer": f"The {subject} is {answer_relation}.",
        "rejected_answer": f"The {subject} is {negative_answer_relation}.",
        "evidence_hint_chosen": f"Evidence hint: annotated relation: {subject} {rel} {obj}.",
        "evidence_hint_rejected": f"Evidence hint: contradicted relation: {subject} {neg_rel} {obj}.",
        "label": {
            "subject": subject,
            "object": obj,
            "relation": rel,
            "negative_relation": neg_rel,
        },
    }


def question_relation_phrase(relation: str) -> str:
    if relation in {"left", "right"}:
        return f"to the {relation} of"
    return relation


def answer_relation_phrase(relation: str, obj: str) -> str:
    if relation in {"left", "right"}:
        return f"to the {relation} of the {obj}"
    return f"{relation} the {obj}"


if __name__ == "__main__":
    raise SystemExit(main())
