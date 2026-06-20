# InstaNovo v1.2.2 AIchor Full Benchmark

Date: 2026-06-17
Last updated: 2026-06-20
Branch: `aichor`

## Scope

Benchmarked Zenodo InstaNovo v1.1 transformer predictions against latest installed InstaNovo `1.2.2`, using the `instanovo-v1.2.0` transformer checkpoint. The branch also contains the later all-tools Figure 1 reproduction plots and AUC summary extended with InstaNovo v1.2.0 predictions.

Datasets:

- `PXD043425`
- `PXD006882`
- `PXD012824`
- `PXD043200`

The AIchor job downloads only the relevant Zenodo files for each dataset:

- `{dataset}_benchmark_dataset.mgf`
- `{dataset}_benchmark_dataset_instanovo_pred.csv`

The all-tools Figure 1 reproduction additionally uses the archived MS-GF+, ContraNovo, CasaNovo, Pi-HelixNovo, Novor, and PepNovo+ prediction files from the same benchmark record.

## What Was Added

Created and pushed the `aichor` branch with:

- `manifest.yaml` for AIchor execution on one H100 GPU.
- `Dockerfile` using a `uv` virtual environment.
- Zenodo download, prediction, recovery, sync, comparison, and plotting scripts under `scripts/aichor/`.
- Recovery logic for failed AIchor runs so completed prediction CSVs are reused.
- Compare-only and plot-only modes to avoid rerunning expensive prediction work.
- A schema-flexible v1.1 loader because `PXD043200` uses `predictions` / `log_probabilities` instead of `transformer_predictions` / `transformer_log_probabilities`.

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
- `095080d3-3f19-41c7-a45b-f1a95a27b43a`: plot-only run; completed successfully and uploaded precision-coverage plots for all four datasets plus the combined `ALL` rowset.

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

## Interpretation

InstaNovo v1.2.0 improves over the Zenodo InstaNovo v1.1 transformer predictions on every evaluated dataset and at both peptide and amino-acid resolution. The aggregate gain is `+0.022441` peptide AUC and `+0.019618` amino-acid AUC, corresponding to relative improvements of `+2.42%` and `+2.05%`.

| Dataset | Peptide AUC delta | Peptide relative delta | AA AUC delta | AA relative delta |
|---|---:|---:|---:|---:|
| `PXD043425` | +0.081617 | +10.22% | +0.072008 | +8.17% |
| `PXD006882` | +0.011712 | +1.21% | +0.011098 | +1.13% |
| `PXD012824` | +0.027114 | +2.91% | +0.024126 | +2.51% |
| `PXD043200` | +0.015131 | +1.63% | +0.014620 | +1.53% |
| `ALL` | +0.022441 | +2.42% | +0.019618 | +2.05% |

The largest absolute improvement is on `PXD043425`, where peptide AUC rises from `0.798529` to `0.880146` and amino-acid AUC rises from `0.880913` to `0.952921`. This dataset is only about `9.0%` of the combined scored rowset, so it does not dominate the aggregate despite being the clearest win.

`PXD006882` is already near saturation for v1.1, so the absolute improvement is smaller but still positive: v1.2.0 reaches `0.982373` peptide AUC and `0.993688` amino-acid AUC. This is the only individual dataset where v1.2.0 exceeds the manuscript headline InstaNovo references of `0.974` peptide AUC and `0.985` amino-acid AUC.

The aggregate result is weighted most heavily by `PXD043200`, which contributes about `49.2%` of the scored rows, followed by `PXD012824` at about `25.3%`. On those two largest datasets, v1.2.0 gives moderate but consistent gains, which explains why the combined curve improves clearly but does not jump as much as `PXD043425`.

The precision-coverage plots should be read as confidence-threshold behavior, not just endpoint accuracy. Because AUC improves on every dataset, the v1.2.0 confidence ranking is better overall: across the coverage range, retained predictions are more precise on average than the corresponding v1.1 retained predictions.

## Relation To Published Numbers

The manuscript headline reference values are:

- Published InstaNovo peptide AUC: `0.974`
- Published InstaNovo amino-acid AUC: `0.985`

The combined InstaNovo-only benchmark result is below those headline values, but v1.2.0 improves over the Zenodo v1.1 transformer predictions on every dataset in this run. This comparison is not an exact reproduction of the manuscript Figure 1 headline rowset: it compares only InstaNovo v1.1 and v1.2.0 on their aligned, post-filtering intersection.

Combined deltas vs the manuscript headline reference:

- v1.1 peptide AUC delta: `-0.044891`
- v1.1 AA AUC delta: `-0.026642`
- v1.2.0 peptide AUC delta: `-0.022450`
- v1.2.0 AA AUC delta: `-0.007024`

## Figure 1 All-Tools Reproduction

The all-tools Figure 1 reproduction was then rerun from the Zenodo prediction files and extended with InstaNovo v1.2.0 predictions. MS-GF+ reproduces the manuscript headline values closely. The de novo tool AUCs are lower than the manuscript headline values on the reconstructed all-dataset rowset, although `PXD006882` reproduces the manuscript ContraNovo and InstaNovo v1.1 numbers closely.

