#!/usr/bin/env python3
"""Shared helpers for lightweight VLM evaluation scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
SPACE_RE = re.compile(r"\s+")


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


def clean_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9 /]+", "", text)
    return SPACE_RE.sub(" ", text).strip()


def article_phrase(name: str) -> str:
    name = clean_name(name)
    if name == "scissors":
        return "a pair of scissors"
    if name == "skis":
        return "a pair of skis"
    if name.endswith("s") and name not in {"bus"}:
        return name
    article = "an" if name[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {name}"


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


def load_json(path: str | Path) -> Any:
    with repo_path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def write_json(path: str | Path, payload: Any) -> None:
    path = repo_path(path)
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


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


def read_id_set(path: str | Path) -> set[str]:
    with repo_path(path).open("r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

