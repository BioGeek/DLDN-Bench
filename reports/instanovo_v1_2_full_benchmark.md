# InstaNovo v1.2.2 AIchor Full Benchmark

Date: 2026-06-17
Branch: `aichor`

## Scope

Benchmarked Zenodo InstaNovo v1.1 transformer predictions against latest installed InstaNovo `1.2.2`, using the `instanovo-v1.2.0` transformer checkpoint.

Datasets:

- `PXD043425`
- `PXD006882`
- `PXD012824`
- `PXD043200`

The AIchor job downloads only the relevant Zenodo files for each dataset:

- `{dataset}_benchmark_dataset.mgf`
- `{dataset}_benchmark_dataset_instanovo_pred.csv`

## What Was Added

Created and pushed the `aichor` branch with:

- `manifest.yaml` for AIchor execution on one H100 GPU.
- `Dockerfile` using a `uv` virtual environment.
- Zenodo download, prediction, recovery, sync, comparison, and plotting scripts under `scripts/aichor/`.
- Recovery logic for failed AIchor runs so completed prediction CSVs are reused.
- Compare-only and plot-only modes to avoid rerunning expensive prediction work.
- A schema-flexible v1.1 loader because `PXD043200` uses `predictions` / `log_probabilities` instead of `transformer_predictions` / `transformer_log_probabilities`.

Recent branch commits:

- `738acd6` - add AIchor precision-coverage plotting workflow.
- `f2e3f5a` - support compare-only metrics run.
- `64efb1b` - recover multiple AIchor prediction outputs.
- `68640fc` - recover prior AIchor prediction outputs.
- `ec55cad` - avoid InstaNovo internal AIchor bucket upload failures.

## Runtime Environment

AIchor GPU environment used for the successful compare-only run:

- GPU: `NVIDIA H100 80GB HBM3`
- PyTorch: `2.5.1+cu124`
- CUDA available: `true`
- Installed package: `instanovo==1.2.2`
- Model argument: `--instanovo-model instanovo-v1.2.0`
- Prediction settings: `batch_size=128`, `num_workers=8`, `num_beams=5`

## Run History

Prediction work completed in AIchor and was recovered across runs:

- `9fea844e-2644-4721-b6b7-b85fabe451d7`: completed and uploaded `PXD043425`, then failed after InstaNovo's internal post-save S3 upload path.
- `46c58e9d-b5f6-43ae-a18a-8112eeec7d6c`: recovered `PXD043425`, completed and uploaded `PXD006882`, then failed after post-save upload handling.
- `b96234df-2fff-4239-8288-faeef8ae81b0`: recovered previous outputs, completed `PXD012824` and `PXD043200`, then failed during comparison before the v1.1 schema patch.
- `7c3e0e59-35c9-41ea-81d3-ab8cbdb102fa`: compare-only run; recovered all four v1.2.0 prediction CSVs and completed metrics successfully.
- `095080d3-3f19-41c7-a45b-f1a95a27b43a`: plot-only run submitted from `738acd6`; currently in AIchor Docker build at the last check.

Successful metrics output prefix:

```text
output/7c3e0e59-35c9-41ea-81d3-ab8cbdb102fa/
```

Uploaded files include:

- `metrics/instanovo_v1_1_vs_v1_2_metrics.csv`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.json`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.md`
- all four `predictions/*_instanovo_v1.2.0_pred.csv`

## PTM Handling

Used the repo's existing `instanovo_filter_out_unspecified_mods` behavior:

- Supported UNIMOD tokens are converted to the repo's expected mass-delta format.
- Rows are removed only if the predicted sequence still contains an unsupported `[UNIMOD:...]` token after conversion.
- Supported PTMs are not removed from scored sequences.

Unsupported-UNIMOD filtering counts:

