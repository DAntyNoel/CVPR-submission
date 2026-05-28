#!/usr/bin/env python3
"""Summarize fixed-budget CEPO control metrics."""

from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from pathlib import Path
from typing import Any

from common import load_json, repo_path


EVALS = OrderedDict(
    [
        ("coco", "coco_heldout_object_existence"),
        ("gqa", "gqa_simple_heldout"),
        ("hard", "coco_hard_object_existence"),
    ]
)
FIELDNAMES = [
    "experiment_id",
    "label",
    "model_key",
    "answer_rows",
    "verifier_rows",
    "total_rows",
    "coco_acc",
    "coco_fpr",
    "coco_fnr",
    "gqa_acc",
    "gqa_fpr",
    "gqa_fnr",
    "hard_acc",
    "hard_fpr",
    "hard_fnr",
    "bem_recovery",
    "supported_acc",
    "wrong_rejection",
    "object_wrong",
    "attribute_wrong",
    "relation_wrong",
    "json_object",
    "scored_output",
    "parse_fail",
    "status",
    "notes",
]
FIXED_ROWS = OrderedDict(
    [
        (
            "answer4k",
            {
                "label": "Answer-4k",
                "model_key": "cepo_answer4k_dpo",
                "answer_rows": 4000,
                "verifier_rows": 0,
                "total_rows": 4000,
                "variant": "cepo_fixed_budget/answer4k",
                "probe_variant": "cepo_fixed_budget/answer4k",
                "notes": "Answer-row-count control; not used for main claim.",
            },
        ),
        (
            "dual1k_fixed6k",
            {
                "label": "Dual-1k-fixed6k",
                "model_key": "cepo_fixed6k_dual1k_dpo",
                "answer_rows": 5000,
                "verifier_rows": 1000,
                "total_rows": 6000,
                "variant": "cepo_fixed_budget/dual1k_fixed6k",
                "probe_variant": "cepo_fixed_budget/dual1k_fixed6k",
                "notes": "Fixed 6k-row control with 500 supported + 500 wrong verifier rows.",
            },
        ),
        (
            "dual2k_fixed6k",
            {
                "label": "Dual-2k-fixed6k",
                "model_key": "cepo_fixed6k_dual2k_dpo",
                "answer_rows": 4000,
                "verifier_rows": 2000,
                "total_rows": 6000,
                "variant": "cepo_fixed_budget/dual2k_fixed6k",
                "probe_variant": "cepo_fixed_budget/dual2k_fixed6k",
                "notes": "Primary fixed-budget control with 1000 supported + 1000 wrong verifier rows.",
            },
        ),
    ]
)
REFERENCES = OrderedDict(
    [
        (
            "answer_dpo_6k",
            {
                "label": "CEPO Answer-DPO-6k",
                "model_key": "cepo_answer_dpo",
                "answer_rows": 6000,
                "verifier_rows": 0,
                "total_rows": 6000,
                "variant": "cepo_dual",
                "probe_variant": "cepo_dual_evidence_probe",
                "notes": "Locked seed-42 reference; reused, not retrained.",
            },
        ),
        (
            "dual2k_original",
            {
                "label": "CEPO-Dual-2k original",
                "model_key": "cepo_dual_dpo",
                "answer_rows": 6000,
                "verifier_rows": 2000,
                "total_rows": 8000,
                "variant": "cepo_dual",
                "probe_variant": "cepo_dual_evidence_probe",
                "notes": "Original 8k-row context; not a fixed-budget control.",
            },
        ),
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-csv",
        default="v2/tasks/fixed-budget-control-experiments/results/metrics.csv",
    )
    parser.add_argument(
        "--output-md",
        default="v2/tasks/fixed-budget-control-experiments/results/summary.md",
    )
    args = parser.parse_args()

    fixed_rows = OrderedDict((key, summarize_spec(key, spec)) for key, spec in FIXED_ROWS.items())
    references = OrderedDict((key, summarize_spec(key, spec)) for key, spec in REFERENCES.items())

    write_csv(args.output_csv, fixed_rows.values())
    write_summary(args.output_md, fixed_rows, references)
    print(f"Wrote fixed-budget metrics to {repo_path(args.output_csv)}")
    print(f"Wrote fixed-budget summary to {repo_path(args.output_md)}")
    return 0


def summarize_spec(experiment_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    variant = spec["variant"]
    probe_variant = spec["probe_variant"]
    model_key = spec["model_key"]

    short_metrics = {}
    for prefix, eval_name in EVALS.items():
        short_metrics[prefix] = safe_load(metrics_path(eval_name, variant, model_key))

    bem = safe_load(metrics_path("base_error_mined_object_existence", variant, model_key))
    supported = safe_load(metrics_path("cepo_evidence_probe", probe_variant, model_key))
    wrong = safe_load(metrics_path("cepo_wrong_evidence_probe", probe_variant, model_key))
    wrong_slices = wrong_slice_metrics(wrong)
    parse_fail = weighted_rate(
        [
            (number(supported, "parse_failure_rate"), number(supported, "total")),
            (number(wrong, "parse_failure_rate"), number(wrong, "total")),
        ]
    )
    json_object = weighted_rate(
        [
            (inverse_rate(supported, "invalid_json_rate"), number(supported, "total")),
            (inverse_rate(wrong, "invalid_json_rate"), number(wrong, "total")),
        ]
    )
    required = list(short_metrics.values()) + [bem, supported, wrong]
    status = "ready" if all(required) else "pending"

    return {
        "experiment_id": experiment_id,
        "label": spec["label"],
        "model_key": model_key,
        "answer_rows": spec["answer_rows"],
        "verifier_rows": spec["verifier_rows"],
        "total_rows": spec["total_rows"],
        "coco_acc": number(short_metrics["coco"], "accuracy"),
        "coco_fpr": number(short_metrics["coco"], "false_positive_rate"),
        "coco_fnr": number(short_metrics["coco"], "false_negative_rate"),
        "gqa_acc": number(short_metrics["gqa"], "accuracy"),
        "gqa_fpr": number(short_metrics["gqa"], "false_positive_rate"),
        "gqa_fnr": number(short_metrics["gqa"], "false_negative_rate"),
        "hard_acc": number(short_metrics["hard"], "accuracy"),
        "hard_fpr": number(short_metrics["hard"], "false_positive_rate"),
        "hard_fnr": number(short_metrics["hard"], "false_negative_rate"),
        "bem_recovery": number(bem, "accuracy"),
        "supported_acc": number(supported, "support_accuracy"),
        "wrong_rejection": number(wrong, "wrong_evidence_rejection_accuracy"),
        "object_wrong": wrong_slices["object"],
        "attribute_wrong": wrong_slices["attribute"],
        "relation_wrong": wrong_slices["relation"],
        "json_object": json_object,
        "scored_output": (1.0 - parse_fail) if parse_fail is not None else None,
        "parse_fail": parse_fail,
        "status": status,
        "notes": missing_note(status, required, spec["notes"]),
    }


def metrics_path(eval_name: str, variant: str, model_key: str) -> Path:
    return repo_path("results/eval/generations") / eval_name / variant / f"{model_key}.metrics.json"


def safe_load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def number(metrics: dict[str, Any] | None, key: str) -> float | int | None:
    if not metrics:
        return None
    value = metrics.get(key)
    if isinstance(value, (int, float)):
        return value
    return None


def inverse_rate(metrics: dict[str, Any] | None, key: str) -> float | None:
    value = number(metrics, key)
    if value is None:
        return None
    return 1.0 - float(value)


def wrong_slice_metrics(metrics: dict[str, Any] | None) -> dict[str, float | None]:
    if not metrics:
        return {"object": None, "attribute": None, "relation": None}
    groups = metrics.get("by_base_task_type") or {}
    return {
        "object": nested_number(groups, "object_existence", "wrong_evidence_rejection_accuracy"),
        "attribute": weighted_rate(
            [
                (
                    nested_number(groups, "attribute_color", "wrong_evidence_rejection_accuracy"),
                    nested_number(groups, "attribute_color", "total"),
                ),
                (
                    nested_number(groups, "attribute_material", "wrong_evidence_rejection_accuracy"),
                    nested_number(groups, "attribute_material", "total"),
                ),
            ]
        ),
        "relation": nested_number(groups, "relation_spatial", "wrong_evidence_rejection_accuracy"),
    }


def nested_number(payload: dict[str, Any], group: str, key: str) -> float | int | None:
    value = (payload.get(group) or {}).get(key)
    if isinstance(value, (int, float)):
        return value
    return None


def weighted_rate(items: list[tuple[float | int | None, float | int | None]]) -> float | None:
    total = 0.0
    positives = 0.0
    for rate, count in items:
        if rate is None or count is None:
            continue
        total += float(count)
        positives += float(rate) * float(count)
    if total == 0:
        return None
    return round(positives / total, 6)


def missing_note(status: str, required: list[dict[str, Any] | None], base_note: str) -> str:
    if status == "ready":
        return base_note
    missing_count = sum(1 for item in required if item is None)
    return f"{base_note} Pending {missing_count} metric file(s)."


def write_csv(path: str | Path, rows: Any) -> None:
    output = repo_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row[key]) for key in FIELDNAMES})


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def write_summary(
    path: str | Path,
    fixed_rows: OrderedDict[str, dict[str, Any]],
    references: OrderedDict[str, dict[str, Any]],
) -> None:
    output = repo_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_summary(fixed_rows, references), encoding="utf-8")


