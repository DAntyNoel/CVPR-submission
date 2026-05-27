#!/usr/bin/env python3
"""Create a GQA simple held-out yes/no eval JSONL."""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from typing import Any

from common import clean_name, load_jsonl, repo_path, write_json, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default="data/processed/canonical_gqa_candidates.jsonl")
    parser.add_argument("--train", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--output", default="data/eval/gqa_simple_heldout.jsonl")
    parser.add_argument("--summary", default="data/eval/gqa_simple_heldout.summary.json")
    parser.add_argument("--max-rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--relation-frac", type=float, default=0.50)
    parser.add_argument("--max-pairs-per-image", type=int, default=1)
    parser.add_argument(
        "--include-material",
        action="store_true",
        help="Also allow material-attribute pairs. Defaults to color + left/right only.",
    )
    args = parser.parse_args()

    candidate_path = repo_path(args.candidates)
    train_path = repo_path(args.train)
    if not candidate_path.exists():
        print(f"Missing GQA candidate file: {candidate_path}", file=sys.stderr)
        return 2
    if not train_path.exists():
        print(f"Missing train file: {train_path}", file=sys.stderr)
        return 2
    if args.max_rows < 2:
        print("--max-rows must be at least 2.", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    train_gqa_image_ids = load_train_gqa_image_ids(train_path)
    candidates = load_jsonl(candidate_path)
    color_pairs: list[list[dict[str, Any]]] = []
    relation_pairs: list[list[dict[str, Any]]] = []
    material_pairs: list[list[dict[str, Any]]] = []

    for record in candidates:
        if record.get("image_id") in train_gqa_image_ids:
            continue
        if record.get("image") and not repo_path(record["image"]).exists():
            continue
        pair = make_eval_pair(record)
        if not pair:
            continue
        task_type = pair[0]["task_type"]
        if task_type == "attribute_color":
            color_pairs.append(pair)
        elif task_type == "relation_spatial":
            relation_pairs.append(pair)
        elif task_type == "attribute_material" and args.include_material:
            material_pairs.append(pair)

    for pool in (color_pairs, relation_pairs, material_pairs):
        rng.shuffle(pool)

    max_rows = args.max_rows if args.max_rows % 2 == 0 else args.max_rows - 1
    target_pairs = max_rows // 2
    target_relation_pairs = min(len(relation_pairs), round(target_pairs * args.relation_frac))
    target_color_pairs = min(len(color_pairs), target_pairs - target_relation_pairs)

    per_image_counts: dict[str, int] = defaultdict(int)
    selected_pairs: list[list[dict[str, Any]]] = []
    selected_pairs.extend(
        take_pairs(relation_pairs, target_relation_pairs, per_image_counts, args.max_pairs_per_image)
    )
    selected_pairs.extend(
        take_pairs(color_pairs, target_color_pairs, per_image_counts, args.max_pairs_per_image)
    )

    remaining = target_pairs - len(selected_pairs)
    if remaining > 0:
        fallback_pool = relation_pairs + color_pairs + material_pairs
        rng.shuffle(fallback_pool)
        selected_pairs.extend(
            take_pairs(fallback_pool, remaining, per_image_counts, args.max_pairs_per_image, selected_pairs)
        )

    rows = flatten_pairs(selected_pairs, rng)
    if not rows:
        print("No held-out GQA eval rows could be built.", file=sys.stderr)
        return 1

    count = write_jsonl(args.output, rows)
    eval_image_ids = {row["image_id"] for row in rows}
    overlap = sorted(eval_image_ids & train_gqa_image_ids)
    summary = {
        "output": str(repo_path(args.output)),
        "source_candidates": str(candidate_path),
        "train_file": str(train_path),
        "candidate_records": len(candidates),
        "train_gqa_image_ids": len(train_gqa_image_ids),
        "available_source_pairs": {
            "attribute_color": len(color_pairs),
            "relation_spatial": len(relation_pairs),
            "attribute_material": len(material_pairs),
        },
        "selected_source_pairs": len(selected_pairs),
        "eval_records": count,
        "unique_images": len(eval_image_ids),
        "target_counts": dict(sorted(Counter(row["target"] for row in rows).items())),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "max_rows": args.max_rows,
        "seed": args.seed,
        "relation_frac": args.relation_frac,
        "max_pairs_per_image": args.max_pairs_per_image,
        "train_eval_image_overlap": len(overlap),
        "train_eval_image_overlap_ids": overlap[:50],
    }
    write_json(args.summary, summary)

    print(f"Wrote {count} GQA simple eval rows to {repo_path(args.output)}")
    print(f"Wrote GQA simple eval summary to {repo_path(args.summary)}")
    print(f"Task counts: {summary['task_counts']}")
    print(f"Target counts: {summary['target_counts']}")
    print(f"Train/eval GQA image overlap: {len(overlap)}")
    if count < max_rows:
        print(f"Warning: requested {max_rows} rows but only wrote {count}.", file=sys.stderr)
    if overlap:
        return 1
    return 0


def load_train_gqa_image_ids(path: Any) -> set[str]:
    image_ids = set()
    for record in load_jsonl(path):
        image_id = record.get("image_id")
        if record.get("source") == "gqa" and image_id:
            image_ids.add(str(image_id))
        elif str(image_id or "").startswith("gqa_"):
            image_ids.add(str(image_id))
    return image_ids


def make_eval_pair(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    task_type = str(record.get("task_type") or "")
    if task_type in {"attribute_color", "attribute_material"}:
        return make_attribute_pair(record)
    if task_type == "relation_spatial":
        return make_relation_pair(record)
    return None


def make_attribute_pair(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    label = record.get("label") or {}
    obj = clean_name(label.get("object"))
    positive = clean_name(label.get("positive_attribute"))
    negative = clean_name(label.get("negative_attribute"))
    attr_type = clean_name(label.get("attribute_type"))
    if not obj or not positive or not negative:
        return None
    if attr_type not in {"color", "material"}:
        return None
    if attr_type == "material":
        yes_question = f"Is the {obj} made of {positive}?"
        no_question = f"Is the {obj} made of {negative}?"
    else:
        yes_question = f"Is the {obj} {positive}?"
        no_question = f"Is the {obj} {negative}?"
    base = base_row(record, f"attribute_{attr_type}")
    return [
        {
            **base,
            "id": "",
            "question": yes_question,
            "target": "yes",
            "target_text": positive,
        },
        {
            **base,
            "id": "",
            "question": no_question,
            "target": "no",
            "target_text": negative,
        },
    ]


def make_relation_pair(record: dict[str, Any]) -> list[dict[str, Any]] | None:
    label = record.get("label") or {}
    subject = clean_name(label.get("subject"))
    obj = clean_name(label.get("object"))
    relation = clean_name(label.get("relation"))
    negative_relation = clean_name(label.get("negative_relation"))
    if relation not in {"left", "right"} or negative_relation not in {"left", "right"}:
        return None
    if not subject or not obj:
        return None
    base = base_row(record, "relation_spatial")
    return [
        {
            **base,
            "id": "",
            "question": f"Is the {subject} to the {relation} of the {obj}?",
            "target": "yes",
            "target_text": relation,
        },
        {
            **base,
            "id": "",
            "question": f"Is the {subject} to the {negative_relation} of the {obj}?",
            "target": "no",
            "target_text": negative_relation,
        },
    ]


def base_row(record: dict[str, Any], task_type: str) -> dict[str, Any]:
    return {
        "source": "gqa_heldout",
        "source_id": record.get("id"),
        "image": record.get("image"),
        "image_id": record.get("image_id"),
        "task_type": task_type,
        "label": record.get("label") or {},
    }


def take_pairs(
    pool: list[list[dict[str, Any]]],
    desired: int,
    per_image_counts: dict[str, int],
    max_pairs_per_image: int,
    already_selected: list[list[dict[str, Any]]] | None = None,
) -> list[list[dict[str, Any]]]:
    selected: list[list[dict[str, Any]]] = []
    seen_source_ids = {
        str(pair[0].get("source_id"))
        for pair in (already_selected or [])
        if pair and pair[0].get("source_id")
    }
    for pair in pool:
        if len(selected) >= desired:
            break
        if not pair:
            continue
        source_id = str(pair[0].get("source_id") or "")
        if source_id in seen_source_ids:
            continue
        image_id = str(pair[0].get("image_id") or "")
        if per_image_counts[image_id] >= max_pairs_per_image:
            continue
        selected.append(pair)
        seen_source_ids.add(source_id)
        per_image_counts[image_id] += 1
    return selected


def flatten_pairs(pairs: list[list[dict[str, Any]]], rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        shuffled = [dict(row) for row in pair]
        rng.shuffle(shuffled)
        rows.extend(shuffled)
    for idx, row in enumerate(rows, start=1):
        row["id"] = f"gqa_simple_{idx:06d}"
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
