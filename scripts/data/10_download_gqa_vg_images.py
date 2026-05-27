#!/usr/bin/env python3
"""Download Visual Genome images referenced by GQA canonical records."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from common import ensure_parent, iter_jsonl, repo_path, write_json


DEFAULT_BASE_URLS = [
    "https://cs.stanford.edu/people/rak248/VG_100K",
    "https://cs.stanford.edu/people/rak248/VG_100K_2",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/processed/canonical_gqa_candidates.jsonl")
    parser.add_argument("--image-root", default="data/raw/gqa/images")
    parser.add_argument("--manifest", default="data/raw/gqa/image_download_manifest.json")
    parser.add_argument("--base-urls", nargs="*", default=DEFAULT_BASE_URLS)
    parser.add_argument("--limit-images", type=int, default=2500)
    parser.add_argument("--min-success", type=int, default=1000)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    image_root = repo_path(args.image_root)
    image_root.mkdir(parents=True, exist_ok=True)
    image_ids = collect_image_ids(args.input)[: args.limit_images]
    print(f"Need {len(image_ids)} GQA/VG images")

    downloaded: list[dict[str, Any]] = []
    existing: list[str] = []
    failed: list[dict[str, Any]] = []

    for idx, image_id in enumerate(image_ids, start=1):
        if find_existing_image(image_root, image_id):
            existing.append(image_id)
        else:
            result = download_one(image_id, image_root, args)
            if result.get("ok"):
                downloaded.append(result)
            else:
                failed.append(result)
        if idx % 100 == 0:
            print(
                f"progress {idx}/{len(image_ids)}: "
                f"{len(existing)} existing, {len(downloaded)} downloaded, {len(failed)} failed"
            )
        if args.sleep > 0:
            time.sleep(args.sleep)

    success = len(existing) + len(downloaded)
    manifest = {
        "input": str(repo_path(args.input)),
        "image_root": str(image_root),
        "requested": len(image_ids),
        "existing": len(existing),
        "downloaded": len(downloaded),
        "failed": len(failed),
        "base_urls": args.base_urls,
        "failed_examples": failed[:50],
    }
    write_json(args.manifest, manifest)
    print(json.dumps(manifest, indent=2))

    if success < args.min_success:
        print(
            f"Only {success} images are available; required at least {args.min_success}.",
            file=sys.stderr,
        )
        return 1
    return 0


def collect_image_ids(path: str) -> list[str]:
    image_ids: list[str] = []
    seen: set[str] = set()
    for record in iter_jsonl(path):
        image = record.get("image")
        image_id = Path(str(image)).stem if image else ""
        if not image_id:
            raw_id = str(record.get("image_id", ""))
            image_id = raw_id.removeprefix("gqa_train_")
        if image_id and image_id not in seen:
            image_ids.append(image_id)
            seen.add(image_id)
    return image_ids


def find_existing_image(image_root: Path, image_id: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png"):
        path = image_root / f"{image_id}{suffix}"
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def download_one(image_id: str, image_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    out_path = image_root / f"{image_id}.jpg"
    tmp_path = out_path.with_suffix(".jpg.tmp")
    ensure_parent(out_path)
    last_error = ""
    for base_url in args.base_urls:
        url = f"{base_url.rstrip('/')}/{image_id}.jpg"
        for attempt in range(args.retries + 1):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "cvpr-gqa-subset/1.0"})
                with urllib.request.urlopen(request, timeout=args.timeout) as response:
                    if response.getcode() != 200:
                        last_error = f"HTTP {response.getcode()}"
                        continue
                    with tmp_path.open("wb") as f:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                if tmp_path.exists() and tmp_path.stat().st_size > 0:
                    tmp_path.replace(out_path)
                    return {
                        "ok": True,
                        "image_id": image_id,
                        "url": url,
                        "bytes": out_path.stat().st_size,
                    }
                last_error = "empty download"
            except urllib.error.HTTPError as exc:
                last_error = f"HTTP {exc.code}"
                if exc.code == 404:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = repr(exc)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
            if attempt < args.retries:
                time.sleep(2**attempt)
    return {"ok": False, "image_id": image_id, "error": last_error}


if __name__ == "__main__":
    raise SystemExit(main())
