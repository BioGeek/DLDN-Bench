#!/usr/bin/env python3
"""Recreate published precision-coverage AUCs from Zenodo prediction files."""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import auc

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calc_and_plot_precision_coverage import plot_precision_coverage_curves
from constants import aa_dict, unimod_dict
from create_result_csv import create_result_csv
from create_venn_plots import (
    create_pyvenn_diagram,
    get_correct_predictions_sets,
    print_intersection_statistics,
)
from utils import (
    calculate_aa_precision_coverage,
    calculate_peptide_precision_coverage,
    instanovo_filter_out_unspecified_mods,
)


DEFAULT_DATASETS = ("PXD043425", "PXD006882", "PXD012824", "PXD043200")
FIGURE1_ORIGINAL_TOOLS = (
    ("msgfplus_percolator", "MS-GF+ with Percolator", 0.997, 0.999),
    ("contranovo", "ContraNovo", 0.981, 0.990),
    ("instanovo", "InstaNovo v1.1 Zenodo transformer", 0.974, 0.985),
    ("casanovo", "CasaNovo", None, None),
    ("pi_helixnovo", "Pi-HelixNovo", None, None),
    ("novor", "Novor", None, None),
    ("pepnovoplus", "PepNovo+", None, None),
)
V12_TOOL = ("instanovo_v1_2", "InstaNovo v1.2.0 transformer", None, None)
PUBLISHED_HEADLINE_TOOLS = ("msgfplus_percolator", "contranovo", "instanovo")
FIGURE1_ORIGINAL_DISPLAY_NAMES = {
    tool_name: label for tool_name, label, _, _ in FIGURE1_ORIGINAL_TOOLS
}
FIGURE1_PLUS_DISPLAY_NAMES = {
    **FIGURE1_ORIGINAL_DISPLAY_NAMES,
    V12_TOOL[0]: V12_TOOL[1],
}
FIGURE1_DE_NOVO_TOOLS = (
    "pepnovoplus",
    "novor",
    "casanovo",
    "pi_helixnovo",
    "contranovo",
    "instanovo",
)
FIGURE1_DE_NOVO_PLUS_TOOLS = (
    "pepnovoplus",
    "novor",
    "casanovo",
    "pi_helixnovo",
    "contranovo",
    "instanovo_v1_2",
)


def iter_files(source: Path) -> list[Path]:
    if not source.exists():
        return []
    return sorted(path for path in source.rglob("*") if path.is_file())


def sync_output_dir(source: Path, destination: str | None) -> None:
    if not destination:
        return

    import fsspec

    fs, root = fsspec.core.url_to_fs(destination)
    root = root.rstrip("/")
    count = 0
    for path in iter_files(source):
        rel = path.relative_to(source).as_posix()
        target = posixpath.join(root, rel)
        parent = posixpath.dirname(target)
        if parent:
            fs.makedirs(parent, exist_ok=True)
        fs.put_file(str(path), target)
        count += 1
    print(f"Incrementally synced {count} published reproduction files to {destination.rstrip('/')}/")


def calculate_metrics(df: pd.DataFrame, tool_name: str) -> dict[str, float | int]:
    seq_col = f"{tool_name}_seq"
    score_col = f"{tool_name}_score"
    tool_df = df[["groundtruth_seq", seq_col, score_col]].copy()
    tool_df = tool_df[tool_df[seq_col].notna() & (tool_df[seq_col].astype(str) != "")]
    tool_df = tool_df[tool_df[score_col].notna()]
    tool_df[score_col] = pd.to_numeric(tool_df[score_col])

    peptide_coverage, peptide_precision, _ = calculate_peptide_precision_coverage(tool_df, aa_dict, tool_name)
    aa_coverage, aa_precision, _ = calculate_aa_precision_coverage(tool_df, aa_dict, tool_name)
    return {
        "rows_scored": int(len(tool_df)),
        "peptide_auc": float(auc(peptide_coverage, peptide_precision)),
        "aa_auc": float(auc(aa_coverage, aa_precision)),
    }


def contranovo_paths(data_dir: Path, dataset: str) -> list[Path]:
    paths = sorted(data_dir.glob(f"{dataset}_benchmark_dataset_contranovo_pred*.txt"))
    if not paths:
        raise FileNotFoundError(f"No ContraNovo prediction files found for {dataset} in {data_dir}")
    return paths


