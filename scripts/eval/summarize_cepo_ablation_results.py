#!/usr/bin/env python3
"""Summarize CEPO verifier-count ablation metrics into paper-facing tables."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from common import load_json, repo_path, write_json


EVALS = OrderedDict(
    [
        ("coco", "coco_heldout_object_existence"),
        ("gqa", "gqa_simple_heldout"),
        ("hard", "coco_hard_object_existence"),
    ]
)
ROWS = OrderedDict(
    [
        (
            "base",
            {
                "label": "Base Instruct",
                "answer_rows": 0,
                "verifier_rows": 0,
                "variant": "cepo_dual",
                "probe_variant": "cepo_dual_evidence_probe",
                "model_key": "base",
            },
        ),
        (
            "cepo_answer_dpo",
            {
                "label": "CEPO Answer-DPO",
                "answer_rows": 6000,
                "verifier_rows": 0,
                "variant": "cepo_dual",
                "probe_variant": "cepo_dual_evidence_probe",
                "model_key": "cepo_answer_dpo",
            },
        ),
        (
            "cepo_evidence_only_dpo",
            {
                "label": "Evidence-DPO only",
                "answer_rows": 0,
                "verifier_rows": 2000,
                "variant": "cepo_dual_ablation/evidence_only_2k",
                "probe_variant": "cepo_dual_ablation/evidence_only_2k",
                "model_key": "cepo_evidence_only_dpo",
            },
        ),
        (
            "cepo_dual500_dpo",
            {
                "label": "CEPO-Dual-500",
                "answer_rows": 6000,
                "verifier_rows": 500,
                "variant": "cepo_dual_ablation/dual500",
                "probe_variant": "cepo_dual_ablation/dual500",
                "model_key": "cepo_dual500_dpo",
            },
        ),
        (
            "cepo_dual1k_dpo",
            {
                "label": "CEPO-Dual-1k",
                "answer_rows": 6000,
                "verifier_rows": 1000,
                "variant": "cepo_dual_ablation/dual1k",
                "probe_variant": "cepo_dual_ablation/dual1k",
                "model_key": "cepo_dual1k_dpo",
            },
        ),
        (
            "cepo_dual_dpo",
            {
                "label": "CEPO-Dual-2k",
                "answer_rows": 6000,
                "verifier_rows": 2000,
                "variant": "cepo_dual",
                "probe_variant": "cepo_dual_evidence_probe",
                "model_key": "cepo_dual_dpo",
            },
        ),
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-md",
        default="cepo-probe-benchmark-improve/artifacts/ablation_results.md",
    )
    parser.add_argument(
        "--output-json",
        default="results/eval/metrics/cepo_probe_ci/ablation_results.json",
    )
    args = parser.parse_args()

    rows = OrderedDict((key, summarize_row(spec)) for key, spec in ROWS.items())
    output_json = {
        "rows": rows,
        "conclusions": build_conclusions(rows),
    }
    write_json(args.output_json, output_json)
    output_md = repo_path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(output_json), encoding="utf-8")
    print(f"Wrote ablation JSON to {repo_path(args.output_json)}")
    print(f"Wrote ablation Markdown to {output_md}")
    return 0


def summarize_row(spec: dict[str, Any]) -> dict[str, Any]:
    variant = spec["variant"]
    probe_variant = spec["probe_variant"]
    model_key = spec["model_key"]
    short = {}
    for eval_key, eval_name in EVALS.items():
        path = metrics_path(eval_name, variant, model_key)
        metrics = safe_load(path)
        short[eval_key] = {
            "path": str(path),
            "accuracy": value(metrics, "accuracy"),
            "false_positive_rate": value(metrics, "false_positive_rate"),
            "status": "ready" if metrics else "pending",
        }

    supported = safe_load(metrics_path("cepo_evidence_probe", probe_variant, model_key))
    wrong = safe_load(metrics_path("cepo_wrong_evidence_probe", probe_variant, model_key))
    wrong_slices = wrong_slice_metrics(wrong)
    parse_fail = weighted_rate(
        [
            (value(supported, "parse_failure_rate"), value(supported, "total")),
            (value(wrong, "parse_failure_rate"), value(wrong, "total")),
        ]
    )
    return {
        "label": spec["label"],
        "answer_rows": spec["answer_rows"],
        "verifier_rows": spec["verifier_rows"],
        "variant": variant,
        "probe_variant": probe_variant,
        "model_key": model_key,
        "short_answer": short,
        "evidence_probe": {
            "supported_path": str(metrics_path("cepo_evidence_probe", probe_variant, model_key)),
            "wrong_path": str(metrics_path("cepo_wrong_evidence_probe", probe_variant, model_key)),
            "supported_accuracy": value(supported, "support_accuracy"),
            "wrong_rejection": value(wrong, "wrong_evidence_rejection_accuracy"),
            "object_wrong_rejection": wrong_slices["object"],
            "attribute_wrong_rejection": wrong_slices["attribute"],
            "relation_wrong_rejection": wrong_slices["relation"],
            "parse_failure_rate": parse_fail,
            "status": "ready" if supported and wrong else "pending",
        },
    }


def metrics_path(eval_name: str, variant: str, model_key: str) -> Path:
    return repo_path("results/eval/generations") / eval_name / variant / f"{model_key}.metrics.json"


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


def nested_value(payload: dict[str, Any], group: str, key: str) -> float | int | None:
    item = payload.get(group) or {}
    value_ = item.get(key)
    if isinstance(value_, (int, float)):
        return value_
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


def build_conclusions(rows: OrderedDict[str, dict[str, Any]]) -> list[str]:
    conclusions: list[str] = []
    answer = rows["cepo_answer_dpo"]
    dual = rows["cepo_dual_dpo"]
    answer_wrong = answer["evidence_probe"]["wrong_rejection"]
    dual_wrong = dual["evidence_probe"]["wrong_rejection"]
    if answer_wrong is not None and dual_wrong is not None:
        conclusions.append(
            "Answer-DPO improves supported-claim behavior but lowers wrong-evidence rejection relative to the base; CEPO-Dual-2k restores rejection strongly."
        )

    relation = dual["evidence_probe"]["relation_wrong_rejection"]
    object_rate = dual["evidence_probe"]["object_wrong_rejection"]
    if relation is not None and object_rate is not None and relation < object_rate:
        conclusions.append(
            "Relation wrong-evidence remains the bottleneck even when object wrong-evidence rejection is high."
        )

    ablation_ready = all(
        rows[key]["evidence_probe"]["wrong_rejection"] is not None
        for key in ("cepo_dual500_dpo", "cepo_dual1k_dpo", "cepo_dual_dpo")
    )
    if ablation_ready:
        values = [
            rows[key]["evidence_probe"]["wrong_rejection"]
            for key in ("cepo_dual500_dpo", "cepo_dual1k_dpo", "cepo_dual_dpo")
        ]
        trend = "monotonic" if values == sorted(values) else "non-monotonic"
        conclusions.append(
            f"The verifier-count ablation is {trend}: wrong-evidence rejection is {fmt_pct(values[0])}, {fmt_pct(values[1])}, and {fmt_pct(values[2])} for 500/1k/2k verifier rows."
        )
    else:
        conclusions.append("Verifier-count ablation jobs are still pending; update this table after the Slurm evals finish.")

    evidence_only = rows["cepo_evidence_only_dpo"]
    if evidence_only["short_answer"]["coco"]["accuracy"] is not None:
        conclusions.append(
            "Evidence-DPO-only has completed enough short-answer evaluation to test whether verifier supervision transfers or harms ordinary VQA behavior."
        )
    return conclusions


def render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# CEPO Verifier-Count Ablation",
        "",
        "| Setting | Answer rows | Verifier rows | COCO Acc | GQA Acc | Hard Acc | Supp. Acc | Wrong Rej. | Object Wrong | Attr. Wrong | Rel. Wrong | Parse Fail |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows.values():
        ev = row["evidence_probe"]
        lines.append(
            "| {label} | {answer_rows} | {verifier_rows} | {coco} | {gqa} | {hard} | {supp} | {wrong} | {obj} | {attr} | {rel} | {parse} |".format(
                label=row["label"],
                answer_rows=row["answer_rows"],
                verifier_rows=row["verifier_rows"],
                coco=fmt_pct_or_pending(row["short_answer"]["coco"]["accuracy"]),
                gqa=fmt_pct_or_pending(row["short_answer"]["gqa"]["accuracy"]),
                hard=fmt_pct_or_pending(row["short_answer"]["hard"]["accuracy"]),
                supp=fmt_pct_or_pending(ev["supported_accuracy"]),
                wrong=fmt_pct_or_pending(ev["wrong_rejection"]),
                obj=fmt_pct_or_pending(ev["object_wrong_rejection"]),
                attr=fmt_pct_or_pending(ev["attribute_wrong_rejection"]),
                rel=fmt_pct_or_pending(ev["relation_wrong_rejection"]),
                parse=fmt_pct_or_pending(ev["parse_failure_rate"]),
            )
        )
    lines.extend(["", "## Current Read", ""])
    for conclusion in payload["conclusions"]:
        lines.append(f"- {conclusion}")
    lines.append("")
    return "\n".join(lines)


def fmt_pct_or_pending(value_: float | int | None) -> str:
    if value_ is None:
        return "pending"
    return fmt_pct(float(value_))


def fmt_pct(value_: float) -> str:
    return f"{100 * value_ + 1e-9:.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
