#!/usr/bin/env python3
"""Normalize POPE object-hallucination annotations into eval JSONL."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from common import ensure_parent, repo_path, write_json


IMAGE_KEYS = ("image", "image_path", "file_name", "filename")
IMAGE_ID_KEYS = ("image_id", "imageId", "img_id")
QUESTION_KEYS = ("question", "text", "prompt")
LABEL_KEYS = ("label", "answer", "target")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Official POPE JSON/JSONL/CSV annotation file.")
    parser.add_argument("--image-root", default="data/raw/coco/val2014")
    parser.add_argument("--output", default="data/eval/pope_object_hallucination.jsonl")
    parser.add_argument("--summary", default="data/eval/pope_object_hallucination.summary.json")
    parser.add_argument("--source-name", default="pope")
    parser.add_argument("--benchmark", default="pope")
    parser.add_argument("--dimension", default="existence")
    parser.add_argument("--sampling-strategy", default=None)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument(
        "--require-images",
        action="store_true",
        help="Return an error if any normalized image path is missing.",
    )
    args = parser.parse_args()

    input_path = repo_path(args.input)
    if not input_path.exists():
        print(f"Missing POPE input file: {input_path}", file=sys.stderr)
        return 2

    raw_records = list(read_records(input_path))
    rows = []
    for raw in raw_records:
        if args.max_records is not None and len(rows) >= args.max_records:
            break
        row = normalize_record(raw, len(rows) + 1, args)
        if row:
            rows.append(row)

    if not rows:
        print("No POPE rows could be normalized.", file=sys.stderr)
        return 1
    missing_images = [
        str(repo_path(row["image"]))
        for row in rows
        if row.get("image") and not repo_path(row["image"]).exists()
    ]
    if missing_images and args.require_images:
        print(
            f"Missing {len(missing_images)} POPE images; first missing image: {missing_images[0]}",
            file=sys.stderr,
        )
        return 1

    output_path = repo_path(args.output)
    ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    target_counts = {}
    for row in rows:
        target_counts[row["target"]] = target_counts.get(row["target"], 0) + 1
    write_json(
        args.summary,
        {
            "input": str(input_path),
            "output": str(output_path),
            "source_name": args.source_name,
            "records_in": len(raw_records),
            "records_out": len(rows),
            "unique_images": len({row["image_id"] for row in rows}),
            "target_counts": dict(sorted(target_counts.items())),
            "image_root": str(repo_path(args.image_root)),
            "benchmark": args.benchmark,
            "dimension": args.dimension,
            "sampling_strategy": args.sampling_strategy,
            "missing_images": len(missing_images),
            "missing_image_examples": missing_images[:10],
        },
    )

    print(f"Wrote {len(rows)} normalized POPE rows to {output_path}")
    print(f"Target counts: {dict(sorted(target_counts.items()))}")
    return 0


def read_records(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            yield from read_jsonl_records(f, path)
    elif suffix == ".json":
        text = path.read_text(encoding="utf-8")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            yield from read_jsonl_records(text.splitlines(), path)
            return
        if isinstance(payload, dict):
            for key in ("questions", "annotations", "data", "records"):
                if isinstance(payload.get(key), list):
                    yield from payload[key]
                    return
            yield payload
        elif isinstance(payload, list):
            yield from payload
        else:
            raise ValueError(f"{path}: expected JSON object or list")
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            yield from csv.DictReader(f)
    else:
        raise ValueError(f"Unsupported POPE file suffix: {path.suffix}")


def read_jsonl_records(lines: Iterable[str], path: Path) -> Iterable[dict[str, Any]]:
    for line_no, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        yield payload


def normalize_record(raw: dict[str, Any], idx: int, args: argparse.Namespace) -> dict[str, Any] | None:
    question = first_value(raw, QUESTION_KEYS)
    target = normalize_target(first_value(raw, LABEL_KEYS))
    image = first_value(raw, IMAGE_KEYS)
    image_id = first_value(raw, IMAGE_ID_KEYS) or derive_image_id(image, f"pope_{idx:06d}")
    if not question or not target:
        return None
    image_path = resolve_image_path(image, image_id, args.image_root)
    return {
        "id": f"{args.source_name}_{idx:06d}",
        "source": args.source_name,
        "source_id": raw.get("question_id") or raw.get("id") or idx,
        "benchmark": args.benchmark,
        "dimension": args.dimension,
        "sampling_strategy": args.sampling_strategy,
        "image": image_path,
        "image_id": str(image_id),
        "question": str(question).strip(),
        "target": target,
        "task_type": "object_existence",
    }


def first_value(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if raw.get(key) not in (None, ""):
            return raw[key]
    return None


def normalize_target(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if text in {"yes", "y", "true", "1", "present"}:
        return "yes"
    if text in {"no", "n", "false", "0", "absent"}:
        return "no"
    return None


def derive_image_id(image: Any, fallback: str) -> str:
    if not image:
        return fallback
    stem = Path(str(image)).stem
    if stem.startswith("COCO_"):
        digits = stem.rsplit("_", 1)[-1]
        if digits:
            return str(int(digits))
    return stem or fallback


def resolve_image_path(image: Any, image_id: Any, image_root: str) -> str:
    if image:
        image_text = str(image)
        image_path = Path(image_text)
        if image_path.is_absolute() or "/" in image_text:
            return image_text
        if not image_path.suffix and image_text.isdigit():
            return str(Path(image_root) / f"COCO_val2014_{int(image_text):012d}.jpg")
        return str(Path(image_root) / image_text)
    image_text = str(image_id)
    if image_text.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return str(Path(image_root) / image_text)
    digits = "".join(ch for ch in image_text if ch.isdigit())
    filename = f"COCO_val2014_{int(digits):012d}.jpg" if digits else f"{image_text}.jpg"
    return str(Path(image_root) / filename)


if __name__ == "__main__":
    raise SystemExit(main())
