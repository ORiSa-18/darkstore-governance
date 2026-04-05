#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-quick}"

if [[ "$MODE" != "quick" && "$MODE" != "full" ]]; then
  echo "Usage: ./darkstore-governance/run_experiments.sh [quick|full]"
  exit 1
fi

echo "Running blockchain benchmark in ${MODE} mode..."
python3 "${ROOT_DIR}/evaluation/run_benchmark.py" --mode "${MODE}"

echo "Running centralized baseline in ${MODE} mode..."
python3 "${ROOT_DIR}/evaluation/centralized_baseline.py" --mode "${MODE}"

echo "Exporting paper-facing results..."
python3 "${ROOT_DIR}/evaluation/export_results.py"

echo "Done. See ${ROOT_DIR}/results/"
