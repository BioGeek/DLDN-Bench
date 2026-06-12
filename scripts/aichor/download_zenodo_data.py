#!/usr/bin/env python3
"""Download the DLDN-Bench MGF and InstaNovo v1.1 files from Zenodo."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path


DEFAULT_RECORD_ID = "19627459"
DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")
ZENODO_API = "https://zenodo.org/api/records/{record_id}"


def md5sum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_suffix(destination.suffix + ".tmp")
    with urllib.request.urlopen(url) as response, tmp_path.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    tmp_path.replace(destination)


def fetch_record(record_id: str) -> dict:
    with urllib.request.urlopen(ZENODO_API.format(record_id=record_id)) as response:
        return json.load(response)


def wanted_file_names(datasets: list[str]) -> list[str]:
    names: list[str] = []
    for dataset in datasets:
        names.append(f"{dataset}_benchmark_dataset.mgf")
        names.append(f"{dataset}_benchmark_dataset_instanovo_pred.csv")
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-id", default=DEFAULT_RECORD_ID)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--metadata-out", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    record = fetch_record(args.record_id)
    files = {item["key"]: item for item in record["files"]}
    manifest: dict[str, object] = {
        "record_id": args.record_id,
        "doi": record["doi"],
        "datasets": args.datasets,
        "files": [],
    }

    for name in wanted_file_names(args.datasets):
        if name not in files:
            raise FileNotFoundError(f"{name} was not found in Zenodo record {args.record_id}")

        file_info = files[name]
        expected_md5 = file_info["checksum"].removeprefix("md5:")
        destination = args.output_dir / name

        if destination.exists() and not args.force:
            actual_md5 = md5sum(destination)
            if actual_md5 == expected_md5:
                print(f"Using existing verified file: {destination}")
            else:
                print(f"Existing file checksum mismatch, re-downloading: {destination}")
                download(file_info["links"]["self"], destination)
        else:
            print(f"Downloading {name} -> {destination}")
            download(file_info["links"]["self"], destination)

        actual_md5 = md5sum(destination)
        if actual_md5 != expected_md5:
            raise RuntimeError(f"Checksum mismatch for {destination}: {actual_md5} != {expected_md5}")

        manifest["files"].append(
            {
                "name": name,
                "path": str(destination),
                "size": destination.stat().st_size,
                "md5": actual_md5,
            }
        )

    args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote download manifest to {args.metadata_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
