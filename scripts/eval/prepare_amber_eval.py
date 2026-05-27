#!/usr/bin/env python3
"""Normalize official AMBER discriminative queries into eval JSONL."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from common import load_json, repo_path, write_json, write_jsonl


DIMENSION_TO_QUERY = {
    "existence": "query_discriminative-existence.json",
    "attribute": "query_discriminative-attribute.json",
    "relation": "query_discriminative-relation.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--annotation",
        default="data/raw/external/amber/data/annotations.json",
        help="Official AMBER annotations.json.",
    )
    parser.add_argument(
        "--query-root",
        default="data/raw/external/amber/data/query",
        help="Directory containing official AMBER query JSON files.",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=None,
        help="Explicit AMBER query JSON file. May be passed more than once.",
    )
    parser.add_argument(
        "--dimensions",
        nargs="+",
        choices=sorted(DIMENSION_TO_QUERY),
        default=["existence", "attribute", "relation"],
        help="AMBER discriminative dimensions to include when --query is not used.",
    )
    parser.add_argument("--image-root", default="data/raw/amber/images")
    parser.add_argument("--output", default="data/eval/amber_discriminative.jsonl")
    parser.add_argument("--summary", default="data/eval/amber_discriminative.summary.json")
    parser.add_argument("--source-name", default="amber")
    parser.add_argument("--benchmark", default="amber")
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument(
        "--max-records-per-dimension",
        type=int,
        default=None,
        help="Optional lightweight cap for smoke/debug subsets. Leave unset for full official data.",
    )
    parser.add_argument(
        "--require-images",
        action="store_true",
        help="Return an error if any normalized image path is missing.",
    )
    args = parser.parse_args()

    annotation_path = repo_path(args.annotation)
    if not annotation_path.exists():
        print(f"Missing AMBER annotation file: {annotation_path}", file=sys.stderr)
        return 2

    annotations = load_annotations(annotation_path)
    query_specs = resolve_query_specs(args)
    rows: list[dict[str, Any]] = []
    missing_annotations: list[int] = []
    seen_ids: set[int] = set()
    per_dimension_counts: Counter[str] = Counter()

    for fallback_dimension, query_path in query_specs:
        if not query_path.exists():
            print(f"Missing AMBER query file: {query_path}", file=sys.stderr)
            return 2
        for raw in read_query_records(query_path):
            if args.max_records is not None and len(rows) >= args.max_records:
                break
            source_id = int(raw["id"])
            if source_id in seen_ids:
                continue
            annotation = annotations.get(source_id)
            if not annotation:
                missing_annotations.append(source_id)
                continue
            dimension = infer_dimension(annotation, fallback_dimension)
            if dimension is None:
                continue
            if (
                args.max_records_per_dimension is not None
                and per_dimension_counts[dimension] >= args.max_records_per_dimension
            ):
                continue
            row = normalize_record(raw, annotation, dimension, args)
            rows.append(row)
            seen_ids.add(source_id)
            per_dimension_counts[dimension] += 1
        if args.max_records is not None and len(rows) >= args.max_records:
            break

    if not rows:
        print("No AMBER rows could be normalized.", file=sys.stderr)
        return 1

    missing_images = [
        str(repo_path(row["image"]))
        for row in rows
        if row.get("image") and not repo_path(row["image"]).exists()
    ]
    if missing_images and args.require_images:
        print(
            f"Missing {len(missing_images)} AMBER images; first missing image: {missing_images[0]}",
            file=sys.stderr,
        )
        return 1

    count = write_jsonl(args.output, rows)
    summary = {
        "annotation": str(annotation_path),
        "query_files": [str(path) for _, path in query_specs],
        "output": str(repo_path(args.output)),
        "source_name": args.source_name,
        "benchmark": args.benchmark,
        "records_out": count,
        "unique_images": len({row["image_id"] for row in rows}),
        "target_counts": dict(sorted(Counter(row["target"] for row in rows).items())),
        "dimension_counts": dict(sorted(Counter(row["dimension"] for row in rows).items())),
        "task_counts": dict(sorted(Counter(row["task_type"] for row in rows).items())),
        "amber_type_counts": dict(sorted(Counter(row["amber_type"] for row in rows).items())),
        "missing_annotations": len(missing_annotations),
        "missing_annotation_examples": missing_annotations[:20],
        "image_root": str(repo_path(args.image_root)),
        "missing_images": len(missing_images),
        "missing_image_examples": missing_images[:10],
        "max_records": args.max_records,
        "max_records_per_dimension": args.max_records_per_dimension,
    }
    write_json(args.summary, summary)

    print(f"Wrote {count} AMBER rows to {repo_path(args.output)}")
    print(f"Dimension counts: {summary['dimension_counts']}")
    print(f"Target counts: {summary['target_counts']}")
    if missing_images:
        print(f"Warning: {len(missing_images)} AMBER image paths are missing locally.")
    return 0


def load_annotations(path: Path) -> dict[int, dict[str, Any]]:
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a list of AMBER annotations")
    annotations: dict[int, dict[str, Any]] = {}
    for idx, annotation in enumerate(payload, start=1):
        if not isinstance(annotation, dict):
            raise ValueError(f"{path}:{idx}: expected object")
        source_id = int(annotation.get("id", idx))
        annotations[source_id] = annotation
    return annotations


def resolve_query_specs(args: argparse.Namespace) -> list[tuple[str | None, Path]]:
    if args.query:
        return [(infer_dimension_from_path(Path(query)), repo_path(query)) for query in args.query]
    query_root = repo_path(args.query_root)
    return [
        (dimension, query_root / DIMENSION_TO_QUERY[dimension])
        for dimension in args.dimensions
    ]


def infer_dimension_from_path(path: Path) -> str | None:
    name = path.name.lower()
    for dimension in DIMENSION_TO_QUERY:
        if dimension in name:
            return dimension
    return None


def read_query_records(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, dict):
        for key in ("queries", "data", "records"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a list of AMBER query records")
    out: list[dict[str, Any]] = []
    for idx, record in enumerate(payload, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{idx}: expected object")
        if "id" not in record or "query" not in record:
            raise ValueError(f"{path}:{idx}: expected id and query keys")
        out.append(record)
    return out


def normalize_record(
    raw: dict[str, Any],
    annotation: dict[str, Any],
    dimension: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source_id = int(raw["id"])
    image = str(raw.get("image") or f"AMBER_{source_id}.jpg")
    return {
        "id": f"{args.source_name}_{source_id:06d}",
        "source": args.source_name,
        "source_id": source_id,
        "benchmark": args.benchmark,
        "dimension": dimension,
        "amber_type": str(annotation.get("type") or ""),
        "image": resolve_image_path(image, args.image_root),
        "image_id": Path(image).stem,
        "question": str(raw["query"]).strip(),
        "target": normalize_target(annotation.get("truth")),
        "task_type": infer_task_type(annotation),
    }


def infer_dimension(annotation: dict[str, Any], fallback: str | None) -> str | None:
    amber_type = str(annotation.get("type") or "")
    if amber_type == "discriminative-hallucination":
        return "existence"
    if amber_type.startswith("discriminative-attribute-"):
        return "attribute"
    if amber_type in {"discriminative-relation", "relation"}:
        return "relation"
    return fallback


def infer_task_type(annotation: dict[str, Any]) -> str:
    amber_type = str(annotation.get("type") or "")
    if amber_type == "discriminative-hallucination":
        return "object_existence"
    if amber_type == "discriminative-attribute-state":
        return "attribute_state"
    if amber_type == "discriminative-attribute-number":
        return "attribute_number"
    if amber_type == "discriminative-attribute-action":
        return "attribute_action"
    if amber_type in {"discriminative-relation", "relation"}:
        return "relation"
    return amber_type or "unknown"


def normalize_target(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "yes"
    if text in {"no", "n", "false", "0"}:
        return "no"
    raise ValueError(f"Unsupported AMBER truth value: {value!r}")


def resolve_image_path(image: str, image_root: str) -> str:
    image_path = Path(image)
    if image_path.is_absolute() or "/" in image:
        return image
    return str(Path(image_root) / image)


if __name__ == "__main__":
    raise SystemExit(main())
