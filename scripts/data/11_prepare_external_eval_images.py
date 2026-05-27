#!/usr/bin/env python3
"""Download and arrange images required by official POPE/AMBER evals."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

import requests

from common import ensure_parent, iter_jsonl, repo_path, write_json


COCO_VAL2014_URL = "http://images.cocodataset.org/zips/val2014.zip"
COCO_VAL2014_IMAGE_BASE_URL = "http://images.cocodataset.org/val2014"
AMBER_GOOGLE_DRIVE_ID = "1MaCHgtupcZUjf007anNl4_MV0o4DjXvl"
GOOGLE_DRIVE_URL = "https://docs.google.com/uc?export=download"
AMBER_HF_DATASET = "visual-preference/AMBER"
AMBER_HF_ENDPOINT = "https://hf-mirror.com"
AMBER_HF_SPLIT = "query_generative"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmarks", nargs="+", choices=("coco", "amber", "all"), default=["all"])
    parser.add_argument("--coco-url", default=COCO_VAL2014_URL)
    parser.add_argument("--coco-image-base-url", default=COCO_VAL2014_IMAGE_BASE_URL)
    parser.add_argument("--amber-gdrive-id", default=AMBER_GOOGLE_DRIVE_ID)
    parser.add_argument(
        "--amber-source",
        choices=("auto", "google-drive", "hf-parquet"),
        default="auto",
        help="Image source for AMBER when data/raw/amber/images is incomplete.",
    )
    parser.add_argument("--amber-hf-dataset", default=AMBER_HF_DATASET)
    parser.add_argument("--amber-hf-endpoint", default=AMBER_HF_ENDPOINT)
    parser.add_argument("--amber-hf-split", default=AMBER_HF_SPLIT)
    parser.add_argument("--coco-root", default="data/raw/coco")
    parser.add_argument("--amber-root", default="data/raw/amber")
    parser.add_argument("--manifest", default="data/raw/external_eval_images_manifest.json")
    parser.add_argument("--min-coco-images", type=int, default=500)
    parser.add_argument("--min-amber-images", type=int, default=1004)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--chunk-mb", type=int, default=8)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument(
        "--download-coco-zip",
        action="store_true",
        help="Download the full COCO val2014 zip instead of only POPE-referenced images.",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument(
        "--allow-missing-eval-images",
        action="store_true",
        help="Do not fail if normalized POPE/AMBER eval files still reference missing images.",
    )
    args = parser.parse_args()

    selected = {"coco", "amber"} if "all" in args.benchmarks else set(args.benchmarks)
    manifest: dict[str, Any] = {"selected": sorted(selected)}

    if "coco" in selected:
        manifest["coco"] = prepare_coco(args)
    if "amber" in selected:
        manifest["amber"] = prepare_amber(args)

    missing = check_eval_image_paths()
    manifest["eval_image_check"] = missing
    write_json(args.manifest, manifest)
    print(json.dumps(manifest, indent=2))

    if missing["missing_rows"] and not args.allow_missing_eval_images:
        print(
            f"Still missing {missing['missing_rows']} eval image references; "
            f"first missing image: {missing['examples'][0] if missing['examples'] else 'n/a'}",
            file=sys.stderr,
        )
        return 1
    return 0


def prepare_coco(args: argparse.Namespace) -> dict[str, Any]:
    coco_root = repo_path(args.coco_root)
    image_root = coco_root / "val2014"
    zip_path = coco_root / "val2014.zip"
    image_root.mkdir(parents=True, exist_ok=True)
    expected = collect_expected_image_paths(
        [
            repo_path("data/eval/pope_coco_random.jsonl"),
            repo_path("data/eval/pope_coco_popular.jsonl"),
            repo_path("data/eval/pope_coco_adversarial.jsonl"),
        ],
        image_root,
    )
    missing_expected = [path for path in expected if not path.exists()]
    if missing_expected and not args.skip_download:
        download_coco_images(missing_expected, args)
    current = count_files(image_root, "COCO_val2014_*.jpg")
    if current < args.min_coco_images and args.download_coco_zip:
        if not args.skip_download and not zip_path.exists():
            download_url(args.coco_url, zip_path, args)
        if not zip_path.exists():
            raise FileNotFoundError(f"Missing COCO val2014 archive: {zip_path}")
        extract_zip(zip_path, coco_root)
    current = count_files(image_root, "COCO_val2014_*.jpg")
    return {
        "image_root": str(image_root),
        "zip_path": str(zip_path),
        "expected_images": len(expected),
        "missing_expected_images": sum(1 for path in expected if not path.exists()),
        "image_count": current,
        "sample_exists": (image_root / "COCO_val2014_000000310196.jpg").exists(),
    }


def prepare_amber(args: argparse.Namespace) -> dict[str, Any]:
    amber_root = repo_path(args.amber_root)
    image_root = amber_root / "images"
    zip_path = amber_root / "amber_images.zip"
    parquet_path = amber_root / f"{args.amber_hf_split}-00000-of-00001.parquet"
    extract_root = amber_root / "extracted"
    image_root.mkdir(parents=True, exist_ok=True)
    current = count_files(image_root, "AMBER_*.jpg")
    if current < args.min_amber_images:
        prepare_amber_images(args, zip_path, parquet_path, extract_root, image_root)
    current = count_files(image_root, "AMBER_*.jpg")
    return {
        "image_root": str(image_root),
        "zip_path": str(zip_path),
        "hf_parquet_path": str(parquet_path),
        "image_count": current,
        "sample_exists": (image_root / "AMBER_1.jpg").exists(),
    }


def prepare_amber_images(
    args: argparse.Namespace,
    zip_path: Path,
    parquet_path: Path,
    extract_root: Path,
    image_root: Path,
) -> None:
    if zip_path.exists():
        extract_amber_zip(zip_path, extract_root, image_root)
        if count_files(image_root, "AMBER_*.jpg") >= args.min_amber_images:
            return
    if args.skip_download:
        raise FileNotFoundError(
            f"AMBER images are incomplete and downloads are disabled: {image_root}"
        )

    if args.amber_source in {"auto", "google-drive"}:
        try:
            if not zip_path.exists():
                download_google_drive(args.amber_gdrive_id, zip_path, args)
            extract_amber_zip(zip_path, extract_root, image_root)
        except Exception as exc:  # noqa: BLE001
            if args.amber_source == "google-drive":
                raise
            print(f"Google Drive AMBER download failed, falling back to HF parquet: {exc!r}")
        if count_files(image_root, "AMBER_*.jpg") >= args.min_amber_images:
            return

    if args.amber_source in {"auto", "hf-parquet"}:
        if not parquet_path.exists():
            download_url(amber_hf_parquet_url(args), parquet_path, args)
        extract_amber_hf_parquet(parquet_path, image_root)
        if count_files(image_root, "AMBER_*.jpg") >= args.min_amber_images:
            return

    raise RuntimeError(f"AMBER images remain incomplete under {image_root}")


def extract_amber_zip(zip_path: Path, extract_root: Path, image_root: Path) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"AMBER archive is not a valid zip file: {zip_path}")
    extract_root.mkdir(parents=True, exist_ok=True)
    extract_zip(zip_path, extract_root)
    link_amber_images(extract_root, image_root)


def amber_hf_parquet_url(args: argparse.Namespace) -> str:
    endpoint = args.amber_hf_endpoint.rstrip("/")
    dataset = args.amber_hf_dataset.strip("/")
    split = args.amber_hf_split
    return f"{endpoint}/datasets/{dataset}/resolve/main/data/{split}-00000-of-00001.parquet"


def download_url(url: str, destination: Path, args: argparse.Namespace) -> None:
    ensure_parent(destination)
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    print(f"Downloading {url} -> {destination}")
    if tmp_path.exists():
        tmp_path.unlink()
    subprocess.run(
        [
            "curl",
            "-L",
            "--fail",
            "--retry",
            "8",
            "--retry-delay",
            "10",
            "--connect-timeout",
            str(args.timeout),
            "-o",
            str(tmp_path),
            url,
        ],
        check=True,
    )
    tmp_path.replace(destination)


def download_coco_images(paths: list[Path], args: argparse.Namespace) -> None:
    print(f"Downloading {len(paths)} POPE-referenced COCO val2014 images")
    failures: list[dict[str, str]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(download_coco_one, path, args): path for path in paths}
        for future in as_completed(futures):
            path = futures[future]
            completed += 1
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001
                failures.append({"image": str(path), "error": repr(exc)})
            if completed % 50 == 0 or completed == len(paths):
                print(f"  COCO image progress {completed}/{len(paths)}; failures={len(failures)}")
    if failures:
        raise RuntimeError(f"Failed to download {len(failures)} COCO images; first failure: {failures[0]}")


def download_coco_one(path: Path, args: argparse.Namespace) -> None:
    ensure_parent(path)
    if path.exists() and path.stat().st_size > 0:
        return
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    url = f"{args.coco_image_base_url.rstrip('/')}/{path.name}"
    subprocess.run(
        [
            "curl",
            "-L",
            "--fail",
            "--silent",
            "--show-error",
            "--retry",
            "4",
            "--retry-delay",
            "2",
            "--connect-timeout",
            str(args.timeout),
            "-o",
            str(tmp_path),
            url,
        ],
        check=True,
    )
    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        raise RuntimeError(f"empty COCO image download: {url}")
    tmp_path.replace(path)


def download_google_drive(file_id: str, destination: Path, args: argparse.Namespace) -> None:
    ensure_parent(destination)
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    session = requests.Session()
    print(f"Downloading Google Drive file {file_id} -> {destination}")
    response = session.get(GOOGLE_DRIVE_URL, params={"id": file_id}, stream=True, timeout=args.timeout)
    token = google_drive_confirm_token(response)
    if token:
        response.close()
        response = session.get(
            GOOGLE_DRIVE_URL,
            params={"id": file_id, "confirm": token},
            stream=True,
            timeout=args.timeout,
        )
    response.raise_for_status()
    save_response(response, tmp_path, destination, args.chunk_mb)


def google_drive_confirm_token(response: requests.Response) -> str | None:
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value
    return None


def save_response(response: requests.Response, tmp_path: Path, destination: Path, chunk_mb: int) -> None:
    chunk_size = max(1, chunk_mb) * 1024 * 1024
    total = int(response.headers.get("content-length") or 0)
    written = 0
    next_report = 0
    with tmp_path.open("wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if not chunk:
                continue
            f.write(chunk)
            written += len(chunk)
            if written >= next_report:
                if total:
                    print(f"  downloaded {written / 1e9:.2f} / {total / 1e9:.2f} GB")
                else:
                    print(f"  downloaded {written / 1e9:.2f} GB")
                next_report = written + 512 * 1024 * 1024
    tmp_path.replace(destination)


def extract_zip(zip_path: Path, destination: Path) -> None:
    print(f"Extracting {zip_path} -> {destination}")
    subprocess.run(["unzip", "-q", "-n", str(zip_path), "-d", str(destination)], check=True)


def link_amber_images(extract_root: Path, image_root: Path) -> None:
    candidates = sorted(extract_root.rglob("AMBER_*.jpg"))
    if not candidates:
        candidates = sorted(extract_root.rglob("AMBER_*.jpeg"))
    if not candidates:
        raise FileNotFoundError(f"No AMBER_*.jpg files found under {extract_root}")
    image_root.mkdir(parents=True, exist_ok=True)
    linked = 0
    for source in candidates:
        target = image_root / source.name
        if target.exists():
            continue
        target.symlink_to(source.resolve())
        linked += 1
    print(f"Linked {linked} AMBER images into {image_root}")


def extract_amber_hf_parquet(parquet_path: Path, image_root: Path) -> None:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required to extract AMBER images from HF parquet") from exc

    image_root.mkdir(parents=True, exist_ok=True)
    parquet_file = pq.ParquetFile(parquet_path)
    written = 0
    seen = 0
    for batch in parquet_file.iter_batches(batch_size=64, columns=["id", "image"]):
        ids = batch.column("id").to_pylist()
        images = batch.column("image").to_pylist()
        for image_id, image_value in zip(ids, images, strict=True):
            seen += 1
            target = image_root / f"AMBER_{int(image_id)}.jpg"
            if target.exists() and target.stat().st_size > 0:
                continue
            image_bytes = amber_image_bytes(image_value)
            ensure_parent(target)
            tmp_path = target.with_suffix(target.suffix + ".tmp")
            with tmp_path.open("wb") as f:
                f.write(image_bytes)
            tmp_path.replace(target)
            written += 1
        if seen % 256 == 0 or seen == parquet_file.metadata.num_rows:
            print(f"  AMBER parquet extraction {seen}/{parquet_file.metadata.num_rows}; written={written}")
    print(f"Extracted {written} AMBER images from {parquet_path}")


def amber_image_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict):
        data = value.get("bytes")
        if isinstance(data, bytes):
            return data
        path = value.get("path")
        if path:
            candidate = Path(path)
            if candidate.exists():
                return candidate.read_bytes()
    raise ValueError(f"Unsupported AMBER parquet image value: {type(value).__name__}")


def check_eval_image_paths() -> dict[str, Any]:
    eval_files = [
        repo_path("data/eval/pope_coco_random.jsonl"),
        repo_path("data/eval/pope_coco_popular.jsonl"),
        repo_path("data/eval/pope_coco_adversarial.jsonl"),
        repo_path("data/eval/amber_discriminative.jsonl"),
    ]
    missing_rows = 0
    total_rows = 0
    missing_unique: set[str] = set()
    examples: list[str] = []
    for eval_file in eval_files:
        if not eval_file.exists():
            continue
        for row in iter_jsonl(eval_file):
            total_rows += 1
            image = row.get("image")
            if not image:
                continue
            path = repo_path(image)
            if not path.exists():
                missing_rows += 1
                missing_unique.add(str(path))
                if len(examples) < 10:
                    examples.append(str(path))
    return {
        "total_rows": total_rows,
        "missing_rows": missing_rows,
        "missing_unique_images": len(missing_unique),
        "examples": examples,
    }


def collect_expected_image_paths(eval_files: Iterable[Path], image_root: Path) -> list[Path]:
    paths: dict[str, Path] = {}
    for eval_file in eval_files:
        if not eval_file.exists():
            continue
        for row in iter_jsonl(eval_file):
            image = row.get("image")
            if not image:
                continue
            path = repo_path(image)
            if path.parent == image_root:
                paths[path.name] = path
    return sorted(paths.values())


def count_files(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob(pattern))


if __name__ == "__main__":
    start = time.time()
    try:
        raise SystemExit(main())
    finally:
        print(f"elapsed_seconds={time.time() - start:.1f}")
