#!/usr/bin/env python3
"""Convert project DPO JSONL files to LLaMA-Factory multimodal preference JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer-input", default="data/processed/answer_dpo_train.jsonl")
    parser.add_argument("--evidence-input", default="data/processed/evidence_hint_dpo_train.jsonl")
    parser.add_argument("--output-dir", default="experiments/llamafactory_data")
    args = parser.parse_args()

    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    answer_records = convert_file(resolve(args.answer_input))
    evidence_records = convert_file(resolve(args.evidence_input))

    write_json(output_dir / "cvpr_answer_dpo.json", answer_records)
    write_json(output_dir / "cvpr_evidence_hint_dpo.json", evidence_records)
    write_json(output_dir / "dataset_info.json", dataset_info())

    print(f"Wrote {len(answer_records)} Answer-DPO records to {output_dir / 'cvpr_answer_dpo.json'}")
    print(f"Wrote {len(evidence_records)} Evidence-Hint DPO records to {output_dir / 'cvpr_evidence_hint_dpo.json'}")
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
            record = json.loads(line)
            records.append(convert_record(record, line_no))
    return records


def convert_record(record: dict[str, Any], line_no: int) -> dict[str, Any]:
    prompt = record["prompt"]
    if prompt.endswith("\nAnswer:"):
        prompt = prompt[: -len("\nAnswer:")]
    if "<image>" not in prompt:
        prompt = "<image>\n" + prompt

    image = record["image"]
    if not resolve(image).exists():
        raise FileNotFoundError(f"{line_no}: image does not exist: {image}")

    return {
        "id": record["id"],
        "conversations": [
            {
                "from": "human",
                "value": prompt,
            }
        ],
        "chosen": {
            "from": "gpt",
            "value": record["chosen"],
        },
        "rejected": {
            "from": "gpt",
            "value": record["rejected"],
        },
        "images": [image],
    }


def dataset_info() -> dict[str, Any]:
    common = {
        "ranking": True,
        "formatting": "sharegpt",
        "columns": {
            "messages": "conversations",
            "chosen": "chosen",
            "rejected": "rejected",
            "images": "images",
        },
    }
    return {
        "cvpr_answer_dpo": {
            "file_name": "cvpr_answer_dpo.json",
            **common,
        },
        "cvpr_evidence_hint_dpo": {
            "file_name": "cvpr_evidence_hint_dpo.json",
            **common,
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())