On the reconstructed all-tools-plus-v1.2 rowset, InstaNovo v1.2.0 is the top de novo method by peptide and amino-acid AUC:

| Tool | Rows scored | Peptide AUC | AA AUC |
|---|---:|---:|---:|
| MS-GF+ with Percolator | 2,767,525 | 0.997447 | 0.998551 |
| ContraNovo | 2,767,525 | 0.950945 | 0.972711 |
| InstaNovo v1.1 Zenodo transformer | 2,767,525 | 0.938361 | 0.966493 |
| CasaNovo | 2,767,525 | 0.889553 | 0.942696 |
| Pi-HelixNovo | 2,767,525 | 0.767271 | 0.891850 |
| Novor | 2,767,525 | 0.199337 | 0.604701 |
| PepNovo+ | 2,767,525 | 0.075620 | 0.291876 |
| InstaNovo v1.2.0 transformer | 2,767,525 | 0.957412 | 0.981321 |

The updated all-tools Venn analysis reports `48,884` ContraNovo-only and `205,932` InstaNovo v1.2.0-only correct predictions on the combined rowset.

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

Plot-job status:

```text
Succeeded / Completed
```

Plot output prefix:

```text
output/095080d3-3f19-41c7-a45b-f1a95a27b43a/plots/
```

The tracked per-dataset plot files were initially created by this plot-only run as InstaNovo v1.1 vs v1.2.0 plots, but were later replaced in the branch with the corresponding fixed-colour all-tools Figure 1 reproduction plots that include InstaNovo v1.2.0. The retained filenames are:

- `plots/PXD043425_peptide_precision_coverage.png`
- `plots/PXD043425_aminoacid_precision_coverage.png`
- `plots/PXD006882_peptide_precision_coverage.png`
- `plots/PXD006882_aminoacid_precision_coverage.png`
- `plots/PXD012824_peptide_precision_coverage.png`
- `plots/PXD012824_aminoacid_precision_coverage.png`
- `plots/PXD043200_peptide_precision_coverage.png`
- `plots/PXD043200_aminoacid_precision_coverage.png`

The aggregate `ALL` plots and updated Venn plot tracked in this branch also use the fixed-colour all-tools Figure 1 reproduction outputs and the same flattened filenames as the Zenodo upload:

- `plots/published_reproduction__figure1_precision_coverage__ALL_published_all_tools_plus_v1_2_peptide_precision_coverage.png`
- `plots/published_reproduction__figure1_precision_coverage__ALL_published_all_tools_plus_v1_2_aminoacid_precision_coverage.png`
- `plots/published_reproduction__figure1_venn__ALL_published_all_tools_plus_v1_2_de_novo_true_positive_venn.png`

The same successful run also re-uploaded the four recovered v1.2.0 prediction CSVs under:

```text
output/095080d3-3f19-41c7-a45b-f1a95a27b43a/predictions/
```

## Local Artifacts

Repo-sized artifacts from the successful metrics and plot runs have been downloaded under:

```text
reports/artifacts/instanovo_v1_2_full_benchmark/
```

Included files:

- `metrics/instanovo_v1_1_vs_v1_2_metrics.csv`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.json`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.md`
- eight per-dataset fixed-colour all-tools Figure 1 precision-coverage PNGs that include InstaNovo v1.2.0
- two fixed-colour aggregate all-tools Figure 1 precision-coverage PNGs with Zenodo-flattened filenames
- one fixed-colour aggregate all-tools Figure 1 Venn PNG with a Zenodo-flattened filename

These local artifacts are repo-sized and are reasonable to keep in git. The recovered InstaNovo v1.2.0 prediction CSVs are not included because they are `2.1 GiB` total:

| Dataset | Prediction CSV size |
|---|---:|
| `PXD043425` | 184.9 MiB |
| `PXD006882` | 366.6 MiB |
| `PXD012824` | 625.9 MiB |
| `PXD043200` | 1014.3 MiB |

The larger files and additional benchmark outputs are archived in the published Zenodo record:
[DLDN-Bench InstaNovo v1.2.2 Figure 1 benchmark outputs](https://zenodo.org/records/19627459).
That record includes the prediction CSVs, fixed-colour Figure 1 reproduction plots, Venn diagrams, AUC summaries, workflow logs, and download manifest. Zenodo asset filenames are flattened with `__` standing in for original path separators.

The bulky intermediate precision-coverage table CSVs are not included in the Zenodo record because they total approximately `46 GiB`, but they can be provided on request.

## Earlier Local Calibration

Before moving to AIchor, a 1% `PXD043425` v1.2.0 calibration run completed on the laptop GPU:

- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- Subset spectra: `3,842`
- Runtime: `495.2` seconds
- Throughput: about `8.1-8.3` seconds per batch at `batch_size=64`

That calibration showed the local laptop GPU was too slow for the full benchmark, so the full run was moved to AIchor.
