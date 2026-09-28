"""Download the CC0 completejourney distribution and materialize Parquet files.

This uses the public completejourney R package data at an exact Git commit. The
package DESCRIPTION declares License: CC0. The large RDS files are not committed
to this repository; this script downloads, hashes and converts them locally.

Usage:
    python scripts/fetch_completejourney_cc0.py data/retail
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pyreadr

SOURCE_REPO = "bradleyboehmke/completejourney"
SOURCE_COMMIT = "5b5d06192b9856edd04e4d405787af2f2e4a1fef"
SOURCE_LICENSE = "CC0"
RAW_ROOT = (
    "https://raw.githubusercontent.com/"
    f"{SOURCE_REPO}/{SOURCE_COMMIT}/data"
)

FILES = {
    "transactions": "transactions.rds",
    "promotions": "promotions.rds",
    "products": "products.rda",
    "demographics": "demographics.rda",
    "campaigns": "campaigns.rda",
    "campaign_descriptions": "campaign_descriptions.rda",
    "coupons": "coupons.rda",
    "coupon_redemptions": "coupon_redemptions.rda",
}

EXPECTED_ROWS = {
    "transactions": 1_469_307,
    "promotions": 20_940_529,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(client: httpx.Client, url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                handle.write(chunk)
    partial.replace(destination)


def read_r_frame(path: Path, preferred_name: str):
    objects = pyreadr.read_r(str(path))
    if preferred_name in objects:
        return objects[preferred_name]
    if len(objects) == 1:
        return next(iter(objects.values()))
    available = ", ".join(str(key) for key in objects)
    raise RuntimeError(
        f"Could not resolve {preferred_name!r} inside {path.name}; objects: {available}"
    )


def normalize_columns(frame):
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    return frame


def write_parquet(frame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Preserve pandas categoricals. The promotions table has >20M rows and
    # materializing factor columns as Python strings needlessly multiplies RAM.
    frame.to_parquet(destination, index=False, compression="zstd")


def reusable_manifest(output_dir: Path) -> dict[str, Any] | None:
    manifest_path = output_dir / "completejourney-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("source_commit") != SOURCE_COMMIT:
        return None
    if manifest.get("source_license") != SOURCE_LICENSE:
        return None
    files = manifest.get("files") or {}
    for logical_name in FILES:
        record = files.get(logical_name) or {}
        parquet_name = record.get("parquet_file")
        if not parquet_name:
            return None
        parquet_path = output_dir / str(parquet_name)
        if not parquet_path.exists() or parquet_path.stat().st_size <= 0:
            return None
        expected = EXPECTED_ROWS.get(logical_name)
        if expected is not None and int(record.get("rows") or -1) != expected:
            return None
    return manifest


def materialize(
    output_dir: Path,
    *,
    keep_r_files: bool,
    force: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    raw_dir = output_dir / "_source_r"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not force:
        cached = reusable_manifest(output_dir)
        if cached is not None:
            print(
                "[cache] Complete Journey Parquet is already materialized "
                f"for {SOURCE_COMMIT[:7]}; reusing it."
            )
            return cached

    manifest: dict[str, Any] = {
        "dataset": "completejourney",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "source_license": SOURCE_LICENSE,
        "source_package": "completejourney",
        "files": {},
    }

    with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0)) as client:
        for logical_name, source_name in FILES.items():
            source_path = raw_dir / source_name
            url = f"{RAW_ROOT}/{source_name}"
            print(f"[download] {logical_name}: {url}")
            download(client, url, source_path)

            print(f"[convert]  {logical_name}: {source_path.name}")
            frame = normalize_columns(read_r_frame(source_path, logical_name))
            expected = EXPECTED_ROWS.get(logical_name)
            if expected is not None and len(frame) != expected:
                raise RuntimeError(
                    f"{logical_name} row count mismatch: expected {expected:,}, got {len(frame):,}"
                )

            parquet_path = output_dir / f"{logical_name}.parquet"
            write_parquet(frame, parquet_path)
            manifest["files"][logical_name] = {
                "source_file": source_name,
                "source_url": url,
                "source_sha256": sha256(source_path),
                "source_bytes": source_path.stat().st_size,
                "parquet_file": parquet_path.name,
                "parquet_sha256": sha256(parquet_path),
                "parquet_bytes": parquet_path.stat().st_size,
                "rows": int(len(frame)),
                "columns": [str(column) for column in frame.columns],
            }
            print(
                f"[ready]    {logical_name}: {len(frame):,} rows -> "
                f"{parquet_path.name} ({parquet_path.stat().st_size / 1024**2:.1f} MiB)"
            )

            del frame

    manifest_path = output_dir / "completejourney-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not keep_r_files:
        for path in raw_dir.glob("*"):
            path.unlink()
        try:
            raw_dir.rmdir()
        except OSError:
            pass

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default="data/retail")
    parser.add_argument(
        "--keep-r-files",
        action="store_true",
        help="Keep downloaded RDS/RDA source files after conversion.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore an existing valid manifest and re-download/rebuild Parquet.",
    )
    args = parser.parse_args()

    manifest = materialize(
        Path(args.output_dir),
        keep_r_files=args.keep_r_files,
        force=args.force,
    )
    core = manifest["files"]
    print("\nComplete Journey ready:")
    print(f"  transactions: {core['transactions']['rows']:,}")
    print(f"  promotions:   {core['promotions']['rows']:,}")
    print(f"  products:     {core['products']['rows']:,}")
    print(f"  manifest:     {Path(args.output_dir) / 'completejourney-manifest.json'}")


if __name__ == "__main__":
    main()
