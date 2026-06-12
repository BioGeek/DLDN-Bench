#!/usr/bin/env python3
"""Run latest InstaNovo transformer predictions for DLDN-Bench MGF files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--metadata-out", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--model", default="instanovo-v1.2.0")
    parser.add_argument("--batch-size", default="128")
    parser.add_argument("--num-workers", default="8")
    parser.add_argument("--log-interval", default="100")
    parser.add_argument("--num-beams", default="5")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs = []

    for dataset in args.datasets:
        mgf_path = args.data_dir / f"{dataset}_benchmark_dataset.mgf"
        output_path = args.output_dir / f"{dataset}_instanovo_v1.2.0_pred.csv"
        if not mgf_path.exists():
            raise FileNotFoundError(f"Missing MGF: {mgf_path}")
        if output_path.exists() and output_path.stat().st_size > 0 and not args.force:
            print(f"Using existing predictions: {output_path}")
            runs.append({"dataset": dataset, "output": str(output_path), "skipped": True})
            continue

        command = [
            "instanovo",
            "transformer",
            "predict",
            "--data-path",
            str(mgf_path),
            "--output-path",
            str(output_path),
            "--instanovo-model",
            args.model,
            "--denovo",
            f"batch_size={args.batch_size}",
            f"num_workers={args.num_workers}",
            "save_all_predictions=false",
            f"log_interval={args.log_interval}",
            f"num_beams={args.num_beams}",
        ]
        print("Running:", " ".join(command))
        start = time.time()
        subprocess.run(command, check=True)
        elapsed_seconds = time.time() - start
        runs.append(
            {
                "dataset": dataset,
                "output": str(output_path),
                "elapsed_seconds": elapsed_seconds,
                "skipped": False,
            }
        )

    args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_out.write_text(json.dumps({"runs": runs}, indent=2) + "\n")
    print(f"Wrote prediction manifest to {args.metadata_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
