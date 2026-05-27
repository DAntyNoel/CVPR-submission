#!/usr/bin/env python3
"""Convert CEPO-Dual DPO JSONL to LLaMA-Factory multimodal preference JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dual-input", default="data/processed/cepo_dual/cepo_dual_dpo_train.jsonl")
    parser.add_argument("--output-dir", default="experiments/llamafactory_data_cepo_dual")
    args = parser.parse_args()

    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records = convert_file(resolve(args.dual_input))
    output_name = "cvpr_cepo_dual_dpo.json"
    output_path = output_dir / output_name
    write_json(output_path, records)
    write_json(output_dir / "dataset_info.json", dataset_info(output_name))

    print(f"Wrote {len(records)} CEPO-Dual DPO records to {output_path}")
    print(f"Wrote dataset registry to {output_dir / 'dataset_info.json'}")
    return 0


def resolve(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def convert_file(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            records.append(convert_record(json.loads(line), line_no))
    return records


def convert_record(record: dict[str, Any], line_no: int) -> dict[str, Any]:
    prompt = record["prompt"]
    if "<image>" not in prompt:
        prompt = "<image>\n" + prompt

    image = record["image"]
    if not resolve(image).exists():
        raise FileNotFoundError(f"{line_no}: image does not exist: {image}")

    return {
        "id": record["id"],
        "conversations": [{"from": "human", "value": prompt}],
        "chosen": {"from": "gpt", "value": record["chosen"]},
        "rejected": {"from": "gpt", "value": record["rejected"]},
        "images": [image],
    }


def dataset_info(output_name: str) -> dict[str, Any]:
    return {
        "cvpr_cepo_dual_dpo": {
            "file_name": output_name,
            "ranking": True,
            "formatting": "sharegpt",
            "columns": {
                "messages": "conversations",
                "chosen": "chosen",
                "rejected": "rejected",
                "images": "images",
            },
        }
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
