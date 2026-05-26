#!/usr/bin/env python3
"""Download small HF-backed COCO/GQA subsets and normalize them for this project."""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from common import clean_name, ensure_parent, repo_path, write_json


COCO_REPOS = [
    "AISNP/COCO2017-instances",
    "detection-datasets/coco",
    "NaiveDev/coco-2017-instance",
    "ariG23498/coco2017",
]

GQA_REPOS = [
    "Voxel51/GQA-Scene-Graph",
]

COCO_80 = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
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
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
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
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
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
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]

COCO_91_ID_TO_NAME = {
    1: "person",
    2: "bicycle",
    3: "car",
    4: "motorcycle",
    5: "airplane",
    6: "bus",
    7: "train",
    8: "truck",
    9: "boat",
    10: "traffic light",
    11: "fire hydrant",
    13: "stop sign",
    14: "parking meter",
    15: "bench",
    16: "bird",
    17: "cat",
    18: "dog",
    19: "horse",
    20: "sheep",
    21: "cow",
    22: "elephant",
    23: "bear",
    24: "zebra",
    25: "giraffe",
    27: "backpack",
    28: "umbrella",
    31: "handbag",
    32: "tie",
    33: "suitcase",
    34: "frisbee",
    35: "skis",
    36: "snowboard",
    37: "sports ball",
    38: "kite",
    39: "baseball bat",
    40: "baseball glove",
    41: "skateboard",
    42: "surfboard",
    43: "tennis racket",
    44: "bottle",
    46: "wine glass",
    47: "cup",
    48: "fork",
    49: "knife",
    50: "spoon",
    51: "bowl",
    52: "banana",
    53: "apple",
    54: "sandwich",
    55: "orange",
    56: "broccoli",
    57: "carrot",
    58: "hot dog",
    59: "pizza",
    60: "donut",
    61: "cake",
    62: "chair",
    63: "couch",
    64: "potted plant",
    65: "bed",
    67: "dining table",
    70: "toilet",
    72: "tv",
    73: "laptop",
    74: "mouse",
    75: "remote",
    76: "keyboard",
    77: "cell phone",
    78: "microwave",
    79: "oven",
    80: "toaster",
    81: "sink",
    82: "refrigerator",
    84: "book",
    85: "clock",
    86: "vase",
    87: "scissors",
    88: "teddy bear",
    89: "hair drier",
    90: "toothbrush",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coco-repos", nargs="*", default=COCO_REPOS)
    parser.add_argument("--gqa-repos", nargs="*", default=GQA_REPOS)
    parser.add_argument("--coco-split", default="train")
    parser.add_argument("--gqa-split", default="train")
    parser.add_argument("--coco-images", type=int, default=8000)
    parser.add_argument("--gqa-images", type=int, default=4000)
    parser.add_argument("--max-scan", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-gqa", action="store_true")
    parser.add_argument("--manifest", default="data/raw/download_manifest.json")
    parser.add_argument("--allow-empty-gqa", action="store_true")
    args = parser.parse_args()

    print_env()
    random.seed(args.seed)

    try:
        coco_manifest = download_coco(args)
    except Exception as exc:  # noqa: BLE001
        print(f"COCO download/normalization failed: {exc}", file=sys.stderr)
        raise

    if args.skip_gqa:
        gqa_manifest = {"status": "skipped"}
    else:
        try:
            gqa_manifest = download_gqa(args)
        except Exception as exc:  # noqa: BLE001
            if not args.allow_empty_gqa:
                print(f"GQA download/normalization failed: {exc}", file=sys.stderr)
                raise
            gqa_manifest = {"status": "failed", "error": repr(exc)}
            print(f"Warning: continuing without GQA because {exc}", file=sys.stderr)

    manifest = {
        "hf_endpoint": os.environ.get("HF_ENDPOINT", ""),
        "coco": coco_manifest,
        "gqa": gqa_manifest,
    }
    write_json(args.manifest, manifest)
    print(f"Wrote manifest to {repo_path(args.manifest)}")
    return 0


def print_env() -> None:
    print("HF_ENDPOINT=", os.environ.get("HF_ENDPOINT", ""))
    print("http_proxy=", os.environ.get("http_proxy", ""))
    print("https_proxy=", os.environ.get("https_proxy", ""))
    print("all_proxy=", os.environ.get("all_proxy", ""))


def download_coco(args: argparse.Namespace) -> dict[str, Any]:
    datasets = import_datasets()
    image_root = repo_path("data/raw/coco/train2017")
    annotation_path = repo_path("data/raw/coco/annotations/instances_train2017.json")
    image_root.mkdir(parents=True, exist_ok=True)
    annotation_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for repo in args.coco_repos:
        print(f"Trying COCO HF dataset: {repo}")
        try:
            ds = load_streaming_dataset(datasets, repo, args.coco_split)
            payload, stats = normalize_coco_stream(ds, image_root, args.coco_images, args.max_scan)
            if len(payload["images"]) == 0:
                raise RuntimeError("no usable COCO images were extracted")
            with annotation_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            print(f"COCO normalized: {len(payload['images'])} images, {len(payload['annotations'])} annotations")
            return {
                "status": "ok",
                "repo": repo,
                "split": args.coco_split,
                "images": len(payload["images"]),
                "annotations": len(payload["annotations"]),
                "annotation_path": str(annotation_path),
                "image_root": str(image_root),
                "stats": stats,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"COCO repo failed: {repo}: {exc}", file=sys.stderr)
    raise RuntimeError(f"all COCO repos failed; last error: {last_error}")


def download_gqa(args: argparse.Namespace) -> dict[str, Any]:
    datasets = import_datasets()
    image_root = repo_path("data/raw/gqa/images")
    scene_graph_path = repo_path("data/raw/gqa/train_sceneGraphs.json")
    image_root.mkdir(parents=True, exist_ok=True)
    scene_graph_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for repo in args.gqa_repos:
        print(f"Trying GQA HF dataset: {repo}")
        try:
            ds = load_streaming_dataset(datasets, repo, args.gqa_split)
            scene_graphs, stats = normalize_gqa_stream(ds, image_root, args.gqa_images, args.max_scan)
            if len(scene_graphs) == 0:
                raise RuntimeError("no usable GQA scene graphs were extracted")
            with scene_graph_path.open("w", encoding="utf-8") as f:
                json.dump(scene_graphs, f, ensure_ascii=False)
            print(f"GQA normalized: {len(scene_graphs)} scene graphs")
            return {
                "status": "ok",
                "repo": repo,
                "split": args.gqa_split,
                "scene_graphs": len(scene_graphs),
                "scene_graph_path": str(scene_graph_path),
                "image_root": str(image_root),
                "stats": stats,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"GQA repo failed: {repo}: {exc}", file=sys.stderr)
    raise RuntimeError(f"all GQA repos failed; last error: {last_error}")


def import_datasets():
    try:
        import datasets  # type: ignore
    except ImportError as exc:
        raise RuntimeError("missing dependency: datasets") from exc
    try:
        datasets.disable_progress_bars()
    except Exception:
        pass
    return datasets


def load_streaming_dataset(datasets, repo: str, split: str):
    try:
        return datasets.load_dataset(
            repo,
            split=split,
            streaming=True,
            trust_remote_code=False,
        )
    except TypeError:
        return datasets.load_dataset(repo, split=split, streaming=True)


def normalize_coco_stream(
    ds: Iterable[dict[str, Any]],
    image_root: Path,
    image_limit: int,
    max_scan: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    category_name_to_id = {name: idx + 1 for idx, name in enumerate(COCO_80)}
    images: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    ann_id = 1
    scanned = 0
    skipped = Counter()
    example_keys: list[str] = []

    for row in ds:
        scanned += 1
        if scanned > max_scan or len(images) >= image_limit:
            break
        if not example_keys:
            example_keys = sorted(row.keys())
            print(f"COCO example keys: {example_keys}")

        image_obj = find_image(row)
        if image_obj is None:
            skipped["missing_image"] += 1
            continue

        image_id = extract_image_id(row, default=len(images) + 1)
        file_name = f"{int_like_id(image_id):012d}.jpg" if str(image_id).isdigit() else f"{safe_name(image_id)}.jpg"
        image_path = image_root / file_name
        width, height = save_image(image_obj, image_path)
        if width <= 0 or height <= 0:
            skipped["bad_image"] += 1
            continue

        ann_dict = find_annotation_dict(row)
        if not ann_dict:
            skipped["missing_annotations"] += 1
            continue
        per_image_annotations = extract_coco_annotations(ann_dict, category_name_to_id)
        if not per_image_annotations:
            skipped["empty_annotations"] += 1
            continue

        numeric_image_id = len(images) + 1
        images.append(
            {
                "id": numeric_image_id,
                "file_name": file_name,
                "width": width,
                "height": height,
            }
        )
        for ann in per_image_annotations:
            annotations.append(
                {
                    "id": ann_id,
                    "image_id": numeric_image_id,
                    "category_id": ann["category_id"],
                    "bbox": ann["bbox"],
                    "area": ann["area"],
                    "iscrowd": ann["iscrowd"],
                }
            )
            ann_id += 1

        if len(images) % 500 == 0:
            print(f"COCO progress: {len(images)} images from {scanned} scanned")

    categories = [
        {"id": idx, "name": name, "supercategory": "object"}
        for name, idx in sorted(category_name_to_id.items(), key=lambda item: item[1])
    ]
    payload = {
        "images": images,
        "annotations": annotations,
        "categories": categories,
    }
    stats = {
        "scanned": scanned,
        "skipped": dict(skipped),
        "example_keys": example_keys,
        "top_categories": Counter(
            ann["category_id"] for ann in annotations
        ).most_common(20),
    }
    return payload, stats


def normalize_gqa_stream(
    ds: Iterable[dict[str, Any]],
    image_root: Path,
    image_limit: int,
    max_scan: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scene_graphs: dict[str, Any] = {}
    scanned = 0
    skipped = Counter()
    example_keys: list[str] = []

    for row in ds:
        scanned += 1
        if scanned > max_scan or len(scene_graphs) >= image_limit:
            break
        if not example_keys:
            example_keys = sorted(row.keys())
            print(f"GQA example keys: {example_keys}")

        image_obj = find_image(row)
        image_id = str(extract_image_id(row, default=len(scene_graphs) + 1))
        image_id = safe_name(image_id)
        if image_obj is None:
            skipped["missing_image"] += 1
            continue
        image_path = image_root / f"{image_id}.jpg"
        width, height = save_image(image_obj, image_path)
        if width <= 0 or height <= 0:
            skipped["bad_image"] += 1
            continue

        graph = extract_gqa_graph(row)
        if not graph:
            skipped["missing_scene_graph"] += 1
            continue
        graph.setdefault("width", width)
        graph.setdefault("height", height)
        if not graph.get("objects"):
            skipped["empty_objects"] += 1
            continue
        scene_graphs[image_id] = graph

        if len(scene_graphs) % 500 == 0:
            print(f"GQA progress: {len(scene_graphs)} scene graphs from {scanned} scanned")

    stats = {
        "scanned": scanned,
        "skipped": dict(skipped),
        "example_keys": example_keys,
    }
    return scene_graphs, stats


def find_image(value: Any) -> Any | None:
    if is_pil_image(value) or is_image_dict(value):
        return value
    if isinstance(value, dict):
        preferred = [
            "image",
            "img",
            "input_image",
            "filepath",
            "file_path",
            "path",
        ]
        for key in preferred:
            if key in value and (is_pil_image(value[key]) or is_image_dict(value[key])):
                return value[key]
        for nested in value.values():
            found = find_image(nested)
            if found is not None:
                return found
    return None


def is_pil_image(value: Any) -> bool:
    return hasattr(value, "save") and hasattr(value, "size")


def is_image_dict(value: Any) -> bool:
    return isinstance(value, dict) and ("bytes" in value or "path" in value)


def save_image(image_obj: Any, path: Path) -> tuple[int, int]:
    ensure_parent(path)
    image = coerce_pil_image(image_obj)
    if image is None:
        return 0, 0
    image = image.convert("RGB")
    image.save(path, format="JPEG", quality=95)
    return int(image.width), int(image.height)


def coerce_pil_image(image_obj: Any) -> Any | None:
    from PIL import Image

    if is_pil_image(image_obj):
        return image_obj
    if isinstance(image_obj, dict):
        if image_obj.get("bytes"):
            return Image.open(io.BytesIO(image_obj["bytes"]))
        path = image_obj.get("path")
        if path and Path(path).exists():
            return Image.open(path)
    return None


def extract_image_id(row: dict[str, Any], default: Any) -> Any:
    for key in (
        "image_id",
        "imageId",
        "id",
        "sample_id",
        "filepath",
        "file_path",
        "coco_url",
        "url",
    ):
        value = row.get(key)
        if value not in (None, ""):
            stem = Path(str(value)).stem
            if stem:
                return stem
            return value
    return default


def int_like_id(value: Any) -> int:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits[-12:] or "0")


def safe_name(value: Any) -> str:
    text = str(value).strip().replace("/", "_").replace("\\", "_")
    out = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text)
    return out.strip("_") or "image"


def find_annotation_dict(row: dict[str, Any]) -> dict[str, Any] | None:
    for key in (
        "objects",
        "annotations",
        "annotation",
        "target",
        "labels",
        "instances",
        "segmentations",
    ):
        value = row.get(key)
        if isinstance(value, dict) and looks_like_coco_annotations(value):
            return value
    for value in row.values():
        if isinstance(value, dict) and looks_like_coco_annotations(value):
            return value
    return None


def looks_like_coco_annotations(value: dict[str, Any]) -> bool:
    keys = set(value)
    return bool(keys & {"bbox", "bboxes"}) and bool(
        keys & {"category", "categories", "category_id", "category_ids", "labels", "label"}
    )


def extract_coco_annotations(
    ann_dict: dict[str, Any],
    category_name_to_id: dict[str, int],
) -> list[dict[str, Any]]:
    bboxes = as_list(ann_dict.get("bbox") or ann_dict.get("bboxes"))
    if not bboxes:
        return []

    raw_names = ann_dict.get("categories")
    raw_ids = (
        ann_dict.get("category_id")
        or ann_dict.get("category_ids")
        or ann_dict.get("category")
        or ann_dict.get("labels")
        or ann_dict.get("label")
    )
    names = normalize_category_names(raw_names, raw_ids)
    if not names:
        return []

    areas = as_list(ann_dict.get("area") or ann_dict.get("areas"))
    iscrowds = as_list(ann_dict.get("iscrowd") or ann_dict.get("is_crowd"))

    out: list[dict[str, Any]] = []
    for idx, bbox in enumerate(bboxes):
        if idx >= len(names):
            break
        name = clean_name(names[idx])
        if not name:
            continue
        category_id = category_name_to_id.setdefault(name, len(category_name_to_id) + 1)
        box = normalize_bbox(bbox)
        if box is None:
            continue
        area = float(areas[idx]) if idx < len(areas) and areas[idx] is not None else box[2] * box[3]
        iscrowd = int(bool(iscrowds[idx])) if idx < len(iscrowds) else 0
        out.append(
            {
                "category_id": category_id,
                "bbox": box,
                "area": area,
                "iscrowd": iscrowd,
            }
        )
    return out


def normalize_category_names(raw_names: Any, raw_ids: Any) -> list[str]:
    names = as_list(raw_names)
    if names and all(isinstance(name, str) for name in names):
        return [clean_name(name) for name in names]

    ids = as_list(raw_ids or raw_names)
    out: list[str] = []
    for raw_id in ids:
        try:
            cid = int(raw_id)
        except (TypeError, ValueError):
            name = clean_name(raw_id)
            if name:
                out.append(name)
            continue
        if cid in COCO_91_ID_TO_NAME:
            out.append(COCO_91_ID_TO_NAME[cid])
        elif 0 <= cid < len(COCO_80):
            out.append(COCO_80[cid])
        else:
            out.append(f"category {cid}")
    return out


def normalize_bbox(bbox: Any) -> list[float] | None:
    values = as_list(bbox)
    if len(values) < 4:
        return None
    try:
        x, y, w, h = (float(values[0]), float(values[1]), float(values[2]), float(values[3]))
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    return [x, y, w, h]


def extract_gqa_graph(row: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("sceneGraph", "scene_graph", "scenegraph"):
        value = row.get(key)
        graph = normalize_gqa_graph(value)
        if graph:
            return graph
    value = row.get("objects")
    graph = normalize_gqa_graph({"objects": value} if value is not None else None)
    if graph:
        return graph
    for value in row.values():
        graph = normalize_gqa_graph(value)
        if graph:
            return graph
    detections = extract_detection_objects(row)
    if detections:
        return {"objects": detections}
    return None


def normalize_gqa_graph(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    objects = value.get("objects")
    if not isinstance(objects, dict):
        return None
    normalized: dict[str, Any] = {}
    for idx, (obj_id, obj) in enumerate(objects.items(), start=1):
        if not isinstance(obj, dict):
            continue
        name = clean_name(obj.get("name") or obj.get("label") or obj.get("category"))
        if not name:
            continue
        relations = normalize_gqa_relations(obj.get("relations"))
        normalized[str(obj_id or idx)] = {
            "name": name,
            "x": obj.get("x", 0),
            "y": obj.get("y", 0),
            "w": obj.get("w", obj.get("width", 0)),
            "h": obj.get("h", obj.get("height", 0)),
            "attributes": [clean_name(a) for a in as_list(obj.get("attributes")) if clean_name(a)],
            "relations": relations,
        }
    if not normalized:
        return None
    out = dict(value)
    out["objects"] = normalized
    return out


def normalize_gqa_relations(relations: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in as_list(relations):
        if not isinstance(rel, dict):
            continue
        name = rel.get("name") or rel.get("relation") or rel.get("predicate")
        target = rel.get("object") or rel.get("object_id") or rel.get("target") or rel.get("target_id")
        if name and target:
            out.append({"name": clean_name(name), "object": str(target)})
    return out


def extract_detection_objects(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("ground_truth", "detections", "det"):
        value = row.get(key)
        if isinstance(value, dict):
            detections = value.get("detections") or value.get("objects")
            normalized = normalize_detection_list(detections)
            if normalized:
                return normalized
        normalized = normalize_detection_list(value)
        if normalized:
            return normalized
    return {}


def normalize_detection_list(value: Any) -> dict[str, Any]:
    detections = as_list(value)
    out: dict[str, Any] = {}
    for idx, det in enumerate(detections, start=1):
        if not isinstance(det, dict):
            continue
        name = clean_name(det.get("label") or det.get("name"))
        if not name:
            continue
        attrs = det.get("attributes") or det.get("attrs") or []
        if isinstance(attrs, dict):
            attrs = [k for k, v in attrs.items() if v not in (False, None, "")]
        out[str(idx)] = {
            "name": name,
            "attributes": [clean_name(a) for a in as_list(attrs) if clean_name(a)],
            "relations": [],
        }
    return out


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    try:
        import numpy as np  # type: ignore

        if isinstance(value, np.ndarray):
            return value.tolist()
    except Exception:
        pass
    return [value]


if __name__ == "__main__":
    raise SystemExit(main())

