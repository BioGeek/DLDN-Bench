# InstaNovo v1.2.0 Benchmark Check

Date: 2026-06-12
Branch: `bench-latest-instanovo`

## Scope

Downloaded only the files needed to benchmark InstaNovo on `PXD043425`:

- `PXD043425_benchmark_dataset.mgf`
- `PXD043425_benchmark_dataset_instanovo_pred.csv`

Files were stored outside the repo in `/dev/shm/dldn-bench/data`.

Verified Zenodo MD5 checksums:

- `PXD043425_benchmark_dataset.mgf`: `c6e4bebcd21852565b1b3b57685cdf9d`
- `PXD043425_benchmark_dataset_instanovo_pred.csv`: `358e1082e8e5c118bd89f8bef207cd6f`

## Runtime Environment

GPU-capable environment:

```bash
micromamba run -p /home/j-vangoey/.local/miniconda3/envs/instanovo_env instanovo version
```

Versions:

- InstaNovo: `1.2.2`
- InstaNovo+: `1.2.2`
- PyTorch: `2.8.0`
- CUDA: `12.9`
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU` with ~7.8 GB VRAM

The similarly named `/home/j-vangoey/.local/miniconda3/envs/instanovo` env has CPU-only PyTorch and was not used for inference.

## PTM Handling

Used the repo's existing `instanovo_filter_out_unspecified_mods` behavior:

- Supported UNIMOD tokens are converted to the repo's expected mass-delta format.
- Rows are removed only if the predicted sequence still contains an unsupported `[UNIMOD:...]` token after conversion.
- Supported PTMs are not removed from scored sequences.

## Full v1.1 Baseline on PXD043425

Scored the Zenodo InstaNovo v1.1 transformer predictions against the full `PXD043425` MGF.

- Raw spectra/predictions: `384,174`
- Removed for unsupported predicted UNIMOD tokens: `5,943` (`1.55%`)
- Rows scored: `378,231`
- Peptide AUC: `0.782336`
- Amino-acid AUC: `0.862463`

## Latest v1.2.0 Inference

Command shape used for latest transformer-only inference:

```bash
CUDA_VISIBLE_DEVICES=0 TMPDIR=/dev/shm \
micromamba run -p /home/j-vangoey/.local/miniconda3/envs/instanovo_env \
  instanovo transformer predict \
  --data-path /dev/shm/dldn-bench/data/PXD043425_benchmark_dataset.mgf \
  --output-path /dev/shm/dldn-bench/results/PXD043425_instanovo_v1.2.0_subset001.csv \
  --instanovo-model instanovo-v1.2.0 \
  --denovo \
  subset=0.01 batch_size=64 num_workers=4 save_all_predictions=false log_interval=10
```

The 1% calibration run completed successfully on CUDA:

- Subset spectra: `3,842`
- Batches: `61`
- Runtime: `495.2` seconds
- Throughput: about `8.1-8.3` seconds per batch at `batch_size=64`

The full latest run was started with `batch_size=64`, but stopped before completion because no progress interval had completed yet and the calibration extrapolated to roughly `14-15+` hours on this laptop GPU. A full run should be done on a larger GPU or left to run unattended.

## 1% Subset Comparison

The v1.2.0 subset output was aligned by `scan_number` to the same v1.1 Zenodo predictions and MGF ground truth. Metrics below use the intersection after unsupported-UNIMOD filtering.

| Tool | Rows scored | Peptide AUC | AA AUC |
|---|---:|---:|---:|
| InstaNovo v1.1 Zenodo transformer | 3,601 | 0.799346 | 0.884175 |
| InstaNovo v1.2.0 transformer | 3,601 | 0.877383 | 0.954005 |

Deltas on this sampled subset:

- Peptide AUC: `+0.078037`
- AA AUC: `+0.069830`

## Relation to Manuscript Numbers

The manuscript reports headline InstaNovo AUCs of `0.974` peptide-level and `0.985` amino-acid-level. Those are not directly comparable to this local result because this run is limited to `PXD043425` and, for v1.2.0, only a 1% sampled subset was completed.
