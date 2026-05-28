#!/usr/bin/env python3
"""Prepare paraphrased CEPO evidence-probe eval files.

The labels, images, and sampled rows are copied from the locked CEPO probes.
Only the wording of the evaluation question and candidate evidence is changed,
so this checks template robustness without introducing new annotation noise.
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from common import clean_name, load_jsonl, write_json, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supported-input", default="data/eval/cepo_evidence_probe.jsonl")
    parser.add_argument("--wrong-input", default="data/eval/cepo_wrong_evidence_probe.jsonl")
    parser.add_argument("--supported-output", default="data/eval/cepo_evidence_probe_paraphrase.jsonl")
    parser.add_argument("--wrong-output", default="data/eval/cepo_wrong_evidence_probe_paraphrase.jsonl")
    parser.add_argument("--summary-output", default="data/eval/cepo_paraphrase_probe.summary.json")
    args = parser.parse_args()

    supported = [paraphrase_row(row, idx) for idx, row in enumerate(load_jsonl(args.supported_input))]
    wrong = [paraphrase_row(row, idx) for idx, row in enumerate(load_jsonl(args.wrong_input))]

    write_jsonl(args.supported_output, supported)
    write_jsonl(args.wrong_output, wrong)
    write_json(
        args.summary_output,
        {
            "supported_input": args.supported_input,
            "wrong_input": args.wrong_input,
            "supported_output": args.supported_output,
            "wrong_output": args.wrong_output,
            "supported_total": len(supported),
            "wrong_total": len(wrong),
            "supported_by_task": count_by(supported, "base_task_type"),
            "wrong_by_task": count_by(wrong, "base_task_type"),
            "paraphrase_policy": (
                "same rows and targets as the locked CEPO probes; changed prompt wording "
                "and rendered candidate evidence in natural-language variants"
            ),
        },
    )
    print(f"Wrote {len(supported)} paraphrased supported rows to {args.supported_output}")
    print(f"Wrote {len(wrong)} paraphrased wrong-evidence rows to {args.wrong_output}")
    print(f"Wrote summary to {args.summary_output}")
    return 0


def paraphrase_row(row: dict[str, Any], idx: int) -> dict[str, Any]:
    out = dict(row)
    out["id"] = f"{row['id']}_paraphrase"
    out["benchmark"] = "cepo_paraphrase_probe"
    out["question"] = build_question(row, idx)
    out["paraphrase_source_id"] = row["id"]
    out["paraphrase_variant"] = str(idx % 3)
    return out


def build_question(row: dict[str, Any], idx: int) -> str:
    claim = str(row.get("target_claim") or "")
    visual_question = visual_question_text(row)
    evidence = evidence_text(row, idx)
    templates = [
        (
            "Question for the image: {visual_question}\n"
            "Claim to verify: {claim}\n"
            "Proposed visual support: {evidence}\n"
            "Judge whether the proposed support is valid evidence for the claim."
        ),
        (
            "Image question: {visual_question}\n"
            "We are checking this claim: {claim}\n"
            "The candidate support says: {evidence}\n"
            "Does this support actually back up the claim in the image?"
        ),
        (
            "Consider the visual claim '{claim}' for the image question '{visual_question}'.\n"
            "Candidate support description: {evidence}\n"
            "Decide if that support should be accepted for the claim."
        ),
    ]
    return templates[idx % len(templates)].format(
        visual_question=visual_question,
        claim=claim,
        evidence=evidence,
    )


def evidence_text(row: dict[str, Any], idx: int) -> str:
    relation = row.get("target_relation")
    if relation:
        subject = clean_name(row.get("target_subject"))
        obj = clean_name(row.get("target_object"))
        direction = str(relation).replace("_of", " of").replace("_", " ")
        templates = [
            f"it identifies {subject} as being {direction} {obj}",
            f"the supporting relation is that {subject} is {direction} {obj}",
            f"a relation cue with subject {subject}, object {obj}, and direction {relation}",
        ]
        return templates[idx % len(templates)]

    label = clean_name(row.get("target_evidence_label")) or "unknown object"
    attr = attribute_from_claim(row.get("target_claim"))
    if attr:
        templates = [
            f"it describes {label} with attribute {attr}",
            f"the evidence phrase says the {label} is {attr}",
            f"a support cue naming {label} and the property {attr}",
        ]
    else:
        templates = [
            f"it points to the object category {label}",
            f"the proposed support is the visible label {label}",
            f"a support cue naming {label}",
        ]
    return templates[idx % len(templates)]


def visual_question_text(row: dict[str, Any]) -> str:
    claim = str(row.get("target_claim") or "")
    parsed_relation = relation_from_claim(claim)
    if parsed_relation:
        subject, relation, obj = parsed_relation
        direction = "left" if relation == "left_of" else "right"
        return f"Is the {subject} to the {direction} of the {obj}?"
    return extract_visual_question(str(row.get("question") or ""))


def extract_visual_question(question: str) -> str:
    for line in question.splitlines():
        prefix = "Visual question:"
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return question.splitlines()[0].strip() if question.splitlines() else "Is the claim visually supported?"


def attribute_from_claim(value: Any) -> str | None:
    text = clean_name(value)
    if " is " not in text:
        return None
    attr = text.rsplit(" is ", 1)[1].strip()
    return attr or None


def relation_from_claim(value: Any) -> tuple[str, str, str] | None:
    parts = str(value or "").strip().split()
    for idx, token in enumerate(parts):
        if token in {"left_of", "right_of"} and idx > 0 and idx + 1 < len(parts):
            return " ".join(parts[:idx]), token, " ".join(parts[idx + 1 :])
    return None


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "unknown") for row in rows).items()))


if __name__ == "__main__":
    raise SystemExit(main())