def create_original_intersection(data_dir: Path, work_dir: Path, dataset: str) -> Path:
    output_path = work_dir / f"{dataset}_published_benchmark_predictions.csv"
    create_result_csv(
        ground_truth_file_path=data_dir / f"{dataset}_benchmark_dataset.mgf",
        msgfplus_result_file_path=data_dir / f"{dataset}_benchmark_dataset_msgfplus_pred.parquet",
        pepnovoplus_result_file_path=data_dir / f"{dataset}_benchmark_dataset_pepnovoplus_pred.txt",
        novor_result_file_path=data_dir / f"{dataset}_benchmark_dataset_novor_pred.csv",
        casanovo_result_file_path=data_dir / f"{dataset}_benchmark_dataset_casanovo_pred.mztab",
        pi_helixnovo_result_file_path=data_dir / f"{dataset}_benchmark_dataset_pi_helixnovo_pred.txt",
        contranovo_result_file_path_list=contranovo_paths(data_dir, dataset),
        instanovo_result_file_path=data_dir / f"{dataset}_benchmark_dataset_instanovo_pred.csv",
        save_path=output_path,
    )
    return output_path


def load_original_subset(path: Path) -> pd.DataFrame:
    tools = [tool_name for tool_name, _, _, _ in FIGURE1_ORIGINAL_TOOLS]
    usecols = ["title", "pos_index", "groundtruth_seq"]
    for tool_name in tools:
        usecols.extend([f"{tool_name}_seq", f"{tool_name}_score"])
    return pd.read_csv(path, usecols=usecols)


def read_instanovo_v1_2(path: Path) -> pd.DataFrame:
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    sequence_col = "predictions"
    score_col = next((col for col in ("log_probs", "log_probabilities", "scores", "score") if col in columns), None)
    if sequence_col not in columns or score_col is None:
        raise ValueError(f"{path} does not look like an InstaNovo v1.2 prediction file. Columns: {columns}")

    index_col = "scan_number" if "scan_number" in columns else None
    usecols = [sequence_col, score_col]
    if index_col is not None:
        usecols.append(index_col)

    df = pd.read_csv(path, usecols=usecols)
    if index_col is None:
        df["pos_index"] = range(len(df))
    else:
        df["pos_index"] = df[index_col].astype(int)

    df = df.rename(
        columns={
            sequence_col: "instanovo_v1_2_seq",
            score_col: "instanovo_v1_2_score",
        }
    )
    df = instanovo_filter_out_unspecified_mods(df, unimod_dict, "instanovo_v1_2")
    df = df[df["instanovo_v1_2_seq"].notna() & (df["instanovo_v1_2_seq"].astype(str) != "")]
    df = df[df["instanovo_v1_2_score"].notna()]
    return df[["pos_index", "instanovo_v1_2_seq", "instanovo_v1_2_score"]].copy()


