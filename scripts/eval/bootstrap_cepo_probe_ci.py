#!/usr/bin/env python3
"""Bootstrap confidence intervals for CEPO-Probe generation outputs."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from common import load_jsonl, repo_path, write_json, write_jsonl
from score_cepo_evidence_probe import score_row


DEFAULT_MODELS = OrderedDict(
    [
        ("base", "Base Instruct"),
        ("cepo_answer_dpo", "CEPO Answer-DPO"),
        ("cepo_dual_dpo", "CEPO-Dual-2k"),
    ]
)
SLICE_GROUPS: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("Object", ("object_existence",)),
        ("Attribute", ("attribute_color", "attribute_material")),
        ("Relation", ("relation_spatial",)),
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--supported-dir",
        default="results/eval/generations/cepo_evidence_probe/cepo_dual_evidence_probe",
        help="Directory containing supported-probe generation JSONL files.",
    )
    parser.add_argument(
        "--wrong-dir",
        default="results/eval/generations/cepo_wrong_evidence_probe/cepo_dual_evidence_probe",
        help="Directory containing wrong-evidence-probe generation JSONL files.",
    )
    parser.add_argument(
        "--metrics-dir",
        default="results/eval/metrics/cepo_probe_ci",
        help="Directory for per-model JSON and scored JSONL artifacts.",
    )
    parser.add_argument(
        "--artifact-dir",
        default="cepo-probe-benchmark-improve/artifacts",
        help="Directory for paper-facing Markdown tables.",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--models",
        nargs="*",
        default=list(DEFAULT_MODELS),
        help="Model keys to read from both generation directories.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    metrics_dir = repo_path(args.metrics_dir)
    artifact_dir = repo_path(args.artifact_dir)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    summaries: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for model_key in args.models:
        label = DEFAULT_MODELS.get(model_key, model_key)
        supported_path = repo_path(args.supported_dir) / f"{model_key}.jsonl"
        wrong_path = repo_path(args.wrong_dir) / f"{model_key}.jsonl"
        if not supported_path.exists():
            print(f"Missing supported generation file: {supported_path}", file=sys.stderr)
            return 2
        if not wrong_path.exists():
            print(f"Missing wrong-evidence generation file: {wrong_path}", file=sys.stderr)
            return 2

        supported_rows = [score_row(row) for row in load_jsonl(supported_path)]
        wrong_rows = [score_row(row) for row in load_jsonl(wrong_path)]
        summary = summarize_model(
            model_key=model_key,
            label=label,
            supported_path=supported_path,
            wrong_path=wrong_path,
            supported_rows=supported_rows,
            wrong_rows=wrong_rows,
            rng=rng,
            bootstrap_samples=args.bootstrap_samples,
        )
        summaries[model_key] = summary

        write_json(metrics_dir / f"{model_key}.json", summary)
        write_jsonl(metrics_dir / f"{model_key}_supported_scored.jsonl", supported_rows)
        write_jsonl(metrics_dir / f"{model_key}_wrong_scored.jsonl", wrong_rows)

    write_json(metrics_dir / "all_models.json", summaries)
    (artifact_dir / "table3_ci.md").write_text(table3_markdown(summaries), encoding="utf-8")
    (artifact_dir / "slice_ci.md").write_text(slice_markdown(summaries), encoding="utf-8")
    (artifact_dir / "parser_audit.md").write_text(parser_markdown(summaries), encoding="utf-8")
    (metrics_dir / "table3_ci.md").write_text(table3_markdown(summaries), encoding="utf-8")
    (metrics_dir / "slice_breakdown_ci.md").write_text(slice_markdown(summaries), encoding="utf-8")

    print(f"Wrote CEPO-Probe CI artifacts to {metrics_dir}")
    print(f"Wrote paper-facing Markdown tables to {artifact_dir}")
    return 0


def summarize_model(
    *,
    model_key: str,
    label: str,
    supported_path: Path,
    wrong_path: Path,
    supported_rows: list[dict[str, Any]],
    wrong_rows: list[dict[str, Any]],
    rng: random.Random,
    bootstrap_samples: int,
) -> dict[str, Any]:
    supported_metric = bootstrap_rate(
        supported_rows,
        lambda row: bool(row.get("support_correct")),
        rng,
        bootstrap_samples,
    )
    wrong_metric = bootstrap_rate(
        wrong_rows,
        lambda row: bool(row.get("wrong_evidence_rejected")),
        rng,
        bootstrap_samples,
    )
    parser_rows = supported_rows + wrong_rows
    parser_metrics = {
        "total": len(parser_rows),
        "strict_json_valid": bootstrap_rate(
            parser_rows,
            lambda row: bool(row.get("json_valid")),
            rng,
            bootstrap_samples,
        ),
        "scored_output_rate": bootstrap_rate(
            parser_rows,
            lambda row: not bool(row.get("parse_failed")),
            rng,
            bootstrap_samples,
        ),
        "parse_failure_rate": bootstrap_rate(
            parser_rows,
            lambda row: bool(row.get("parse_failed")),
            rng,
            bootstrap_samples,
        ),
    }
    slice_metrics = OrderedDict()
    for slice_name, task_types in SLICE_GROUPS.items():
        rows = [row for row in wrong_rows if row.get("base_task_type") in task_types]
        slice_metrics[slice_name] = bootstrap_rate(
            rows,
            lambda row: bool(row.get("wrong_evidence_rejected")),
            rng,
            bootstrap_samples,
        )

    detailed_wrong_slices = OrderedDict()
    for task_type in sorted({str(row.get("base_task_type")) for row in wrong_rows}):
        rows = [row for row in wrong_rows if row.get("base_task_type") == task_type]
        detailed_wrong_slices[task_type] = bootstrap_rate(
            rows,
            lambda row: bool(row.get("wrong_evidence_rejected")),
            rng,
            bootstrap_samples,
        )

    return {
        "model_key": model_key,
        "label": label,
        "supported_generation_file": str(supported_path),
        "wrong_generation_file": str(wrong_path),
        "bootstrap_samples": bootstrap_samples,
        "supported_support_accuracy": supported_metric,
        "wrong_evidence_rejection_accuracy": wrong_metric,
        "parser": parser_metrics,
        "wrong_evidence_by_slice": slice_metrics,
        "wrong_evidence_by_base_task_type": detailed_wrong_slices,
    }


def bootstrap_rate(
    rows: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    rng: random.Random,
    bootstrap_samples: int,
) -> dict[str, Any]:
    values = [1.0 if predicate(row) else 0.0 for row in rows]
    n = len(values)
    if not values:
        return {
            "n": 0,
            "mean": 0.0,
            "se": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "positives": 0,
        }

    observed = sum(values) / n
    samples = []
    for _ in range(bootstrap_samples):
        samples.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    samples.sort()
    boot_mean = sum(samples) / len(samples)
    se = math.sqrt(sum((value - boot_mean) ** 2 for value in samples) / max(1, len(samples) - 1))
    return {
        "n": n,
        "mean": round(observed, 6),
        "se": round(se, 6),
        "ci95_low": round(percentile(samples, 0.025), 6),
        "ci95_high": round(percentile(samples, 0.975), 6),
        "positives": int(sum(values)),
    }


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = q * (len(sorted_values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def table3_markdown(summaries: OrderedDict[str, dict[str, Any]]) -> str:
    lines = [
        "# Table 3 CEPO-Probe CI",
        "",
        "| Model | Supported N | Supported Acc. | Wrong N | Wrong-Evidence Rej. | Strict JSON | Scored Output | Parse Fail |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries.values():
        supported = summary["supported_support_accuracy"]
        wrong = summary["wrong_evidence_rejection_accuracy"]
        parser = summary["parser"]
        lines.append(
            "| {label} | {supp_n} | {supp} | {wrong_n} | {wrong} | {strict} | {scored} | {parse} |".format(
                label=summary["label"],
                supp_n=supported["n"],
                supp=fmt_ci(supported),
                wrong_n=wrong["n"],
                wrong=fmt_ci(wrong),
                strict=fmt_pct(parser["strict_json_valid"]["mean"]),
                scored=fmt_pct(parser["scored_output_rate"]["mean"]),
                parse=fmt_pct(parser["parse_failure_rate"]["mean"]),
            )
        )
    lines.extend(
        [
            "",
            "Values are row-bootstrap estimates with 10,000 resamples by default; intervals are percentile 95% CIs.",
            "Strict JSON measures parseable JSON objects in raw generations; scored output also counts fallback parsing.",
            "",
        ]
    )
    return "\n".join(lines)


def slice_markdown(summaries: OrderedDict[str, dict[str, Any]]) -> str:
    lines = [
        "# Wrong-Evidence Slice CI",
        "",
        "| Slice | N | Base wrong-rej. | Answer-DPO wrong-rej. | CEPO-Dual-2k wrong-rej. |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    keys = list(summaries)
    for slice_name in SLICE_GROUPS:
        first_metric = summaries[keys[0]]["wrong_evidence_by_slice"][slice_name]
        row = [f"| {slice_name}", str(first_metric["n"])]
        for key in keys:
            row.append(fmt_ci(summaries[key]["wrong_evidence_by_slice"][slice_name]))
        lines.append(" | ".join(row) + " |")
    lines.extend(
        [
            "",
            "Attribute combines color and material wrong-evidence rows.",
            "",
        ]
    )
    return "\n".join(lines)


def parser_markdown(summaries: OrderedDict[str, dict[str, Any]]) -> str:
    lines = [
        "# Parser Audit",
        "",
        "| Model | Rows | Strict JSON Valid | Scored Output | Parse Failure |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries.values():
        parser = summary["parser"]
        lines.append(
            "| {label} | {n} | {strict} | {scored} | {parse} |".format(
                label=summary["label"],
                n=parser["total"],
                strict=fmt_ci(parser["strict_json_valid"]),
                scored=fmt_ci(parser["scored_output_rate"]),
                parse=fmt_ci(parser["parse_failure_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "Scored output means that JSON parsing or fallback field/support inference recovered enough structure for scoring.",
            "",
        ]
    )
    return "\n".join(lines)


def fmt_ci(metric: dict[str, Any]) -> str:
    return f"{fmt_pct(metric['mean'])} [{fmt_pct(metric['ci95_low'])}, {fmt_pct(metric['ci95_high'])}]"


def fmt_pct(value: float) -> str:
    return f"{100 * float(value) + 1e-9:.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
