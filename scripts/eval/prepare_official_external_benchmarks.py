#!/usr/bin/env python3
"""Fetch official POPE/AMBER metadata and build external eval JSONL files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import repo_path, write_json


SCRIPT_DIR = Path(__file__).resolve().parent
POPE_REPO = "https://github.com/RUCAIBox/POPE.git"
AMBER_REPO = "https://github.com/junyangwang0410/AMBER.git"
POPE_STRATEGIES = ("random", "popular", "adversarial")
AMBER_DIMENSIONS = ("existence", "attribute", "relation")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pope-raw-root", default="data/raw/external/pope")
    parser.add_argument("--amber-raw-root", default="data/raw/external/amber")
    parser.add_argument("--pope-image-root", default="data/raw/coco/val2014")
    parser.add_argument("--amber-image-root", default="data/raw/amber/images")
    parser.add_argument("--output-dir", default="data/eval")
    parser.add_argument("--manifest", default="data/eval/external_benchmarks.summary.json")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-pope", action="store_true")
    parser.add_argument("--skip-amber", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Run git pull in existing sparse checkouts.")
    parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail if any normalized eval row still points to a missing image.",
    )
    parser.add_argument(
        "--amber-max-records-per-dimension",
        type=int,
        default=None,
        help="Optional AMBER smoke/debug cap. Leave unset for the full official discriminative set.",
    )
    args = parser.parse_args()

    if not args.skip_download:
        if not args.skip_pope:
            ensure_sparse_checkout(
                POPE_REPO,
                repo_path(args.pope_raw_root),
                ["README.md", "output/coco"],
                [
                    "output/coco/coco_pope_random.json",
                    "output/coco/coco_pope_popular.json",
                    "output/coco/coco_pope_adversarial.json",
                ],
                args.refresh,
            )
        if not args.skip_amber:
            ensure_sparse_checkout(
                AMBER_REPO,
                repo_path(args.amber_raw_root),
                ["README.md", "data/annotations.json", "data/query"],
                [
                    "data/annotations.json",
                    "data/query/query_discriminative-existence.json",
                    "data/query/query_discriminative-attribute.json",
                    "data/query/query_discriminative-relation.json",
                ],
                args.refresh,
            )

    outputs: list[dict[str, Any]] = []
    output_dir = repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_pope:
        outputs.extend(prepare_pope(args, output_dir))
    if not args.skip_amber:
        outputs.append(prepare_amber(args, output_dir))

    write_json(
        args.manifest,
        {
            "pope_repo": POPE_REPO,
            "amber_repo": AMBER_REPO,
            "pope_raw_root": str(repo_path(args.pope_raw_root)),
            "amber_raw_root": str(repo_path(args.amber_raw_root)),
            "pope_image_root": str(repo_path(args.pope_image_root)),
            "amber_image_root": str(repo_path(args.amber_image_root)),
            "outputs": outputs,
            "notes": [
                "POPE uses COCO val2014 images; this script only prepares official POPE annotations.",
                "AMBER images are distributed separately by the AMBER authors; this script only prepares official query/annotation files.",
            ],
        },
    )
    print(f"Wrote external benchmark manifest to {repo_path(args.manifest)}")
    return 0


def ensure_sparse_checkout(
    repo_url: str,
    destination: Path,
    sparse_paths: list[str],
    expected_files: list[str],
    refresh: bool,
) -> None:
    if all((destination / path).exists() for path in expected_files) and not refresh:
        print(f"Using existing official data at {destination}")
        return
    if destination.exists() and any(destination.iterdir()) and not (destination / ".git").exists():
        raise RuntimeError(
            f"{destination} exists but is not a git checkout. Move it aside or pass --skip-download."
        )
    if not (destination / ".git").exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", repo_url, str(destination)])
    run(["git", "-C", str(destination), "sparse-checkout", "set", *sparse_paths])
    if refresh:
        run(["git", "-C", str(destination), "pull", "--ff-only"])
    missing = [path for path in expected_files if not (destination / path).exists()]
    if missing:
        raise FileNotFoundError(f"{destination} is missing expected official files: {missing}")


def prepare_pope(args: argparse.Namespace, output_dir: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for strategy in POPE_STRATEGIES:
        input_path = repo_path(args.pope_raw_root) / "output" / "coco" / f"coco_pope_{strategy}.json"
        output_path = output_dir / f"pope_coco_{strategy}.jsonl"
        summary_path = output_dir / f"pope_coco_{strategy}.summary.json"
        command = [
            sys.executable,
            str(SCRIPT_DIR / "prepare_pope_eval.py"),
            "--input",
            str(input_path),
            "--image-root",
            args.pope_image_root,
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--source-name",
            f"pope_coco_{strategy}",
            "--sampling-strategy",
            strategy,
        ]
        if args.require_images:
            command.append("--require-images")
        run(command)
        outputs.append(
            {
                "benchmark": "pope",
                "strategy": strategy,
                "input": str(input_path),
                "eval": str(output_path),
                "summary": str(summary_path),
            }
        )
    return outputs


def prepare_amber(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    output_path = output_dir / "amber_discriminative.jsonl"
    summary_path = output_dir / "amber_discriminative.summary.json"
    command = [
        sys.executable,
        str(SCRIPT_DIR / "prepare_amber_eval.py"),
        "--annotation",
        str(repo_path(args.amber_raw_root) / "data" / "annotations.json"),
        "--query-root",
        str(repo_path(args.amber_raw_root) / "data" / "query"),
        "--dimensions",
        *AMBER_DIMENSIONS,
        "--image-root",
        args.amber_image_root,
        "--output",
        str(output_path),
        "--summary",
        str(summary_path),
    ]
    if args.amber_max_records_per_dimension is not None:
        command.extend(["--max-records-per-dimension", str(args.amber_max_records_per_dimension)])
    if args.require_images:
        command.append("--require-images")
    run(command)
    return {
        "benchmark": "amber",
        "dimensions": list(AMBER_DIMENSIONS),
        "eval": str(output_path),
        "summary": str(summary_path),
    }


def run(command: list[str]) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
