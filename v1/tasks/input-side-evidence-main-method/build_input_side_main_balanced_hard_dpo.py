#!/usr/bin/env python3
"""Build Balanced Hard Input-Side Evidence DPO data from existing artifacts."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").exists() and (parent / "scripts").exists():
            return parent
    raise RuntimeError("Could not locate repository root from task script path.")


REPO_ROOT = find_repo_root()
SPACE_RE = re.compile(r"\s+")

ARTICLE_OVERRIDES = {
    "scissors": "a pair of scissors",
    "skis": "a pair of skis",
}
PLURAL_OVERRIDES = {"scissors", "skis"}
SINGULAR_S_ENDINGS = {"bus", "wine glass"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--hard-eval", default="data/eval/coco_hard_object_existence.jsonl")
    parser.add_argument("--base-error-mined", default="data/eval/base_error_mined_object_existence.jsonl")
    parser.add_argument(
        "--output",
        default="data/processed/input_side_main_balanced_hard_dpo_train.jsonl",
    )
    parser.add_argument(
        "--summary-output",
        default="data/processed/input_side_main_balanced_hard_dpo_summary.json",
    )
    parser.add_argument(
        "--llamafactory-dir",
        default="experiments/llamafactory_data_input_side_main",
    )
    parser.add_argument("--dataset-key", default="cvpr_input_side_main_balanced_hard_dpo")
    parser.add_argument("--total-rows", type=int, default=5500)
    parser.add_argument("--hard-rows", type=int, default=1000)
    parser.add_argument("--base-error-rows", type=int, default=1000)
    parser.add_argument("--gqa-anchor-rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    canonical = load_jsonl(args.canonical)
    hard_eval = load_jsonl(args.hard_eval)
    base_error = load_jsonl(args.base_error_mined)

    canonical_coco_rows = args.total_rows - args.hard_rows - args.base_error_rows - args.gqa_anchor_rows
    if canonical_coco_rows < 0:
        raise ValueError("Requested slice rows exceed --total-rows")

    records: list[dict[str, Any]] = []
    records.extend(select_hard_coco_records(hard_eval, args.hard_rows, rng))
    records.extend(select_base_error_records(base_error, args.base_error_rows, rng))
    records.extend(select_canonical_coco_records(canonical, canonical_coco_rows, rng))
    records.extend(select_gqa_anchor_records(canonical, args.gqa_anchor_rows, rng))
    rng.shuffle(records)

    write_jsonl(args.output, records)
    write_llamafactory(records, args.llamafactory_dir, args.dataset_key)
    write_json(args.summary_output, build_summary(args, canonical_coco_rows, records))
    print(f"Wrote {len(records)} DPO rows to {repo_path(args.output)}")
    print(f"Wrote LLaMA-Factory data to {repo_path(args.llamafactory_dir)}")
    print(f"Wrote summary to {repo_path(args.summary_output)}")
    return 0


def select_hard_coco_records(rows: list[dict[str, Any]], requested_rows: int, rng: random.Random) -> list[dict[str, Any]]:
    pairs = paired_eval_rows(rows, source_family="hard_coco")
    return flatten_selected_pairs(pairs, requested_rows, rng, "hard_coco")


def select_base_error_records(rows: list[dict[str, Any]], requested_rows: int, rng: random.Random) -> list[dict[str, Any]]:
    pairs = []
    for row in rows:
        pos = clean_name(row.get("positive_object"))
        neg = clean_name(row.get("negative_object"))
        if not pos or not neg:
            continue
        common = {
            "image": row["image"],
            "image_id": row.get("image_id"),
            "pair_id": row.get("pair_id", row.get("id")),
            "positive_object": pos,
            "negative_object": neg,
            "base_error_type": row.get("base_error_type"),
            "source_candidate_id": row.get("source_candidate_id"),
        }
        pairs.append(
            (
                {
                    **common,
                    "id": f"{row['id']}::present::{slug(pos)}",
                    "target": "yes",
                    "target_object": pos,
                    "source": "input_side_main_base_error_pair",
                    "task_type": "object_existence",
                },
                {
                    **common,
                    "id": f"{row['id']}::absent::{slug(neg)}",
                    "target": "no",
                    "target_object": neg,
                    "source": "input_side_main_base_error_pair",
                    "task_type": "object_existence",
                },
            )
        )
    return flatten_selected_pairs(pairs, requested_rows, rng, "base_error_pair")


def select_canonical_coco_records(rows: list[dict[str, Any]], requested_rows: int, rng: random.Random) -> list[dict[str, Any]]:
    pairs = []
    for row in rows:
        if row.get("source") != "coco":
            continue
        label = row.get("label") or {}
        pos = clean_name(label.get("positive_object"))
        neg = clean_name(label.get("negative_object"))
        if not pos or not neg:
            continue
        common = {
            "image": row["image"],
            "image_id": row.get("image_id"),
            "pair_id": row.get("id"),
            "positive_object": pos,
            "negative_object": neg,
        }
        pairs.append(
            (
                {
                    **common,
                    "id": f"{row['id']}::present::{slug(pos)}",
                    "target": "yes",
                    "target_object": pos,
                    "source": "input_side_main_canonical_coco_pair",
                    "task_type": "object_existence",
                },
                {
                    **common,
                    "id": f"{row['id']}::absent::{slug(neg)}",
                    "target": "no",
                    "target_object": neg,
                    "source": "input_side_main_canonical_coco_pair",
                    "task_type": "object_existence",
                },
            )
        )
    return flatten_selected_pairs(pairs, requested_rows, rng, "canonical_coco_pair")


def select_gqa_anchor_records(rows: list[dict[str, Any]], requested_rows: int, rng: random.Random) -> list[dict[str, Any]]:
    anchors = []
    for row in rows:
        if row.get("source") != "gqa":
            continue
        anchors.append(
            {
                "id": f"{row['id']}::input_side_anchor",
                "image": row["image"],
                "image_id": row.get("image_id"),
                "prompt": prompt(row["question"], evidence_body(row["evidence_hint_chosen"])),
                "chosen": row["chosen_answer"],
                "rejected": row["rejected_answer"],
                "source": "input_side_main_gqa_anchor",
                "task_type": row.get("task_type"),
                "origin_id": row.get("id"),
            }
        )
    if requested_rows > len(anchors):
        raise ValueError(f"Need {requested_rows} GQA anchors but only found {len(anchors)}")
    return rng.sample(anchors, requested_rows)


def paired_eval_rows(rows: list[dict[str, Any]], source_family: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("task_type") != "object_existence":
            continue
        if row.get("target") not in {"yes", "no"}:
            continue
        grouped[str(row.get("pair_id") or row["id"])].append(row)

    pairs = []
    for group_rows in grouped.values():
        yes_rows = [row for row in group_rows if row.get("target") == "yes"]
        no_rows = [row for row in group_rows if row.get("target") == "no"]
        if not yes_rows or not no_rows:
            continue
        yes_row = dict(yes_rows[0])
        no_row = dict(no_rows[0])
        yes_row["source"] = f"input_side_main_{source_family}_pair"
        no_row["source"] = f"input_side_main_{source_family}_pair"
        pairs.append((yes_row, no_row))
    return pairs


def flatten_selected_pairs(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    requested_rows: int,
    rng: random.Random,
    label: str,
) -> list[dict[str, Any]]:
    if requested_rows % 2 != 0:
        raise ValueError(f"{label} requested_rows must be even")
    requested_pairs = requested_rows // 2
    if requested_pairs > len(pairs):
        raise ValueError(f"Need {requested_pairs} {label} pairs but only found {len(pairs)}")
    selected = rng.sample(pairs, requested_pairs)
    out = []
    for yes_row, no_row in selected:
        out.append(object_dpo_record(yes_row))
        out.append(object_dpo_record(no_row))
    return out


def object_dpo_record(row: dict[str, Any]) -> dict[str, Any]:
    target = row["target"]
    target_object = clean_name(row.get("target_object"))
    if target not in {"yes", "no"}:
        raise ValueError(f"Unsupported object target: {target}")
    if not target_object:
        raise ValueError(f"Missing target_object for {row.get('id')}")

    if target == "yes":
        cue = support_cue(target_object)
        chosen = yes_answer(target_object)
        rejected = no_answer(target_object)
    else:
        cue = unsupported_cue(target_object)
        chosen = no_answer(target_object)
        rejected = yes_answer(target_object)

    return {
        "id": row["id"],
        "image": row["image"],
        "prompt": prompt(existence_question(target_object), cue),
        "chosen": chosen,
        "rejected": rejected,
        "source": row.get("source"),
        "task_type": row.get("task_type"),
        "target": target,
        "target_object": target_object,
        "pair_id": row.get("pair_id"),
        "positive_object": row.get("positive_object"),
        "negative_object": row.get("negative_object"),
        "base_error_type": row.get("base_error_type"),
        "source_candidate_id": row.get("source_candidate_id"),
    }


def prompt(question: str, cue: str | None = None) -> str:
    parts = ["<image>"]
    if cue:
        parts.append(f"Visual cue: {str(cue).strip()}")
    parts.append(f"Question: {str(question).strip()}")
    parts.append("Answer:")
    return "\n".join(parts)


def evidence_body(hint: str) -> str:
    prefix = "Evidence hint:"
    if prefix not in hint:
        raise ValueError(f"Missing evidence hint prefix: {hint}")
    return hint.split(prefix, 1)[1].strip()


def support_cue(obj: str) -> str:
    return f"{article_phrase(obj)} {be_verb(obj)} visually supported in the image."


def unsupported_cue(obj: str) -> str:
    return f"{article_phrase(obj)} {be_verb(obj)} not visually supported in the image."


def yes_answer(obj: str) -> str:
    return f"Yes, there {be_verb(obj)} {article_phrase(obj)} in the image."


def no_answer(obj: str) -> str:
    name = clean_name(obj)
    if is_plural(name):
        return f"No, there are no {name} in the image."
    return f"No, there is no {name} in the image."


def existence_question(obj: str) -> str:
    phrase = article_phrase(obj)
    if is_plural(obj):
        return f"Are there {phrase} in the image?"
    return f"Is there {phrase} in the image?"


def article_phrase(name: str) -> str:
    name = clean_name(name)
    if name in ARTICLE_OVERRIDES:
        return ARTICLE_OVERRIDES[name]
    if is_plural(name):
        return name
    article = "an" if name[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {name}"


def be_verb(name: str) -> str:
    return "are" if is_plural(name) else "is"


def is_plural(name: str) -> bool:
    name = clean_name(name)
    return name in PLURAL_OVERRIDES or (name.endswith("s") and name not in SINGULAR_S_ENDINGS)


def clean_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9 /]+", "", text)
    return SPACE_RE.sub(" ", text).strip()


def slug(value: str) -> str:
    return clean_name(value).replace(" ", "_").replace("/", "_")


def build_summary(args: argparse.Namespace, canonical_coco_rows: int, records: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(record.get("source", "unknown") for record in records)
    target_counts = Counter(record.get("target", "non_yesno") for record in records)
    task_counts = Counter(record.get("task_type", "unknown") for record in records)
    object_counts = Counter(record.get("target_object") for record in records if record.get("target_object"))
    response_evidence_rows = sum(
        1
        for record in records
        if "Evidence:" in record["chosen"] or "Evidence:" in record["rejected"]
    )
    prompt_cue_rows = sum(1 for record in records if "Visual cue:" in record["prompt"])
    return {
        "seed": args.seed,
        "total_rows": len(records),
        "requested": {
            "total_rows": args.total_rows,
            "hard_rows": args.hard_rows,
            "base_error_rows": args.base_error_rows,
            "canonical_coco_rows": canonical_coco_rows,
            "gqa_anchor_rows": args.gqa_anchor_rows,
        },
        "sources": dict(sorted(source_counts.items())),
        "targets": dict(sorted(target_counts.items())),
        "tasks": dict(sorted(task_counts.items())),
        "unique_images": len({record.get("image_id") or record.get("image") for record in records}),
        "prompt_cue_rows": prompt_cue_rows,
        "response_evidence_rows": response_evidence_rows,
        "top_target_objects": object_counts.most_common(20),
        "inputs": {
            "canonical": args.canonical,
            "hard_eval": args.hard_eval,
            "base_error_mined": args.base_error_mined,
        },
        "outputs": {
            "dpo_jsonl": args.output,
            "summary": args.summary_output,
            "llamafactory_dir": args.llamafactory_dir,
            "dataset_key": args.dataset_key,
        },
    }


def write_llamafactory(records: list[dict[str, Any]], output_dir: str | Path, dataset_key: str) -> None:
    output_dir = repo_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_name = f"{dataset_key}.json"
    payload = [llamafactory_record(record, idx) for idx, record in enumerate(records, start=1)]
    write_json(output_dir / data_name, payload)
    write_json(
        output_dir / "dataset_info.json",
        {
            dataset_key: {
                "file_name": data_name,
                "ranking": True,
                "formatting": "sharegpt",
                "columns": {
                    "messages": "conversations",
                    "chosen": "chosen",
                    "rejected": "rejected",
                    "images": "images",
                },
            }
        },
    )


def llamafactory_record(record: dict[str, Any], line_no: int) -> dict[str, Any]:
    image = record["image"]
    if not repo_path(image).exists():
        raise FileNotFoundError(f"{line_no}: image does not exist: {image}")
    return {
        "id": record["id"],
        "conversations": [{"from": "human", "value": record["prompt"]}],
        "chosen": {"from": "gpt", "value": record["chosen"]},
        "rejected": {"from": "gpt", "value": record["rejected"]},
        "images": [image],
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    with repo_path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
    return records


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    path = repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def write_json(path: str | Path, payload: Any) -> None:
    path = repo_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