def score_rowset(
    df: pd.DataFrame,
    *,
    dataset: str,
    rowset: str,
    tools: tuple[tuple[str, str, float | None, float | None], ...],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tool_name, label, published_peptide_auc, published_aa_auc in tools:
        metrics = calculate_metrics(df, tool_name)
        rows.append(
            {
                "dataset": dataset,
                "rowset": rowset,
                "tool_key": tool_name,
                "tool": label,
                **metrics,
                "published_peptide_auc": published_peptide_auc,
                "published_aa_auc": published_aa_auc,
                "peptide_auc_delta_vs_published": (
                    metrics["peptide_auc"] - published_peptide_auc
                    if published_peptide_auc is not None
                    else None
                ),
                "aa_auc_delta_vs_published": (
                    metrics["aa_auc"] - published_aa_auc
                    if published_aa_auc is not None
                    else None
                ),
            }
        )
    return rows


def write_precision_coverage_plots(
    df: pd.DataFrame,
    *,
    dataset: str,
    rowset: str,
    output_dir: Path,
    tool_display_names: dict[str, str],
) -> None:
    plot_dir = output_dir / "figure1_precision_coverage"
    table_dir = output_dir / "figure1_precision_coverage_tables"
    plot_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    plot_precision_coverage_curves(
        result_df=df,
        tool_name_dict=tool_display_names,
        benchmark_dataset_name=f"{dataset}_{rowset}",
        save_plot_path=str(plot_dir),
        save_tables_path=str(table_dir),
    )


def write_venn_plot(
    df: pd.DataFrame,
    *,
    dataset: str,
    rowset: str,
    output_dir: Path,
    tool_names: tuple[str, ...],
) -> None:
    venn_dir = output_dir / "figure1_venn"
    venn_dir.mkdir(parents=True, exist_ok=True)
    sets_dict = get_correct_predictions_sets(df, list(tool_names), use_exact=False, aa_dict=aa_dict)
    print_intersection_statistics(sets_dict)
    create_pyvenn_diagram(
        sets_dict,
        list(tool_names),
        "",
        venn_dir / f"{dataset}_{rowset}_de_novo_true_positive_venn.png",
        figsize=(12, 10),
        dpi=300,
        show_numbers=True,
    )


def write_markdown(summary: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Published Figure 1 AUC Reproduction",
        "",
        "Metrics are computed with the repository precision-coverage functions after rebuilding the benchmark intersection from the Zenodo prediction files.",
        "",
        "| Dataset | Rowset | Tool | Rows scored | Peptide AUC | AA AUC | Published peptide AUC | Published AA AUC |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        published_peptide = "" if pd.isna(row["published_peptide_auc"]) else f"{row['published_peptide_auc']:.3f}"
        published_aa = "" if pd.isna(row["published_aa_auc"]) else f"{row['published_aa_auc']:.3f}"
        lines.append(
            f"| {row['dataset']} | {row['rowset']} | {row['tool']} | {int(row['rows_scored'])} | "
            f"{row['peptide_auc']:.6f} | {row['aa_auc']:.6f} | {published_peptide} | {published_aa} |"
        )

    all_original = summary[(summary["dataset"] == "ALL") & (summary["rowset"] == "published_all_tools")]
    all_plus = summary[(summary["dataset"] == "ALL") & (summary["rowset"] == "published_all_tools_plus_v1_2")]
    contranovo = all_original[all_original["tool_key"] == "contranovo"]
    instanovo_v12 = all_plus[all_plus["tool_key"] == "instanovo_v1_2"]
    if not contranovo.empty and not instanovo_v12.empty:
        contra = contranovo.iloc[0]
        v12 = instanovo_v12.iloc[0]
        lines.extend(
            [
                "",
                "## Updated Manuscript Sentences",
                "",
                (
                    "Across the evaluated PRIDE datasets, ContraNovo and InstaNovo achieved the highest "
                    "de novo sequencing performance among the tested tools. In the peptide-level "
                    f"precision-coverage analysis, ContraNovo reproduced at an AUC of {contra['peptide_auc']:.3f} "
                    f"and InstaNovo v1.2.0 reached an AUC of {v12['peptide_auc']:.3f}, approaching the "
                    "performance of the database-search reference MS-GF+."
                ),
                "",
                (
                    "A similar pattern was observed at the amino-acid level. ContraNovo reproduced at an "
                    f"AUC of {contra['aa_auc']:.3f} and InstaNovo v1.2.0 reached an AUC of "
                    f"{v12['aa_auc']:.3f}, again nearly matching MS-GF+."
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Figure 1 Plot Outputs",
            "",
            "Updated precision-coverage plots are written under `figure1_precision_coverage/`.",
            "The corresponding curve tables are written under `figure1_precision_coverage_tables/`.",
            "True-positive de novo overlap plots are written under `figure1_venn/`.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n")


def write_summary_files(metric_rows: list[dict[str, object]], output_dir: Path, stem: str) -> pd.DataFrame:
    summary = pd.DataFrame(metric_rows)
    summary.to_csv(output_dir / f"{stem}.csv", index=False)
    (output_dir / f"{stem}.json").write_text(json.dumps(summary.to_dict("records"), indent=2) + "\n")
    write_markdown(summary, output_dir / f"{stem}.md")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--predictions-dir", type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    parser.add_argument("--include-instanovo-v1-2", action="store_true")
    parser.add_argument("--save-aligned", action="store_true")
    parser.add_argument("--sync-output-root")
    args = parser.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    metric_rows: list[dict[str, object]] = []
    original_frames: list[pd.DataFrame] = []
    plus_frames: list[pd.DataFrame] = []

    for dataset in args.datasets:
        print(f"Recreating original benchmark rowset for {dataset}")
        intersection_path = create_original_intersection(args.data_dir, args.work_dir, dataset)
        original = load_original_subset(intersection_path)
        original.insert(0, "dataset", dataset)
        metric_rows.extend(
            score_rowset(
                original,
                dataset=dataset,
                rowset="published_all_tools",
                tools=FIGURE1_ORIGINAL_TOOLS,
            )
        )
        write_precision_coverage_plots(
            original,
            dataset=dataset,
            rowset="published_all_tools",
            output_dir=args.output_dir,
            tool_display_names=FIGURE1_ORIGINAL_DISPLAY_NAMES,
        )
        write_venn_plot(
            original,
            dataset=dataset,
            rowset="published_all_tools",
            output_dir=args.output_dir,
            tool_names=FIGURE1_DE_NOVO_TOOLS,
        )
        original_frames.append(original)

        if args.save_aligned:
            original.to_csv(args.output_dir / f"{dataset}_published_all_tools_aligned.csv", index=False)
        write_summary_files(metric_rows, args.output_dir, "published_figure1_auc_reproduction_partial")
        sync_output_dir(args.output_dir, args.sync_output_root)

        if args.include_instanovo_v1_2:
            if args.predictions_dir is None:
                raise ValueError("--predictions-dir is required with --include-instanovo-v1-2")
            v12 = read_instanovo_v1_2(args.predictions_dir / f"{dataset}_instanovo_v1.2.0_pred.csv")
            plus = original.merge(v12, on="pos_index", how="inner")
            metric_rows.extend(
                score_rowset(
                    plus,
                    dataset=dataset,
                    rowset="published_all_tools_plus_v1_2",
                    tools=(*FIGURE1_ORIGINAL_TOOLS, V12_TOOL),
                )
            )
            write_precision_coverage_plots(
                plus,
                dataset=dataset,
                rowset="published_all_tools_plus_v1_2",
                output_dir=args.output_dir,
                tool_display_names=FIGURE1_PLUS_DISPLAY_NAMES,
            )
            write_venn_plot(
                plus,
                dataset=dataset,
                rowset="published_all_tools_plus_v1_2",
                output_dir=args.output_dir,
                tool_names=FIGURE1_DE_NOVO_PLUS_TOOLS,
            )
            plus_frames.append(plus)

            if args.save_aligned:
                plus.to_csv(args.output_dir / f"{dataset}_published_all_tools_plus_v1_2_aligned.csv", index=False)
            write_summary_files(metric_rows, args.output_dir, "published_figure1_auc_reproduction_partial")
            sync_output_dir(args.output_dir, args.sync_output_root)

        if not args.save_aligned:
            intersection_path.unlink(missing_ok=True)

    if len(original_frames) > 1:
        combined = pd.concat(original_frames, ignore_index=True)
        metric_rows.extend(
            score_rowset(
                combined,
                dataset="ALL",
                rowset="published_all_tools",
                tools=FIGURE1_ORIGINAL_TOOLS,
            )
        )
        write_precision_coverage_plots(
            combined,
            dataset="ALL",
            rowset="published_all_tools",
            output_dir=args.output_dir,
            tool_display_names=FIGURE1_ORIGINAL_DISPLAY_NAMES,
        )
        write_venn_plot(
            combined,
            dataset="ALL",
            rowset="published_all_tools",
            output_dir=args.output_dir,
            tool_names=FIGURE1_DE_NOVO_TOOLS,
        )
        write_summary_files(metric_rows, args.output_dir, "published_figure1_auc_reproduction_partial")
        sync_output_dir(args.output_dir, args.sync_output_root)

    if len(plus_frames) > 1:
        combined_plus = pd.concat(plus_frames, ignore_index=True)
        metric_rows.extend(
            score_rowset(
                combined_plus,
                dataset="ALL",
                rowset="published_all_tools_plus_v1_2",
                tools=(*FIGURE1_ORIGINAL_TOOLS, V12_TOOL),
            )
        )
        write_precision_coverage_plots(
            combined_plus,
            dataset="ALL",
            rowset="published_all_tools_plus_v1_2",
            output_dir=args.output_dir,
            tool_display_names=FIGURE1_PLUS_DISPLAY_NAMES,
        )
        write_venn_plot(
            combined_plus,
            dataset="ALL",
            rowset="published_all_tools_plus_v1_2",
            output_dir=args.output_dir,
            tool_names=FIGURE1_DE_NOVO_PLUS_TOOLS,
        )
        write_summary_files(metric_rows, args.output_dir, "published_figure1_auc_reproduction_partial")
        sync_output_dir(args.output_dir, args.sync_output_root)

    summary = write_summary_files(metric_rows, args.output_dir, "published_figure1_auc_reproduction")
    summary_path = args.output_dir / "published_figure1_auc_reproduction.csv"
    sync_output_dir(args.output_dir, args.sync_output_root)
    print(summary.to_string(index=False))
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
