#!/usr/bin/env python3
"""Summarize locked base-error-mining diagnostic results."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from common import load_jsonl, repo_path, write_json
from score_object_eval import compute_base_metrics, score_row


MODEL_ORDER = ("base", "answer_dpo", "evidence_hint_dpo")
MODEL_LABELS = {
    "base": "Base Instruct",
    "answer_dpo": "Answer-DPO",
    "evidence_hint_dpo": "Evidence-Hint DPO",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-name", default="base_error_mined_object_existence")
    parser.add_argument("--variant", default="mixed")
    parser.add_argument("--results-root", default="results/eval/generations")
    parser.add_argument("--base-file", default=None)
    parser.add_argument("--answer-file", default=None)
    parser.add_argument("--evidence-file", default=None)
    parser.add_argument("--output", default="tasks/base-error-mining/results_summary.json")
    parser.add_argument("--markdown-output", default="tasks/base-error-mining/RESULTS.md")
    parser.add_argument("--min-group-size", type=int, default=20)
    args = parser.parse_args()

    model_files = {
        model_key: repo_path(args.results_root) / args.eval_name / args.variant / f"{model_key}.jsonl"
        for model_key in MODEL_ORDER
    }
    overrides = {
        "base": args.base_file,
        "answer_dpo": args.answer_file,
        "evidence_hint_dpo": args.evidence_file,
    }
    for model_key, override in overrides.items():
        if override:
            model_files[model_key] = repo_path(override)
    missing = [str(path) for path in model_files.values() if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required generation files: {missing}")

    summaries = {}
    for model_key, path in model_files.items():
        rows = [score_row(row) for row in load_jsonl(path)]
        summaries[model_key] = summarize_model(model_key, path, rows, args.min_group_size)

    deltas = compute_deltas(summaries)
    payload = {
        "eval_name": args.eval_name,
        "variant": args.variant,
        "model_files": {key: str(path) for key, path in model_files.items()},
        "models": summaries,
        "deltas": deltas,
    }
    write_json(args.output, payload)
    write_markdown(args.markdown_output, payload)

    print(f"Wrote base-error mining JSON summary to {repo_path(args.output)}")
    print(f"Wrote base-error mining Markdown summary to {repo_path(args.markdown_output)}")
    return 0


def summarize_model(
    model_key: str,
    path: Path,
    rows: list[dict[str, Any]],
    min_group_size: int,
) -> dict[str, Any]:
    metrics = compute_base_metrics(rows)
    recovery = {
        "overall": metrics["accuracy"],
        "false_positive": group_accuracy(rows, "base_error_type", "false_positive"),
        "false_negative": group_accuracy(rows, "base_error_type", "false_negative"),
    }
    return {
        "label": MODEL_LABELS[model_key],
        "path": str(path),
        "total": len(rows),
        "recovery": recovery,
        "accuracy": metrics["accuracy"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "false_positive_rate": metrics["false_positive_rate"],
        "false_negative_rate": metrics["false_negative_rate"],
        "refusal_rate": metrics["refusal_rate"],
        "other_rate": metrics["other_rate"],
        "invalid_prediction_rate": metrics["invalid_prediction_rate"],
        "confusion": metrics["confusion"],
        "target_counts": metrics["target_counts"],
        "prediction_counts": metrics["prediction_counts"],
        "base_error_type_counts": dict(sorted(Counter(row.get("base_error_type") for row in rows).items())),
        "category_breakdown": grouped_accuracy(rows, "target_object", min_group_size),
        "strategy_breakdown": grouped_accuracy(rows, "candidate_strategy", min_group_size),
    }


def group_accuracy(rows: list[dict[str, Any]], field: str, value: str) -> float:
    group = [row for row in rows if row.get(field) == value]
    if not group:
        return 0.0
    return round(sum(1 for row in group if row.get("is_correct")) / len(group), 6)


def grouped_accuracy(rows: list[dict[str, Any]], field: str, min_group_size: int) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(field)
        if value in (None, ""):
            continue
        groups.setdefault(str(value), []).append(row)
    out = {}
    for value, items in sorted(groups.items()):
        if len(items) < min_group_size:
            continue
        out[value] = {
            "n": len(items),
            "accuracy": round(sum(1 for row in items if row.get("is_correct")) / len(items), 6),
            "refusal_rate": round(sum(1 for row in items if row.get("is_refusal")) / len(items), 6),
            "other_rate": round(sum(1 for row in items if row.get("prediction") == "other") / len(items), 6),
        }
    return out


def compute_deltas(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    answer = summaries["answer_dpo"]["recovery"]
    evidence = summaries["evidence_hint_dpo"]["recovery"]
    return {
        "evidence_hint_minus_answer_dpo": {
            key: round(float(evidence.get(key, 0.0)) - float(answer.get(key, 0.0)), 6)
            for key in sorted(set(answer) | set(evidence))
        }
    }


def write_markdown(path: str, payload: dict[str, Any]) -> None:
    output_path = repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Base-Error Mining Results",
        "",
        "This diagnostic set is conditioned on Base Instruct errors, so the table measures error recovery rather than unbiased benchmark accuracy.",
        "",
        "## Locked-Set Recovery",
        "",
        "| Model | Rows | Recovery Acc | FP Recovery | FN Recovery | Refusal | Other |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model_key in MODEL_ORDER:
        model = payload["models"][model_key]
        recovery = model["recovery"]
        lines.append(
            "| {label} | {rows} | {overall:.3f} | {fp:.3f} | {fn:.3f} | {refusal:.3f} | {other:.3f} |".format(
                label=model["label"],
                rows=model["total"],
                overall=recovery["overall"],
                fp=recovery["false_positive"],
                fn=recovery["false_negative"],
                refusal=model["refusal_rate"],
                other=model["other_rate"],
            )
        )
    delta = payload["deltas"]["evidence_hint_minus_answer_dpo"]
    lines.extend(
        [
            "",
            "## Evidence-Hint Delta",
            "",
            "| Comparison | Overall | FP | FN |",
            "| --- | ---: | ---: | ---: |",
            (
                "| Evidence-Hint DPO - Answer-DPO | "
                f"{delta['overall']:.3f} | {delta['false_positive']:.3f} | {delta['false_negative']:.3f} |"
            ),
            "",
            "## Files",
            "",
        ]
    )
    for model_key, path_value in payload["model_files"].items():
        lines.append(f"- {MODEL_LABELS[model_key]}: `{path_value}`")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