| Dataset | v1.1 rows removed | v1.1 % | v1.2 rows removed | v1.2 % |
|---|---:|---:|---:|---:|
| `PXD043425` | 5,943 | 1.55 | 20,562 | 5.35 |
| `PXD006882` | 14,229 | 2.09 | 20,199 | 2.97 |
| `PXD012824` | 36,074 | 3.23 | 94,701 | 8.48 |
| `PXD043200` | 34,423 | 1.70 | 52,926 | 2.61 |

## Final Metrics

Metrics use the row intersection after supported-UNIMOD conversion/filtering.

| Dataset | Tool | Rows scored | Peptide AUC | AA AUC |
|---|---|---:|---:|---:|
| `PXD043425` | InstaNovo v1.1 Zenodo transformer | 358,789 | 0.798529 | 0.880913 |
| `PXD043425` | InstaNovo v1.2.0 transformer | 358,789 | 0.880146 | 0.952921 |
| `PXD006882` | InstaNovo v1.1 Zenodo transformer | 654,557 | 0.970661 | 0.982590 |
| `PXD006882` | InstaNovo v1.2.0 transformer | 654,557 | 0.982373 | 0.993688 |
| `PXD012824` | InstaNovo v1.1 Zenodo transformer | 1,005,566 | 0.930216 | 0.959711 |
| `PXD012824` | InstaNovo v1.2.0 transformer | 1,005,566 | 0.957330 | 0.983837 |
| `PXD043200` | InstaNovo v1.1 Zenodo transformer | 1,955,469 | 0.925932 | 0.953988 |
| `PXD043200` | InstaNovo v1.2.0 transformer | 1,955,469 | 0.941063 | 0.968608 |
| `ALL` | InstaNovo v1.1 Zenodo transformer | 3,974,381 | 0.929109 | 0.958358 |
| `ALL` | InstaNovo v1.2.0 transformer | 3,974,381 | 0.951550 | 0.977976 |

Combined v1.2.0 improvement over v1.1:

- Peptide AUC: `+0.022441`
- Amino-acid AUC: `+0.019618`

## Relation To Published Numbers

The manuscript headline reference values are:

- Published InstaNovo peptide AUC: `0.974`
- Published InstaNovo amino-acid AUC: `0.985`

The combined benchmark result is below those headline values, but v1.2.0 improves over the Zenodo v1.1 transformer predictions on every dataset in this run.

Combined deltas vs the manuscript headline reference:

- v1.1 peptide AUC delta: `-0.044891`
- v1.1 AA AUC delta: `-0.026642`
- v1.2.0 peptide AUC delta: `-0.022450`
- v1.2.0 AA AUC delta: `-0.007024`

## Precision-Coverage Plots

Added a plot-only AIchor workflow that:

1. Recovers the four v1.2.0 prediction CSVs from `b96234df-2fff-4239-8288-faeef8ae81b0`.
2. Skips prediction with `DLDN_COMPARE_ONLY=1`.
3. Skips the metrics comparison pass with `DLDN_SKIP_COMPARE=1`.
4. Rebuilds aligned inputs for each dataset and `ALL`.
5. Runs `calc_and_plot_precision_coverage.py` for each aligned input.
6. Syncs PNG plots under the AIchor output `plots/` prefix.

Plot job:

```text
095080d3-3f19-41c7-a45b-f1a95a27b43a
```

Current plot-job status at last check:

```text
Building / Processing
```

Expected plot output prefix after completion:

```text
output/095080d3-3f19-41c7-a45b-f1a95a27b43a/plots/
```

Expected files include peptide and amino-acid precision-coverage PNGs for:

- `PXD043425`
- `PXD006882`
- `PXD012824`
- `PXD043200`
- `ALL`

## Earlier Local Calibration

Before moving to AIchor, a 1% `PXD043425` v1.2.0 calibration run completed on the laptop GPU:

- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- Subset spectra: `3,842`
- Runtime: `495.2` seconds
- Throughput: about `8.1-8.3` seconds per batch at `batch_size=64`

That calibration showed the local laptop GPU was too slow for the full benchmark, so the full run was moved to AIchor.
