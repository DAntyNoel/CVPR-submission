#!/usr/bin/env python3
"""Shared helpers for lightweight evidence-hint data processing."""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[^\w\s]", re.UNICODE)
SPACE_RE = re.compile(r"\s+")


ARTICLE_OVERRIDES = {
    "scissors": "a pair of scissors",
    "skis": "a pair of skis",
}


PLURAL_OVERRIDES = {
    "scissors",
    "skis",
}


def repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def repo_relative(path: str | Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_parent(path: str | Path) -> None:
    repo_path(path).parent.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path) -> Any:
    with repo_path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, payload: Any) -> None:
    path = repo_path(path)
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def iter_jsonl(path: str | Path) -> Iterable[dict[str, Any]]:
    with repo_path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL record") from exc


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> int:
    path = repo_path(path)
    ensure_parent(path)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")
            count += 1
    return count


def clean_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9 /]+", "", text)
    return SPACE_RE.sub(" ", text).strip()


def article_phrase(name: str) -> str:
    name = clean_name(name)
    if name in ARTICLE_OVERRIDES:
        return ARTICLE_OVERRIDES[name]
    if name.endswith("s") and name not in {"bus"}:
        return name
    article = "an" if name[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {name}"


def be_verb(name: str) -> str:
    name = clean_name(name)
    if name in PLURAL_OVERRIDES:
        return "are"
    if name.endswith("s") and name not in {"bus"}:
        return "are"
    return "is"


def token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text or ""))


def weighted_choice(
    items: list[str],
    weights: list[float],
    rng: random.Random,
) -> str:
    if not items:
        raise ValueError("weighted_choice received no items")
    total = sum(max(w, 0.0) for w in weights)
    if total <= 0:
        return rng.choice(items)
    return rng.choices(items, weights=weights, k=1)[0]


def load_image_id_set(paths: list[str] | None) -> set[str]:
    ids: set[str] = set()
    for raw_path in paths or []:
        path = repo_path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"image-id file not found: {path}")
        if path.suffix.lower() == ".jsonl":
            for record in iter_jsonl(path):
                ids.update(extract_image_ids(record))
        elif path.suffix.lower() == ".json":
            payload = load_json(path)
            if isinstance(payload, dict):
                if "image_ids" in payload and isinstance(payload["image_ids"], list):
                    ids.update(str(x) for x in payload["image_ids"])
                else:
                    ids.update(extract_image_ids(payload))
                    for value in payload.values():
                        ids.update(extract_image_ids(value))
            elif isinstance(payload, list):
                for value in payload:
                    ids.update(extract_image_ids(value))
        elif path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ids.update(extract_image_ids(row))
        else:
            with path.open("r", encoding="utf-8") as f:
                ids.update(line.strip() for line in f if line.strip())
    return {x for x in ids if x}


def extract_image_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if not isinstance(value, dict):
        return set()
    out: set[str] = set()
    for key in ("image_id", "imageId", "image", "img_id", "imageIdStr"):
        if key in value and value[key] not in (None, ""):
            out.add(str(value[key]))
    return out


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    task_counts = Counter(record.get("task_type", "unknown") for record in records)
    source_counts = Counter(record.get("source", "unknown") for record in records)
    label_counts: Counter[str] = Counter()
    for record in records:
        label = record.get("label") or {}
        for key in ("positive_object", "positive_attribute", "relation"):
            if label.get(key):
                label_counts[f"{key}:{label[key]}"] += 1
    return {
        "total": len(records),
        "sources": dict(sorted(source_counts.items())),
        "tasks": dict(sorted(task_counts.items())),
        "top_labels": label_counts.most_common(20),
        "avg_question_tokens": avg(token_count(r.get("question", "")) for r in records),
        "avg_chosen_tokens": avg(token_count(r.get("chosen_answer", "")) for r in records),
        "avg_rejected_tokens": avg(token_count(r.get("rejected_answer", "")) for r in records),
    }


def avg(values: Iterable[int]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)

