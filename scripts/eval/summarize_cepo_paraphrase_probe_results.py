#!/usr/bin/env python3
"""Summarize CEPO paraphrased-probe metrics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from common import load_json, repo_path


MODELS = ("base", "cepo_answer_dpo", "cepo_dual_dpo")
DEFAULT_OUTPUT = (
    "v2/tasks/review-convergence-experiments/results/paraphrase_probe/metrics.csv"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="cepo_paraphrase_probe")
    parser.add_argument("--supported-eval", default="cepo_evidence_probe_paraphrase")
    parser.add_argument("--wrong-eval", default="cepo_wrong_evidence_probe_paraphrase")
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rows = [summarize_model(model, args) for model in MODELS]
    output = repo_path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote paraphrased-probe metrics to {output}")
    for row in rows:
        print(
            "{model_key}: supported={supported_acc:.1%} wrong={wrong_rejection:.1%} "
            "obj/attr/rel={object_wrong:.1%}/{attribute_wrong:.1%}/{relation_wrong:.1%}".format(**row)
        )
    return 0


def summarize_model(model_key: str, args: argparse.Namespace) -> dict[str, Any]:
    supported = load_json(metrics_path(args.supported_eval, args.variant, model_key))
    wrong = load_json(metrics_path(args.wrong_eval, args.variant, model_key))
    wrong_slices = wrong_slice_metrics(wrong)
    total = supported["total"] + wrong["total"]
    parse_fail = weighted_rate(
        [
            (supported.get("parse_failure_rate"), supported.get("total")),
            (wrong.get("parse_failure_rate"), wrong.get("total")),
        ]
    )
    json_obj = weighted_rate(
        [
            (1 - supported.get("invalid_json_rate", 0.0), supported.get("total")),
            (1 - wrong.get("invalid_json_rate", 0.0), wrong.get("total")),
        ]
    )
    return {
        "model_key": model_key,
        "supported_acc": supported["support_accuracy"],
        "wrong_rejection": wrong["wrong_evidence_rejection_accuracy"],
        "object_wrong": wrong_slices["object"],
        "attribute_wrong": wrong_slices["attribute"],
        "relation_wrong": wrong_slices["relation"],
        "json_obj": json_obj,
        "scored_output": 1.0 - parse_fail,
        "parse_fail": parse_fail,
        "notes": f"{total} paraphrased CEPO-Probe rows; same labels as locked probe",
    }


def metrics_path(eval_name: str, variant: str, model_key: str) -> Path:
    return repo_path("results/eval/generations") / eval_name / variant / f"{model_key}.metrics.json"


def wrong_slice_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    groups = metrics.get("by_base_task_type") or {}
    return {
        "object": nested(groups, "object_existence", "wrong_evidence_rejection_accuracy"),
        "attribute": weighted_rate(
            [
                (
                    nested(groups, "attribute_color", "wrong_evidence_rejection_accuracy"),
                    nested(groups, "attribute_color", "total"),
                ),
                (
                    nested(groups, "attribute_material", "wrong_evidence_rejection_accuracy"),
                    nested(groups, "attribute_material", "total"),
                ),
            ]
        ),
        "relation": nested(groups, "relation_spatial", "wrong_evidence_rejection_accuracy"),
    }


def nested(payload: dict[str, Any], group: str, key: str) -> float:
    value = (payload.get(group) or {}).get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def weighted_rate(items: list[tuple[float | int | None, float | int | None]]) -> float:
    total = 0.0
    positives = 0.0
    for rate, count in items:
        if rate is None or count is None:
            continue
        total += float(count)
        positives += float(rate) * float(count)
    return round(positives / total, 6) if total else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
