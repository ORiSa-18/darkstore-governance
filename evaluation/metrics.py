from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


RESULT_HEADERS = {
    "latency.csv": [
        "timestamp_utc",
        "experiment",
        "order_id",
        "transaction_name",
        "txid",
        "duration_ms",
        "success",
        "notes",
    ],
    "throughput.csv": [
        "timestamp_utc",
        "experiment",
        "workload_orders",
        "transactions_submitted",
        "transactions_succeeded",
        "total_duration_ms",
        "throughput_tps",
        "notes",
    ],
    "scalability.csv": [
        "timestamp_utc",
        "experiment",
        "workload_orders",
        "avg_latency_ms",
        "p95_latency_ms",
        "throughput_tps",
        "success_rate",
    ],
    "sla_accuracy.csv": [
        "timestamp_utc",
        "order_id",
        "scenario",
        "expected_violation",
        "actual_violation",
        "predicted_sla_satisfied",
        "expected_sla_satisfied",
        "is_correct",
        "verify_latency_ms",
        "txid",
    ],
    "block_times.csv": [
        "timestamp_utc",
        "order_id",
        "transaction_name",
        "txid",
        "pre_block_height",
        "post_block_height",
        "block_confirmed",
        "block_confirmation_ms",
    ],
    "fault_tolerance.csv": [
        "timestamp_utc",
        "phase",
        "order_id",
        "transaction_name",
        "success",
        "duration_ms",
        "txid",
        "notes",
    ],
    "execution_time.csv": [
        "timestamp_utc",
        "order_id",
        "scenario",
        "function_name",
        "duration_ms",
        "txid",
    ],
    "immutability.csv": [
        "timestamp_utc",
        "order_id",
        "tamper_attempt_blocked",
        "history_preserved",
        "history_size",
        "notes",
    ],
}


def ensure_results_files(results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    for filename, headers in RESULT_HEADERS.items():
        path = results_dir / filename
        if not path.exists():
            pd.DataFrame(columns=headers).to_csv(path, index=False)


def append_row(results_dir: Path, filename: str, row: dict[str, Any]) -> None:
    ensure_results_files(results_dir)
    path = results_dir / filename
    headers = RESULT_HEADERS[filename]
    normalized = {column: row.get(column) for column in headers}
    pd.DataFrame([normalized], columns=headers).to_csv(
        path,
        mode="a",
        header=False,
        index=False,
    )


def write_experiment_config(results_dir: Path, config: dict[str, Any]) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    target = results_dir / "experiment_config.json"
    with target.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
    return target


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
