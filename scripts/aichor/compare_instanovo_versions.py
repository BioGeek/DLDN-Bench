#!/usr/bin/env python3
"""Compare Zenodo InstaNovo v1.1 predictions with latest InstaNovo predictions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from pyteomics import mgf
from sklearn.metrics import auc

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from constants import aa_dict, unimod_dict
from utils import (
    calculate_aa_precision_coverage,
    calculate_peptide_precision_coverage,
    instanovo_filter_out_unspecified_mods,
)


DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")


def clean_predictions(df: pd.DataFrame, tool_name: str) -> pd.DataFrame:
    seq_col = f"{tool_name}_seq"
    score_col = f"{tool_name}_score"
    df = instanovo_filter_out_unspecified_mods(df, unimod_dict, tool_name)
    df = df[df[seq_col].notna() & (df[seq_col].astype(str) != "")]
    df = df[df[score_col].notna()]
    return df[["scan_number", seq_col, score_col]].copy()


def load_ground_truth(mgf_path: Path, scan_numbers: set[int]) -> pd.DataFrame:
    rows = []
    for index, spectrum in enumerate(mgf.read(str(mgf_path))):
        if index in scan_numbers:
            rows.append((index, spectrum["params"]["seq"]))
    return pd.DataFrame(rows, columns=["scan_number", "groundtruth_seq"])


def calculate_metrics(df: pd.DataFrame, tool_name: str) -> dict[str, float]:
    cols = ["groundtruth_seq", f"{tool_name}_seq", f"{tool_name}_score"]
    peptide_coverage, peptide_precision, _ = calculate_peptide_precision_coverage(df[cols], aa_dict, tool_name)
    aa_coverage, aa_precision, _ = calculate_aa_precision_coverage(df[cols], aa_dict, tool_name)
    return {
        "peptide_auc": float(auc(peptide_coverage, peptide_precision)),
        "aa_auc": float(auc(aa_coverage, aa_precision)),
    }


def write_markdown(summary: pd.DataFrame, output_path: Path, published_peptide_auc: float, published_aa_auc: float) -> None:
    lines = [
        "# InstaNovo v1.1 vs v1.2.0 Metrics",
        "",
        "Metrics use the row intersection after applying the repo's supported-UNIMOD conversion/filtering.",
        "",
        "| Dataset | Tool | Rows scored | Peptide AUC | AA AUC |",
        "|---|---|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['dataset']} | {row['tool']} | {int(row['rows_scored'])} | "
            f"{row['peptide_auc']:.6f} | {row['aa_auc']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Manuscript Headline Reference",
            "",
            f"- Published InstaNovo peptide AUC: `{published_peptide_auc:.3f}`",
            f"- Published InstaNovo amino-acid AUC: `{published_aa_auc:.3f}`",
            "",
            "The manuscript headline values are included as a reference point; dataset-level values may not be directly comparable if the paper aggregated or plotted data differently.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--predictions-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--published-peptide-auc", type=float, default=0.974)
    parser.add_argument("--published-aa-auc", type=float, default=0.985)
    parser.add_argument("--save-aligned", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metric_rows = []
    combined_frames = []

    for dataset in args.datasets:
        print(f"Scoring {dataset}")
        old_path = args.data_dir / f"{dataset}_benchmark_dataset_instanovo_pred.csv"
        new_path = args.predictions_dir / f"{dataset}_instanovo_v1.2.0_pred.csv"
        mgf_path = args.data_dir / f"{dataset}_benchmark_dataset.mgf"

        old = pd.read_csv(old_path, usecols=["scan_number", "transformer_predictions", "transformer_log_probabilities"])
        old = old.rename(
            columns={
                "transformer_predictions": "instanovo_v1_1_seq",
                "transformer_log_probabilities": "instanovo_v1_1_score",
            }
        )
        old = clean_predictions(old, "instanovo_v1_1")

        new = pd.read_csv(new_path, usecols=["scan_number", "predictions", "log_probs"])
        new = new.rename(columns={"predictions": "instanovo_v1_2_seq", "log_probs": "instanovo_v1_2_score"})
        new = clean_predictions(new, "instanovo_v1_2")

        scan_numbers = set(old["scan_number"].astype(int)).intersection(set(new["scan_number"].astype(int)))
        gt = load_ground_truth(mgf_path, scan_numbers)
        merged = gt.merge(old, on="scan_number", how="inner").merge(new, on="scan_number", how="inner")
        merged.insert(0, "dataset", dataset)

        if args.save_aligned:
            merged.to_csv(args.output_dir / f"{dataset}_instanovo_v1_1_vs_v1_2_aligned.csv", index=False)

        for tool_name, label in [
            ("instanovo_v1_1", "InstaNovo v1.1 Zenodo transformer"),
            ("instanovo_v1_2", "InstaNovo v1.2.0 transformer"),
        ]:
            metrics = calculate_metrics(merged, tool_name)
            metric_rows.append(
                {
                    "dataset": dataset,
                    "tool": label,
                    "rows_scored": len(merged),
                    **metrics,
                    "peptide_auc_delta_vs_published": metrics["peptide_auc"] - args.published_peptide_auc,
                    "aa_auc_delta_vs_published": metrics["aa_auc"] - args.published_aa_auc,
                }
            )
        combined_frames.append(merged)

    if len(combined_frames) > 1:
        combined = pd.concat(combined_frames, ignore_index=True)
        for tool_name, label in [
            ("instanovo_v1_1", "InstaNovo v1.1 Zenodo transformer"),
            ("instanovo_v1_2", "InstaNovo v1.2.0 transformer"),
        ]:
            metrics = calculate_metrics(combined, tool_name)
            metric_rows.append(
                {
                    "dataset": "ALL",
                    "tool": label,
                    "rows_scored": len(combined),
                    **metrics,
                    "peptide_auc_delta_vs_published": metrics["peptide_auc"] - args.published_peptide_auc,
                    "aa_auc_delta_vs_published": metrics["aa_auc"] - args.published_aa_auc,
                }
            )

    summary = pd.DataFrame(metric_rows)
    summary.to_csv(args.output_dir / "instanovo_v1_1_vs_v1_2_metrics.csv", index=False)
    (args.output_dir / "instanovo_v1_1_vs_v1_2_metrics.json").write_text(
        json.dumps(summary.to_dict("records"), indent=2) + "\n"
    )
    write_markdown(
        summary,
        args.output_dir / "instanovo_v1_1_vs_v1_2_metrics.md",
        args.published_peptide_auc,
        args.published_aa_auc,
    )
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
