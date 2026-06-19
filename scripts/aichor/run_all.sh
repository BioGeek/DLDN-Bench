#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${DLDN_DATASETS:-}" ]]; then
  # Accept either comma-separated or whitespace-separated dataset lists.
  read -r -a DATASETS <<< "${DLDN_DATASETS//,/ }"
else
  DATASETS=(PXD043425 PXD006882 PXD012824 PXD043200)
fi

WORK_ROOT="${DLDN_WORKDIR:-/mnt/storage/dldn-bench}"
DATA_DIR="${DLDN_DATA_DIR:-${WORK_ROOT}/data}"
REMOTE_OUTPUT_ROOT="${AICHOR_OUTPUT_PATH:-}"
if [[ "${REMOTE_OUTPUT_ROOT}" == s3://* ]]; then
  OUTPUT_ROOT="${DLDN_LOCAL_OUTPUT_DIR:-${WORK_ROOT}/outputs}"
else
  OUTPUT_ROOT="${REMOTE_OUTPUT_ROOT:-${PWD}/aichor_outputs}"
  REMOTE_OUTPUT_ROOT=""
fi
PREDICTIONS_DIR="${OUTPUT_ROOT}/predictions"
METRICS_DIR="${OUTPUT_ROOT}/metrics"
PLOTS_DIR="${OUTPUT_ROOT}/plots"
PUBLISHED_DIR="${OUTPUT_ROOT}/published_reproduction"
LOG_DIR="${OUTPUT_ROOT}/logs"
PLOT_INPUT_DIR="${DLDN_PLOT_INPUT_DIR:-${WORK_ROOT}/plot_inputs}"
PUBLISHED_WORK_DIR="${DLDN_PUBLISHED_WORK_DIR:-${WORK_ROOT}/published_reproduction_work}"

MODEL="${DLDN_INSTANOVO_MODEL:-instanovo-v1.2.0}"
BATCH_SIZE="${DLDN_BATCH_SIZE:-128}"
NUM_WORKERS="${DLDN_NUM_WORKERS:-8}"
LOG_INTERVAL="${DLDN_LOG_INTERVAL:-100}"
NUM_BEAMS="${DLDN_NUM_BEAMS:-5}"

mkdir -p "${DATA_DIR}" "${PREDICTIONS_DIR}" "${METRICS_DIR}" "${PLOTS_DIR}" "${PUBLISHED_DIR}" "${LOG_DIR}"

sync_outputs() {
  local status=$?
  if [[ -n "${REMOTE_OUTPUT_ROOT}" ]]; then
    echo "Syncing outputs to ${REMOTE_OUTPUT_ROOT}"
    python scripts/aichor/sync_outputs.py \
      --source "${OUTPUT_ROOT}" \
      --destination "${REMOTE_OUTPUT_ROOT}" || true
  fi
  exit "${status}"
}
trap sync_outputs EXIT

{
  echo "Started: $(date --iso-8601=seconds)"
  echo "Datasets: ${DATASETS[*]}"
  echo "Output root: ${OUTPUT_ROOT}"
  echo "Remote output root: ${REMOTE_OUTPUT_ROOT:-<none>}"
  echo "Work root: ${WORK_ROOT}"
  echo "Data dir: ${DATA_DIR}"
  echo "Model: ${MODEL}"
  echo "Batch size: ${BATCH_SIZE}"
  echo "Num workers: ${NUM_WORKERS}"
  echo "Num beams: ${NUM_BEAMS}"
  echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-<unset>}"
  python - <<'PY'
import torch
print("torch:", torch.__version__)
print("torch.version.cuda:", torch.version.cuda)
print("cuda_available:", torch.cuda.is_available())
if torch.cuda.is_available():
    for idx in range(torch.cuda.device_count()):
        print(f"cuda_device_{idx}:", torch.cuda.get_device_name(idx))
PY
} | tee "${LOG_DIR}/environment.txt"

DOWNLOAD_INCLUDE=(mgf instanovo)
if [[ "${DLDN_RECREATE_PUBLISHED:-0}" == "1" ]]; then
  DOWNLOAD_INCLUDE=(mgf all_predictions)
fi

python scripts/aichor/download_zenodo_data.py \
  --output-dir "${DATA_DIR}" \
  --metadata-out "${OUTPUT_ROOT}/downloads/zenodo_downloads.json" \
  --datasets "${DATASETS[@]}" \
  --include "${DOWNLOAD_INCLUDE[@]}" \
  2>&1 | tee "${LOG_DIR}/download.log"

if [[ -n "${DLDN_RECOVER_PREDICTIONS_FROM:-}" ]]; then
  read -r -a RECOVERY_ROOTS <<< "${DLDN_RECOVER_PREDICTIONS_FROM//,/ }"
  python scripts/aichor/recover_predictions.py \
    --source-output-root "${RECOVERY_ROOTS[@]}" \
    --output-dir "${PREDICTIONS_DIR}" \
    --datasets "${DATASETS[@]}" \
    2>&1 | tee "${LOG_DIR}/recover_predictions.log"
fi

if [[ "${DLDN_COMPARE_ONLY:-0}" == "1" ]]; then
  {
    echo "Compare-only mode enabled; skipping InstaNovo prediction."
    for dataset in "${DATASETS[@]}"; do
      prediction_path="${PREDICTIONS_DIR}/${dataset}_instanovo_v1.2.0_pred.csv"
      if [[ ! -s "${prediction_path}" ]]; then
        echo "Missing recovered prediction: ${prediction_path}" >&2
        exit 1
      fi
      echo "Using recovered prediction: ${prediction_path}"
    done
  } 2>&1 | tee "${LOG_DIR}/predict.log"
else
  python scripts/aichor/run_instanovo_predictions.py \
    --data-dir "${DATA_DIR}" \
    --output-dir "${PREDICTIONS_DIR}" \
    --metadata-out "${OUTPUT_ROOT}/predictions/prediction_runs.json" \
    --datasets "${DATASETS[@]}" \
    --model "${MODEL}" \
    --batch-size "${BATCH_SIZE}" \
    --num-workers "${NUM_WORKERS}" \
    --log-interval "${LOG_INTERVAL}" \
    --num-beams "${NUM_BEAMS}" \
    2>&1 | tee "${LOG_DIR}/predict.log"
fi

if [[ "${DLDN_SKIP_COMPARE:-0}" == "1" ]]; then
  echo "Skipping metrics comparison." 2>&1 | tee "${LOG_DIR}/compare.log"
else
  COMPARE_ARGS=()
  if [[ "${DLDN_SAVE_ALIGNED:-0}" == "1" ]]; then
    COMPARE_ARGS+=(--save-aligned)
  fi

  python scripts/aichor/compare_instanovo_versions.py \
    --data-dir "${DATA_DIR}" \
    --predictions-dir "${PREDICTIONS_DIR}" \
    --output-dir "${METRICS_DIR}" \
    --datasets "${DATASETS[@]}" \
    "${COMPARE_ARGS[@]}" \
    2>&1 | tee "${LOG_DIR}/compare.log"
fi

if [[ "${DLDN_RUN_PLOTS:-0}" == "1" ]]; then
  python scripts/aichor/build_and_plot_precision_coverage.py \
    --data-dir "${DATA_DIR}" \
    --predictions-dir "${PREDICTIONS_DIR}" \
    --aligned-dir "${PLOT_INPUT_DIR}" \
    --output-dir "${PLOTS_DIR}" \
    --datasets "${DATASETS[@]}" \
    2>&1 | tee "${LOG_DIR}/plot_precision_coverage.log"
fi

if [[ "${DLDN_RECREATE_PUBLISHED:-0}" == "1" ]]; then
  PUBLISHED_ARGS=()
  if [[ "${DLDN_INCLUDE_INSTANOVO_V1_2:-1}" == "1" ]]; then
    PUBLISHED_ARGS+=(--include-instanovo-v1-2 --predictions-dir "${PREDICTIONS_DIR}")
  fi
  if [[ "${DLDN_SAVE_PUBLISHED_ALIGNED:-0}" == "1" ]]; then
    PUBLISHED_ARGS+=(--save-aligned)
  fi
  if [[ "${DLDN_SKIP_PLOT_TABLES:-0}" == "1" ]]; then
    PUBLISHED_ARGS+=(--skip-plot-tables)
  fi
  if [[ -n "${REMOTE_OUTPUT_ROOT}" ]]; then
    PUBLISHED_ARGS+=(--sync-output-root "${REMOTE_OUTPUT_ROOT%/}/published_reproduction")
  fi

  python scripts/aichor/recreate_published_benchmark.py \
    --data-dir "${DATA_DIR}" \
    --work-dir "${PUBLISHED_WORK_DIR}" \
    --output-dir "${PUBLISHED_DIR}" \
    --datasets "${DATASETS[@]}" \
    "${PUBLISHED_ARGS[@]}" \
    2>&1 | tee "${LOG_DIR}/published_reproduction.log"
fi

echo "Finished: $(date --iso-8601=seconds)" | tee -a "${LOG_DIR}/environment.txt"
