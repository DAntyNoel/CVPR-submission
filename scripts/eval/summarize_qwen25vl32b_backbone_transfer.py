#!/usr/bin/env python3
"""Summarize Qwen2.5-VL-32B backbone-transfer metrics."""

from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from pathlib import Path
from typing import Any

from common import load_json, load_jsonl, repo_path
from score_cepo_evidence_probe import score_row as score_probe_row


MODELS = OrderedDict(
    [
        ("base", "Qwen2.5-VL-32B Base"),
        ("cepo_answer_dpo", "32B CEPO Answer-DPO"),
        ("cepo_dual_dpo", "32B CEPO-Dual-2k"),
    ]
)
SHORT_EVALS = OrderedDict(
    [
        ("coco", "coco_heldout_object_existence"),
        ("gqa", "gqa_simple_heldout"),
        ("hard_coco", "coco_hard_object_existence"),
        ("bem", "base_error_mined_object_existence"),
    ]
)
PROBE_EVALS = OrderedDict(
    [
        ("supported", "cepo_evidence_probe"),
        ("wrong", "cepo_wrong_evidence_probe"),
        ("relation_stress", "relation_stress_probe"),
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="backbone_transfer/qwen25vl32b")
    parser.add_argument("--output-dir", default="v2/tasks/backbone-transfer-experiments/results")
    args = parser.parse_args()

    output_dir = repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(args.variant)
    write_csv(output_dir / "metrics.csv", rows)
    (output_dir / "transfer_summary.md").write_text(render_markdown(rows, args.variant), encoding="utf-8")
    print(f"Wrote metrics CSV to {output_dir / 'metrics.csv'}")
    print(f"Wrote summary to {output_dir / 'transfer_summary.md'}")
    return 0


def collect_rows(variant: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model_key, label in MODELS.items():
        for eval_key, eval_name in SHORT_EVALS.items():
            metrics = safe_load(metrics_path(eval_name, variant, model_key))
            status = "ready" if metrics else "pending"
            rows.extend(
                metric_rows(
                    model_key,
                    label,
                    eval_key,
                    metrics_path(eval_name, variant, model_key),
                    status,
                    {
                        "accuracy": value(metrics, "accuracy"),
                        "false_positive_rate": value(metrics, "false_positive_rate"),
                        "false_negative_rate": value(metrics, "false_negative_rate"),
                        "json_object_rate": None,
                        "scored_output_rate": invert(value(metrics, "invalid_prediction_rate")),
                        "parse_failure_rate": value(metrics, "invalid_prediction_rate"),
                    },
                )
            )

        supported = safe_load(metrics_path("cepo_evidence_probe", variant, model_key))
        wrong = safe_load(metrics_path("cepo_wrong_evidence_probe", variant, model_key))
        relation = safe_load(metrics_path("relation_stress_probe", variant, model_key))
        wrong_slices = wrong_slice_metrics(wrong)
        relation_slices = relation_stress_slices(variant, model_key)
        rows.extend(
            metric_rows(
                model_key,
                label,
                "cepo_supported",
                metrics_path("cepo_evidence_probe", variant, model_key),
                "ready" if supported else "pending",
                {
                    "support_accuracy": value(supported, "support_accuracy"),
                    "json_object_rate": invert(value(supported, "invalid_json_rate")),
                    "scored_output_rate": invert(value(supported, "parse_failure_rate")),
                    "parse_failure_rate": value(supported, "parse_failure_rate"),
                },
            )
        )
        rows.extend(
            metric_rows(
                model_key,
                label,
                "cepo_wrong",
                metrics_path("cepo_wrong_evidence_probe", variant, model_key),
                "ready" if wrong else "pending",
                {
                    "wrong_evidence_rejection": value(wrong, "wrong_evidence_rejection_accuracy"),
                    "object_wrong_rejection": wrong_slices["object"],
                    "attribute_wrong_rejection": wrong_slices["attribute"],
                    "relation_wrong_rejection": wrong_slices["relation"],
                    "json_object_rate": invert(value(wrong, "invalid_json_rate")),
                    "scored_output_rate": invert(value(wrong, "parse_failure_rate")),
                    "parse_failure_rate": value(wrong, "parse_failure_rate"),
                },
            )
        )
        rows.extend(
            metric_rows(
                model_key,
                label,
                "relation_stress",
                metrics_path("relation_stress_probe", variant, model_key),
                "ready" if relation else "pending",
                {
                    "overall_rejection": value(relation, "wrong_evidence_rejection_accuracy"),
                    "subject_object_swap_rejection": relation_slices["subject_object_swap"],
                    "left_right_reversal_rejection": relation_slices["left_right_reversal"],
                    "false_accept_rate": false_accept_rate(value(relation, "wrong_evidence_rejection_accuracy")),
                    "json_object_rate": invert(value(relation, "invalid_json_rate")),
                    "scored_output_rate": invert(value(relation, "parse_failure_rate")),
                    "parse_failure_rate": value(relation, "parse_failure_rate"),
                },
            )
        )
    return rows


def metric_rows(
    model_key: str,
    model_label: str,
    eval_key: str,
    path: Path,
    status: str,
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "model_key": model_key,
            "model_label": model_label,
            "eval": eval_key,
            "metric": key,
            "value": "" if metric_value is None else metric_value,
            "status": status,
            "source": str(path),
        }
        for key, metric_value in metrics.items()
    ]


def metrics_path(eval_name: str, variant: str, model_key: str) -> Path:
    return repo_path("results/eval/generations") / eval_name / variant / f"{model_key}.metrics.json"


def generation_path(eval_name: str, variant: str, model_key: str) -> Path:
    return repo_path("results/eval/generations") / eval_name / variant / f"{model_key}.jsonl"


def safe_load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def value(metrics: dict[str, Any] | None, key: str) -> float | int | None:
    if not metrics:
        return None
    item = metrics.get(key)
    if isinstance(item, (int, float)):
        return item
    return None


def invert(value_: float | int | None) -> float | None:
    if value_ is None:
        return None
    return round(1.0 - float(value_), 6)


def false_accept_rate(rejection: float | int | None) -> float | None:
    return invert(rejection)


def wrong_slice_metrics(metrics: dict[str, Any] | None) -> dict[str, float | None]:
    if not metrics:
        return {"object": None, "attribute": None, "relation": None}
    groups = metrics.get("by_base_task_type") or {}
    object_rate = nested_value(groups, "object_existence", "wrong_evidence_rejection_accuracy")
    relation_rate = nested_value(groups, "relation_spatial", "wrong_evidence_rejection_accuracy")
    attribute_rate = weighted_rate(
        [
            (
                nested_value(groups, "attribute_color", "wrong_evidence_rejection_accuracy"),
                nested_value(groups, "attribute_color", "total"),
            ),
            (
                nested_value(groups, "attribute_material", "wrong_evidence_rejection_accuracy"),
                nested_value(groups, "attribute_material", "total"),
            ),
        ]
    )
    return {
        "object": object_rate,
        "attribute": attribute_rate,
        "relation": relation_rate,
    }


def relation_stress_slices(variant: str, model_key: str) -> dict[str, float | None]:
    path = generation_path("relation_stress_probe", variant, model_key)
    if not path.exists():
        return {"subject_object_swap": None, "left_right_reversal": None}
    rows = [score_probe_row(row) for row in load_jsonl(path)]
    out: dict[str, float | None] = {}
    for stress_type in ("subject_object_swap", "left_right_reversal"):
        items = [row for row in rows if row.get("stress_type") == stress_type]
        out[stress_type] = rate(items, "wrong_evidence_rejected")
    return out


def nested_value(payload: dict[str, Any], group: str, key: str) -> float | int | None:
    item = payload.get(group) or {}
    value_ = item.get(key)
    if isinstance(value_, (int, float)):
        return value_
    return None


def weighted_rate(items: list[tuple[float | int | None, float | int | None]]) -> float | None:
    total = 0.0
    positives = 0.0
    for rate_, count in items:
        if rate_ is None or count is None:
            continue
        total += float(count)
        positives += float(rate_) * float(count)
    if total == 0:
        return None
    return round(positives / total, 6)


def rate(rows: list[dict[str, Any]], key: str) -> float | None:
    if not rows:
        return None
    return round(sum(1 for row in rows if row.get(key)) / len(rows), 6)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["model_key", "model_label", "eval", "metric", "value", "status", "source"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def render_markdown(rows: list[dict[str, Any]], variant: str) -> str:
    lines = [
        "# Qwen2.5-VL-32B Backbone Transfer Summary",
        "",
        f"Variant: `{variant}`",
        "",
        "## Status",
        "",
    ]
    pending = [row for row in rows if row["status"] != "ready"]
    if pending:
        pending_keys = sorted({f"{row['model_key']}:{row['eval']}" for row in pending})
        lines.append(f"Pending metrics: {', '.join(pending_keys)}")
    else:
        lines.append("All planned T0/T1/T2 metrics are present.")

    lines.extend(["", "## Acceptance Snapshot", ""])
    for model_key, label in MODELS.items():
        lines.append(f"### {label}")
        for eval_key, metric in (
            ("coco", "accuracy"),
            ("gqa", "accuracy"),
            ("hard_coco", "accuracy"),
            ("bem", "accuracy"),
            ("cepo_supported", "support_accuracy"),
            ("cepo_wrong", "wrong_evidence_rejection"),
            ("cepo_wrong", "object_wrong_rejection"),
            ("cepo_wrong", "attribute_wrong_rejection"),
            ("cepo_wrong", "relation_wrong_rejection"),
            ("relation_stress", "overall_rejection"),
            ("relation_stress", "subject_object_swap_rejection"),
            ("relation_stress", "left_right_reversal_rejection"),
            ("relation_stress", "false_accept_rate"),
            ("cepo_wrong", "parse_failure_rate"),
        ):
            value_ = lookup(rows, model_key, eval_key, metric)
            lines.append(f"- {eval_key}.{metric}: {fmt(value_)}")
        lines.append("")

    answer_wrong = lookup(rows, "cepo_answer_dpo", "cepo_wrong", "wrong_evidence_rejection")
    dual_wrong = lookup(rows, "cepo_dual_dpo", "cepo_wrong", "wrong_evidence_rejection")
    if isinstance(answer_wrong, (int, float)) and isinstance(dual_wrong, (int, float)):
        delta = dual_wrong - answer_wrong
        lines.append(f"CEPO-Dual-2k wrong-evidence delta over Answer-DPO: {fmt(delta)}")
        lines.append("")
    return "\n".join(lines)


def lookup(rows: list[dict[str, Any]], model_key: str, eval_key: str, metric: str) -> float | int | None:
    for row in rows:
        if row["model_key"] == model_key and row["eval"] == eval_key and row["metric"] == metric:
            value_ = row["value"]
            if value_ == "":
                return None
            return value_
    return None


def fmt(value_: float | int | None) -> str:
    if value_ is None:
        return "pending"
    return f"{float(value_) * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