def render_summary(
    fixed_rows: OrderedDict[str, dict[str, Any]],
    references: OrderedDict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Fixed-Budget Control Summary",
        "",
        f"Status: {overall_status(fixed_rows)}.",
        "",
        "## Fixed-Budget Rows",
        "",
        "| Setting | Answer | Verifier | Total | COCO | GQA | Hard | BEM | Supported | Wrong | Obj | Attr | Rel | JSON obj | Parse fail |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in fixed_rows.values():
        lines.append(render_table_row(row))

    lines.extend(
        [
            "",
            "## References",
            "",
            "| Setting | Answer | Verifier | Total | COCO | GQA | Hard | BEM | Supported | Wrong | Obj | Attr | Rel | JSON obj | Parse fail |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in references.values():
        lines.append(render_table_row(row))

    lines.extend(["", "## Paper Integration Read", ""])
    lines.extend(render_integration_read(fixed_rows, references))
    lines.append("")
    return "\n".join(lines)


def overall_status(rows: OrderedDict[str, dict[str, Any]]) -> str:
    if all(row["status"] == "ready" for row in rows.values()):
        return "complete"
    ready = sum(1 for row in rows.values() if row["status"] == "ready")
    return f"pending Slurm completion ({ready}/{len(rows)} rows ready)"


def render_table_row(row: dict[str, Any]) -> str:
    return (
        f"| {row['label']} | {row['answer_rows']} | {row['verifier_rows']} | {row['total_rows']} | "
        f"{fmt_pct(row['coco_acc'])} | {fmt_pct(row['gqa_acc'])} | {fmt_pct(row['hard_acc'])} | "
        f"{fmt_pct(row['bem_recovery'])} | {fmt_pct(row['supported_acc'])} | {fmt_pct(row['wrong_rejection'])} | "
        f"{fmt_pct(row['object_wrong'])} | {fmt_pct(row['attribute_wrong'])} | {fmt_pct(row['relation_wrong'])} | "
        f"{fmt_pct(row['json_object'])} | {fmt_pct(row['parse_fail'])} |"
    )


def render_integration_read(
    fixed_rows: OrderedDict[str, dict[str, Any]],
    references: OrderedDict[str, dict[str, Any]],
) -> list[str]:
    answer = references["answer_dpo_6k"]
    fixed_dual2k = fixed_rows["dual2k_fixed6k"]
    required = [
        answer["wrong_rejection"],
        fixed_dual2k["wrong_rejection"],
        answer["coco_acc"],
        answer["gqa_acc"],
        answer["hard_acc"],
        fixed_dual2k["coco_acc"],
        fixed_dual2k["gqa_acc"],
        fixed_dual2k["hard_acc"],
    ]
    if any(value is None for value in required):
        return [
            "- Fixed-budget jobs are still pending. Do not integrate this control into the paper yet.",
            "- Once complete, compare Dual-2k-fixed6k against the locked CEPO Answer-DPO-6k reference using the stop rule in this task README.",
        ]

    wrong_delta = float(fixed_dual2k["wrong_rejection"]) - float(answer["wrong_rejection"])
    short_deltas = {
        "COCO": float(fixed_dual2k["coco_acc"]) - float(answer["coco_acc"]),
        "GQA": float(fixed_dual2k["gqa_acc"]) - float(answer["gqa_acc"]),
        "Hard": float(fixed_dual2k["hard_acc"]) - float(answer["hard_acc"]),
    }
    short_ok = all(delta >= -0.01 for delta in short_deltas.values())
    wrong_ok = wrong_delta >= 0.20
    deltas = ", ".join(f"{name} {fmt_delta(delta)}" for name, delta in short_deltas.items())
    lines = [
        f"- Dual-2k-fixed6k vs CEPO Answer-DPO-6k wrong-evidence rejection: {fmt_delta(wrong_delta)} pp.",
        f"- Short-answer deltas: {deltas}.",
    ]
    if wrong_ok and short_ok:
        lines.append(
            "- Paper action: add the fixed 6k-row appendix/control sentence that verifier replacement remains effective, so the original 2k gain is not only a total-row-count artifact."
        )
    else:
        lines.append(
            "- Paper action: use the conservative reading that verifier supervision and total training volume both contribute, then report the full control table in the appendix."
        )
    return lines


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "pending"
    return f"{100 * float(value):.1f}"


def fmt_delta(value: float) -> str:
    return f"{100 * value:+.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
