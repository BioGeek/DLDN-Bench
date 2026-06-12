#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${DLDN_DATASETS:-}" ]]; then
  # Accept either comma-separated or whitespace-separated dataset lists.
  read -r -a DATASETS <<< "${DLDN_DATASETS//,/ }"
else
  DATASETS=(PXD043425 PXD006882 PXD012824 PXD043200)
fi

OUTPUT_ROOT="${AICHOR_OUTPUT_PATH:-${PWD}/aichor_outputs}"
WORK_ROOT="${DLDN_WORKDIR:-/mnt/storage/dldn-bench}"
DATA_DIR="${DLDN_DATA_DIR:-${WORK_ROOT}/data}"
PREDICTIONS_DIR="${OUTPUT_ROOT}/predictions"
METRICS_DIR="${OUTPUT_ROOT}/metrics"
LOG_DIR="${OUTPUT_ROOT}/logs"

MODEL="${DLDN_INSTANOVO_MODEL:-instanovo-v1.2.0}"
BATCH_SIZE="${DLDN_BATCH_SIZE:-128}"
NUM_WORKERS="${DLDN_NUM_WORKERS:-8}"
LOG_INTERVAL="${DLDN_LOG_INTERVAL:-100}"
NUM_BEAMS="${DLDN_NUM_BEAMS:-5}"

mkdir -p "${DATA_DIR}" "${PREDICTIONS_DIR}" "${METRICS_DIR}" "${LOG_DIR}"

{
  echo "Started: $(date --iso-8601=seconds)"
  echo "Datasets: ${DATASETS[*]}"
  echo "Output root: ${OUTPUT_ROOT}"
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

python scripts/aichor/download_zenodo_data.py \
  --output-dir "${DATA_DIR}" \
  --metadata-out "${OUTPUT_ROOT}/downloads/zenodo_downloads.json" \
  --datasets "${DATASETS[@]}" \
  2>&1 | tee "${LOG_DIR}/download.log"

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

echo "Finished: $(date --iso-8601=seconds)" | tee -a "${LOG_DIR}/environment.txt"
