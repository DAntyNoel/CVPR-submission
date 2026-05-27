#!/usr/bin/env python3
"""Convert project DPO JSONL files to LLaMA-Factory multimodal preference JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


DATASET_SPECS = [
    (
        "cvpr_answer_dpo",
        "answer_input",
        "data/processed/answer_dpo_train.jsonl",
        "cvpr_answer_dpo.json",
        "Answer-DPO",
    ),
    (
        "cvpr_evidence_hint_dpo",
        "evidence_input",
        "data/processed/evidence_hint_dpo_train.jsonl",
        "cvpr_evidence_hint_dpo.json",
        "Evidence-Hint DPO",
    ),
    (
        "cvpr_answer_evidence_mix_dpo",
        "answer_evidence_mix_input",
        "data/processed/answer_evidence_mix_dpo_train.jsonl",
        "cvpr_answer_evidence_mix_dpo.json",
        "Answer-Evidence Mix DPO",
    ),
    (
        "cvpr_phase2_evidence_only_dpo",
        "phase2_evidence_only_input",
        "data/processed/phase2_evidence_only_dpo_train.jsonl",
        "cvpr_phase2_evidence_only_dpo.json",
        "Phase-2 Evidence-Only DPO",
    ),
    (
        "cvpr_phase2_input_side_evidence_dpo",
        "phase2_input_side_evidence_input",
        "data/processed/phase2_input_side_evidence_dpo_train.jsonl",
        "cvpr_phase2_input_side_evidence_dpo.json",
        "Phase-2 Input-Side Evidence DPO",
    ),
    (
        "cvpr_phase2_chosen_only_evidence_dpo",
        "phase2_chosen_only_evidence_input",
        "data/processed/phase2_chosen_only_evidence_dpo_train.jsonl",
        "cvpr_phase2_chosen_only_evidence_dpo.json",
        "Phase-2 Chosen-Only Evidence DPO",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer-input", default="data/processed/answer_dpo_train.jsonl")
    parser.add_argument("--evidence-input", default="data/processed/evidence_hint_dpo_train.jsonl")
    parser.add_argument(
        "--answer-evidence-mix-input",
        default="data/processed/answer_evidence_mix_dpo_train.jsonl",
    )
    parser.add_argument(
        "--phase2-evidence-only-input",
        default="data/processed/phase2_evidence_only_dpo_train.jsonl",
    )
    parser.add_argument(
        "--phase2-input-side-evidence-input",
        default="data/processed/phase2_input_side_evidence_dpo_train.jsonl",
    )
    parser.add_argument(
        "--phase2-chosen-only-evidence-input",
        default="data/processed/phase2_chosen_only_evidence_dpo_train.jsonl",
    )
    parser.add_argument("--output-dir", default="experiments/llamafactory_data")
    args = parser.parse_args()

    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    registered: dict[str, str] = {}
    for dataset_key, input_arg, default_input_path, output_name, label in DATASET_SPECS:
        input_path = getattr(args, input_arg) or default_input_path
        records = convert_file(resolve(input_path))
        output_path = output_dir / output_name
        write_json(output_path, records)
        registered[dataset_key] = output_name
        print(f"Wrote {len(records)} {label} records to {output_path}")

    write_json(output_dir / "dataset_info.json", dataset_info(registered))
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


def dataset_info(registered: dict[str, str]) -> dict[str, Any]:
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
        dataset_key: {
            "file_name": file_name,
            **common,
        }
        for dataset_key, file_name in registered.items()
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
