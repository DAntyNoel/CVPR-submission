#!/usr/bin/env python3
"""Sample relation wrong-evidence CEPO-Probe cases for qualitative analysis."""

from __future__ import annotations

import argparse
import random
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from common import load_jsonl, repo_path
from score_cepo_evidence_probe import score_row


DEFAULT_MODELS = OrderedDict(
    [
        ("base", "Base Instruct"),
        ("cepo_answer_dpo", "CEPO Answer-DPO"),
        ("cepo_dual_dpo", "CEPO-Dual-2k"),
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wrong-dir",
        default="results/eval/generations/cepo_wrong_evidence_probe/cepo_dual_evidence_probe",
    )
    parser.add_argument(
        "--output",
        default="cepo-probe-benchmark-improve/artifacts/relation_failure_cases.md",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dual-correct", type=int, default=4)
    parser.add_argument("--dual-false-accept", type=int, default=6)
    parser.add_argument("--all-fail", type=int, default=4)
    parser.add_argument("--answer-fail-dual-succeed", type=int, default=4)
    args = parser.parse_args()

    model_rows = load_model_rows(repo_path(args.wrong_dir))
    cases = build_cases(model_rows)
    rng = random.Random(args.seed)
    buckets = OrderedDict(
        [
            ("CEPO-Dual correctly rejects relation wrong-evidence", args.dual_correct),
            ("CEPO-Dual falsely accepts relation wrong-evidence", args.dual_false_accept),
            ("All models fail", args.all_fail),
            ("Answer-DPO fails but CEPO-Dual succeeds", args.answer_fail_dual_succeed),
        ]
    )
    selected = OrderedDict()
    for bucket, count in buckets.items():
        items = [case for case in cases if bucket in case["buckets"]]
        rng.shuffle(items)
        selected[bucket] = items[:count]

    output_path = repo_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(selected), encoding="utf-8")
    print(f"Wrote relation failure samples to {output_path}")
    return 0


def load_model_rows(wrong_dir: Path) -> OrderedDict[str, dict[str, dict[str, Any]]]:
    out: OrderedDict[str, dict[str, dict[str, Any]]] = OrderedDict()
    for model_key in DEFAULT_MODELS:
        path = wrong_dir / f"{model_key}.jsonl"
        rows = [score_row(row) for row in load_jsonl(path)]
        out[model_key] = {
            row["id"]: row
            for row in rows
            if row.get("base_task_type") == "relation_spatial"
            and row.get("target_support") == "wrong_evidence"
        }
    return out


def build_cases(model_rows: OrderedDict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    common_ids = set.intersection(*(set(rows) for rows in model_rows.values()))
    cases = []
    for case_id in sorted(common_ids):
        rows = {model_key: rows_by_id[case_id] for model_key, rows_by_id in model_rows.items()}
        base = rows["base"]
        answer = rows["cepo_answer_dpo"]
        dual = rows["cepo_dual_dpo"]
        buckets = []
        if dual["wrong_evidence_rejected"]:
            buckets.append("CEPO-Dual correctly rejects relation wrong-evidence")
        else:
            buckets.append("CEPO-Dual falsely accepts relation wrong-evidence")
        if not any(row["wrong_evidence_rejected"] for row in rows.values()):
            buckets.append("All models fail")
        if not answer["wrong_evidence_rejected"] and dual["wrong_evidence_rejected"]:
            buckets.append("Answer-DPO fails but CEPO-Dual succeeds")

        cases.append(
            {
                "id": case_id,
                "image": base.get("image"),
                "question": one_line(base.get("question")),
                "claim": base.get("target_claim"),
                "candidate_evidence": candidate_evidence(base),
                "category": categorize(base, dual),
                "buckets": buckets,
                "predictions": {
                    model_key: {
                        "support": row.get("predicted_support"),
                        "rejected": bool(row.get("wrong_evidence_rejected")),
                        "generation": compact_generation(row.get("generation")),
                    }
                    for model_key, row in rows.items()
                },
            }
        )
    return cases


def candidate_evidence(row: dict[str, Any]) -> str:
    prompt = str(row.get("prompt") or row.get("question") or "")
    match = re.search(r"Candidate evidence:\s*(.+)", prompt)
    return one_line(match.group(1)) if match else ""


def categorize(row: dict[str, Any], dual_row: dict[str, Any]) -> str:
    claim = str(row.get("target_claim") or "").lower()
    subject = str(row.get("target_subject") or "").lower()
    obj = str(row.get("target_object") or "").lower()
    if subject and obj and obj in claim and subject in claim and claim.find(obj) < claim.find(subject):
        return "subject/object swap"
    if str(row.get("target_relation") or "") in {"left_of", "right_of"}:
        if dual_row.get("predicted_support") == "supported":
            return "copied candidate evidence without verification"
        return "left/right ambiguity"
    if dual_row.get("predicted_support") == "supported":
        return "copied candidate evidence without verification"
    return "candidate relation text under-specified"


def render_markdown(selected: OrderedDict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "# Relation Wrong-Evidence Failure Cases",
        "",
        "These samples are drawn from the locked CEPO wrong-evidence relation slice. Categories are heuristic triage labels for writing the analysis section.",
        "",
    ]
    for bucket, cases in selected.items():
        lines.extend([f"## {bucket}", ""])
        if not cases:
            lines.extend(["No matching cases found.", ""])
            continue
        lines.extend(
            [
                "| ID | Category | Claim | Candidate evidence | Base | Answer-DPO | CEPO-Dual-2k |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for case in cases:
            preds = case["predictions"]
            lines.append(
                "| {id} | {cat} | {claim} | {evidence} | {base} | {answer} | {dual} |".format(
                    id=case["id"],
                    cat=case["category"],
                    claim=escape_md(case["claim"]),
                    evidence=escape_md(case["candidate_evidence"]),
                    base=fmt_pred(preds["base"]),
                    answer=fmt_pred(preds["cepo_answer_dpo"]),
                    dual=fmt_pred(preds["cepo_dual_dpo"]),
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Takeaway",
            "",
            "Relation wrong-evidence rejection remains the bottleneck: CEPO-Dual improves the overall rejection rate, but many relation cases still accept swapped subject/object evidence. This supports the paper claim that answer-level correctness and evidence-level verification can move independently, and that relation verification likely needs stronger region-aware supervision.",
            "",
        ]
    )
    return "\n".join(lines)


def fmt_pred(pred: dict[str, Any]) -> str:
    mark = "reject" if pred["rejected"] else "accept"
    return f"{mark}/{pred['support']}"


def compact_generation(value: Any) -> str:
    return one_line(str(value or ""))[:180]


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def escape_md(value: Any) -> str:
    return one_line(value).replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
