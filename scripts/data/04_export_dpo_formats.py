#!/usr/bin/env python3
"""Export canonical pairs to Answer-DPO, Evidence-Hint, and Phase-2 DPO JSONL."""

from __future__ import annotations

import argparse
import sys

from common import load_jsonl, repo_path, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/canonical_pairs_main.jsonl")
    parser.add_argument("--answer-output", default="data/processed/answer_dpo_train.jsonl")
    parser.add_argument(
        "--evidence-output",
        default="data/processed/evidence_hint_dpo_train.jsonl",
    )
    parser.add_argument(
        "--evidence-only-output",
        default="data/processed/phase2_evidence_only_dpo_train.jsonl",
    )
    parser.add_argument(
        "--input-side-evidence-output",
        default="data/processed/phase2_input_side_evidence_dpo_train.jsonl",
    )
    parser.add_argument(
        "--chosen-only-evidence-output",
        default="data/processed/phase2_chosen_only_evidence_dpo_train.jsonl",
    )
    parser.add_argument("--include-metadata", action="store_true")
    args = parser.parse_args()

    canonical_path = repo_path(args.input)
    if not canonical_path.exists():
        print(f"Missing canonical input: {canonical_path}", file=sys.stderr)
        return 2

    records = load_jsonl(canonical_path)
    answer_records = [export_answer(record, args.include_metadata) for record in records]
    evidence_records = [export_evidence(record, args.include_metadata) for record in records]
    evidence_only_records = [export_evidence_only(record, args.include_metadata) for record in records]
    input_side_records = [export_input_side_evidence(record, args.include_metadata) for record in records]
    chosen_only_records = [export_chosen_only_evidence(record, args.include_metadata) for record in records]

    answer_count = write_jsonl(args.answer_output, answer_records)
    evidence_count = write_jsonl(args.evidence_output, evidence_records)
    evidence_only_count = write_jsonl(args.evidence_only_output, evidence_only_records)
    input_side_count = write_jsonl(args.input_side_evidence_output, input_side_records)
    chosen_only_count = write_jsonl(args.chosen_only_evidence_output, chosen_only_records)
    print(f"Wrote {answer_count} Answer-DPO records to {repo_path(args.answer_output)}")
    print(f"Wrote {evidence_count} Evidence-Hint DPO records to {repo_path(args.evidence_output)}")
    print(f"Wrote {evidence_only_count} Phase-2 Evidence-Only records to {repo_path(args.evidence_only_output)}")
    print(f"Wrote {input_side_count} Phase-2 Input-Side Evidence records to {repo_path(args.input_side_evidence_output)}")
    print(f"Wrote {chosen_only_count} Phase-2 Chosen-Only Evidence records to {repo_path(args.chosen_only_evidence_output)}")
    return 0


def prompt(record: dict, cue: str | None = None) -> str:
    parts = ["<image>"]
    if cue:
        parts.append(cue)
    parts.append(f"Question: {record['question']}")
    parts.append("Answer:")
    return "\n".join(parts)


def base_record(record: dict, include_metadata: bool, cue: str | None = None) -> dict:
    out = {
        "id": record["id"],
        "image": record["image"],
        "prompt": prompt(record, cue),
    }
    if include_metadata:
        out.update(
            {
                "image_id": record.get("image_id"),
                "source": record.get("source"),
                "task_type": record.get("task_type"),
            }
        )
    return out


def export_answer(record: dict, include_metadata: bool) -> dict:
    out = base_record(record, include_metadata)
    out["chosen"] = record["chosen_answer"]
    out["rejected"] = record["rejected_answer"]
    return out


def export_evidence(record: dict, include_metadata: bool) -> dict:
    chosen_hint = record["evidence_hint_chosen"]
    rejected_hint = record["evidence_hint_rejected"]
    if "Evidence hint:" not in chosen_hint or "Evidence hint:" not in rejected_hint:
        raise ValueError(f"Missing evidence hint in canonical record {record.get('id')}")
    out = base_record(record, include_metadata)
    out["chosen"] = f"{record['chosen_answer']}\n{chosen_hint}"
    out["rejected"] = f"{record['rejected_answer']}\n{rejected_hint}"
    return out


def export_evidence_only(record: dict, include_metadata: bool) -> dict:
    """Keep the answer fixed and make evidence consistency the only preference signal."""
    chosen_hint = evidence_line(record["evidence_hint_chosen"])
    rejected_hint = evidence_line(record["evidence_hint_rejected"])
    out = base_record(record, include_metadata)
    out["chosen"] = f"{record['chosen_answer']}\n{chosen_hint}"
    out["rejected"] = f"{record['chosen_answer']}\n{rejected_hint}"
    return out


def export_input_side_evidence(record: dict, include_metadata: bool) -> dict:
    """Move supported evidence to the user-side context and keep responses plain."""
    cue = f"Visual cue: {evidence_body(record['evidence_hint_chosen'])}"
    out = base_record(record, include_metadata, cue=cue)
    out["chosen"] = record["chosen_answer"]
    out["rejected"] = record["rejected_answer"]
    return out


def export_chosen_only_evidence(record: dict, include_metadata: bool) -> dict:
    """Attach supported evidence only to the chosen response."""
    out = base_record(record, include_metadata)
    out["chosen"] = f"{record['chosen_answer']}\n{evidence_line(record['evidence_hint_chosen'])}"
    out["rejected"] = record["rejected_answer"]
    return out


def evidence_line(hint: str) -> str:
    return f"Evidence: {evidence_body(hint)}"


def evidence_body(hint: str) -> str:
    prefix = "Evidence hint:"
    if prefix not in hint:
        raise ValueError(f"Missing evidence hint prefix: {hint}")
    return hint.split(prefix, 1)[1].strip()


if __name__ == "__main__":
    raise SystemExit(main())
