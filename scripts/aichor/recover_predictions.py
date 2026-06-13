#!/usr/bin/env python3
"""Recover completed InstaNovo prediction CSVs from earlier AIchor outputs."""

from __future__ import annotations

import argparse
import posixpath
import sys
from pathlib import Path


DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")


def remote_prediction_path(source_output_root: str, dataset: str) -> str:
    return posixpath.join(
        source_output_root.rstrip("/"),
        "predictions",
        f"{dataset}_instanovo_v1.2.0_pred.csv",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-output-root", required=True, nargs="+")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    import fsspec

    args.output_dir.mkdir(parents=True, exist_ok=True)
    recovered = 0

    for dataset in args.datasets:
        target = args.output_dir / f"{dataset}_instanovo_v1.2.0_pred.csv"
        if target.exists() and target.stat().st_size > 0 and not args.force:
            print(f"Keeping existing local prediction: {target}")
            continue

        recovered_dataset = False
        for source_root in args.source_output_root:
            source = remote_prediction_path(source_root, dataset)
            fs, source_path = fsspec.core.url_to_fs(source)
            if not fs.exists(source_path):
                print(f"No recovered prediction found for {dataset}: {source}")
                continue

            tmp_target = target.with_suffix(target.suffix + ".tmp")
            fs.get_file(source_path, str(tmp_target))
            tmp_target.replace(target)
            recovered += 1
            recovered_dataset = True
            print(f"Recovered {source} -> {target}")
            break

        if not recovered_dataset:
            continue

    print(f"Recovered {recovered} prediction file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
