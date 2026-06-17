#!/usr/bin/env python3
"""Build aligned InstaNovo result CSVs and run precision-coverage plotting."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.aichor.compare_instanovo_versions import (
    clean_predictions,
    load_ground_truth,
    read_prediction_columns,
)


DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")


def build_aligned_frame(data_dir: Path, predictions_dir: Path, dataset: str) -> pd.DataFrame:
    old_path = data_dir / f"{dataset}_benchmark_dataset_instanovo_pred.csv"
    new_path = predictions_dir / f"{dataset}_instanovo_v1.2.0_pred.csv"
    mgf_path = data_dir / f"{dataset}_benchmark_dataset.mgf"

    old = read_prediction_columns(
        old_path,
        schema_name="InstaNovo v1.1",
        sequence_candidates=("transformer_predictions", "predictions"),
        score_candidates=("transformer_log_probabilities", "log_probabilities", "log_probs"),
        sequence_out="instanovo_v1_1_seq",
        score_out="instanovo_v1_1_score",
    )
    old = clean_predictions(old, "instanovo_v1_1")

    new = read_prediction_columns(
        new_path,
        schema_name="InstaNovo v1.2",
        sequence_candidates=("predictions",),
        score_candidates=("log_probs", "log_probabilities"),
        sequence_out="instanovo_v1_2_seq",
        score_out="instanovo_v1_2_score",
    )
    new = clean_predictions(new, "instanovo_v1_2")

    scan_numbers = set(old["scan_number"].astype(int)).intersection(set(new["scan_number"].astype(int)))
    gt = load_ground_truth(mgf_path, scan_numbers)
    merged = gt.merge(old, on="scan_number", how="inner").merge(new, on="scan_number", how="inner")
    merged.insert(0, "dataset", dataset)
    return merged


def run_plotter(input_path: Path, output_dir: Path, dataset: str) -> None:
    command = [
        sys.executable,
        "calc_and_plot_precision_coverage.py",
        "--input",
        str(input_path),
        "--output",
        str(output_dir),
        "--dataset",
        dataset,
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--predictions-dir", required=True, type=Path)
    parser.add_argument("--aligned-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--combined-dataset-name", default="ALL")
    args = parser.parse_args()

    args.aligned_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for dataset in args.datasets:
        print(f"Building aligned plot input for {dataset}")
        frame = build_aligned_frame(args.data_dir, args.predictions_dir, dataset)
        frames.append(frame)
        aligned_path = args.aligned_dir / f"{dataset}_instanovo_v1_1_vs_v1_2_aligned.csv"
        frame.to_csv(aligned_path, index=False)
        run_plotter(aligned_path, args.output_dir, dataset)

    if len(frames) > 1:
        combined = pd.concat(frames, ignore_index=True)
        aligned_path = args.aligned_dir / f"{args.combined_dataset_name}_instanovo_v1_1_vs_v1_2_aligned.csv"
        combined.to_csv(aligned_path, index=False)
        run_plotter(aligned_path, args.output_dir, args.combined_dataset_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
