# AIchor Full InstaNovo Benchmark

This branch prepares a full AIchor job for comparing the Zenodo InstaNovo v1.1 transformer predictions against InstaNovo v1.2.2 / `instanovo-v1.2.0` predictions.

## What The Job Does

`manifest.yaml` runs:

```bash
bash scripts/aichor/run_all.sh
```

The job:

1. Downloads only relevant Zenodo files for each selected dataset: the annotated MGF and the old InstaNovo prediction CSV.
2. Runs latest InstaNovo transformer prediction on each MGF.
3. Computes v1.1 vs v1.2.0 peptide and amino-acid AUC metrics.
4. Writes persistent outputs under `$AICHOR_OUTPUT_PATH`.

Large input data is downloaded to `/mnt/storage/dldn-bench/data` by default.

## Outputs

The following are written below `$AICHOR_OUTPUT_PATH`:

- `downloads/zenodo_downloads.json`
- `logs/environment.txt`
- `logs/download.log`
- `logs/predict.log`
- `logs/compare.log`
- `predictions/*_instanovo_v1.2.0_pred.csv`
- `predictions/prediction_runs.json`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.csv`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.json`
- `metrics/instanovo_v1_1_vs_v1_2_metrics.md`

Set `DLDN_SAVE_ALIGNED=1` to also persist per-dataset aligned scoring CSVs.

## Runtime Knobs

Environment variables:

- `DLDN_DATASETS`: dataset list. Accepts comma-separated or whitespace-separated values. Default: all four datasets.
- `DLDN_BATCH_SIZE`: InstaNovo prediction batch size. Default: `128`.
- `DLDN_NUM_WORKERS`: data loader workers. Default: `8`.
- `DLDN_LOG_INTERVAL`: InstaNovo logging interval. Default: `100`.
- `DLDN_NUM_BEAMS`: beam search width. Default: `5`.
- `DLDN_WORKDIR`: working directory for large input data. Default: `/mnt/storage/dldn-bench`.
- `DLDN_SAVE_ALIGNED`: set to `1` to save aligned scored rows.

## CLI Setup

The AIchor CLI is installed with:

```bash
uv tool install aichor-cli --index https://aichor-python-packages.aichor.ai --index-strategy unsafe-best-match
```

Before submitting, authenticate and set context:

```bash
aichor auth key --apikey "$AICHOR_API_KEY"
aichor context set project "$AICHOR_PROJECT_NAME"
aichor context set engine "$AICHOR_ENGINE_NAME"
```

Submit only after explicit approval:

```bash
aichor experiments submit local --repo-dir . --message "full instanovo v1.2.2 benchmark"
```

For committed code:

```bash
aichor experiments submit commit-sha "$(git rev-parse HEAD)" --branch "$(git branch --show-current)"
```
