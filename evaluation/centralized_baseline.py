from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (PROJECT_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evaluation.metrics import append_row, ensure_results_files, utc_now_iso


ORDER_PLACED = "ORDER_PLACED"
ORDER_PICKED = "ORDER_PICKED"
ORDER_PACKED = "ORDER_PACKED"
ORDER_DISPATCHED = "ORDER_DISPATCHED"
ORDER_DELIVERED = "ORDER_DELIVERED"

PICKING_SLA_MILLIS = 3 * 60 * 1000
PACKING_SLA_MILLIS = 10 * 60 * 1000
DISPATCH_SLA_MILLIS = 5 * 60 * 1000
DELIVERY_SLA_MILLIS = 30 * 60 * 1000


@dataclass
class BaselineConfig:
    results_dir: Path
    mode: str
    workloads: list[int]
    sla_samples_per_scenario: int
    base_timestamp_ms: int = 1710600000000


class CentralizedDarkstore:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, object]]] = {}

    def store_event(self, order_id: str, store_id: str, event_type: str, timestamp: int) -> None:
        events = self._events.setdefault(order_id, [])
        if any(event["eventType"] == event_type for event in events):
            raise ValueError(f"Event {event_type} already exists for order {order_id}")
        events.append(
            {
                "orderId": order_id,
                "storeId": store_id,
                "eventType": event_type,
                "timestamp": timestamp,
            }
        )
        events.sort(key=lambda item: item["timestamp"])

    def check_sla(self, order_id: str) -> dict[str, object]:
        events = {event["eventType"]: event for event in self._events.get(order_id, [])}
        required = [
            ORDER_PLACED,
            ORDER_PICKED,
            ORDER_PACKED,
            ORDER_DISPATCHED,
            ORDER_DELIVERED,
        ]
        for event_type in required:
            if event_type not in events:
                raise ValueError(f"Missing required event {event_type} for order {order_id}")

        picking_duration = events[ORDER_PICKED]["timestamp"] - events[ORDER_PLACED]["timestamp"]
        packing_duration = events[ORDER_PACKED]["timestamp"] - events[ORDER_PICKED]["timestamp"]
        dispatch_duration = events[ORDER_DISPATCHED]["timestamp"] - events[ORDER_PACKED]["timestamp"]
        delivery_duration = events[ORDER_DELIVERED]["timestamp"] - events[ORDER_PLACED]["timestamp"]

        violations = []
        if picking_duration > PICKING_SLA_MILLIS:
            violations.append("PICKING_SLA_BREACH")
        if packing_duration > PACKING_SLA_MILLIS:
            violations.append("PACKING_SLA_BREACH")
        if dispatch_duration > DISPATCH_SLA_MILLIS:
            violations.append("DISPATCH_SLA_BREACH")
        if delivery_duration > DELIVERY_SLA_MILLIS:
            violations.append("DELIVERY_SLA_BREACH")

        return {
            "orderId": order_id,
            "pickingDurationMillis": picking_duration,
            "packingDurationMillis": packing_duration,
            "dispatchDurationMillis": dispatch_duration,
            "deliveryDurationMillis": delivery_duration,
            "slaSatisfied": not violations,
            "violationType": ",".join(violations) if violations else "NONE",
        }


def compliant_timestamps(base: int) -> dict[str, int]:
    return {
        ORDER_PLACED: base,
        ORDER_PICKED: base + 2 * 60 * 1000,
        ORDER_PACKED: base + 9 * 60 * 1000,
        ORDER_DISPATCHED: base + 13 * 60 * 1000,
        ORDER_DELIVERED: base + 25 * 60 * 1000,
    }


def violation_timestamps(base: int, violation: str) -> dict[str, int]:
    timestamps = compliant_timestamps(base)
    if violation == "PICKING_SLA_BREACH":
        timestamps[ORDER_PICKED] = base + 4 * 60 * 1000
    elif violation == "PACKING_SLA_BREACH":
        timestamps[ORDER_PACKED] = timestamps[ORDER_PICKED] + 11 * 60 * 1000
    elif violation == "DISPATCH_SLA_BREACH":
        timestamps[ORDER_DISPATCHED] = timestamps[ORDER_PACKED] + 6 * 60 * 1000
    elif violation == "DELIVERY_SLA_BREACH":
        timestamps[ORDER_DELIVERED] = base + 31 * 60 * 1000
    return timestamps


def run_baseline(config: BaselineConfig) -> None:
    ensure_results_files(config.results_dir)
    simulator = CentralizedDarkstore()

    scenarios = [
        ("COMPLIANT", compliant_timestamps(config.base_timestamp_ms), "NONE"),
        ("PICKING", violation_timestamps(config.base_timestamp_ms, "PICKING_SLA_BREACH"), "PICKING_SLA_BREACH"),
        ("PACKING", violation_timestamps(config.base_timestamp_ms, "PACKING_SLA_BREACH"), "PACKING_SLA_BREACH"),
        ("DISPATCH", violation_timestamps(config.base_timestamp_ms, "DISPATCH_SLA_BREACH"), "DISPATCH_SLA_BREACH"),
        ("DELIVERY", violation_timestamps(config.base_timestamp_ms, "DELIVERY_SLA_BREACH"), "DELIVERY_SLA_BREACH"),
    ]

    accuracies = []
    for workload in config.workloads:
        store_durations = []
        verify_durations = []
        start = perf_counter()
        for idx in range(workload):
            order_id = f"CENT-{uuid4().hex[:10].upper()}"
            timestamps = compliant_timestamps(config.base_timestamp_ms + idx * 1000)
            for event_type, timestamp in timestamps.items():
                event_start = perf_counter()
                simulator.store_event(order_id, "STORE1", event_type, timestamp)
                store_durations.append((perf_counter() - event_start) * 1000.0)
            verify_start = perf_counter()
            simulator.check_sla(order_id)
            verify_durations.append((perf_counter() - verify_start) * 1000.0)
        total_duration_s = max(perf_counter() - start, 1e-9)

        for scenario_name, timestamps, expected_violation in scenarios:
            for sample in range(config.sla_samples_per_scenario):
                order_id = f"{scenario_name}-{sample}-{uuid4().hex[:8].upper()}"
                scenario_simulator = CentralizedDarkstore()
                for event_type, timestamp in timestamps.items():
                    scenario_simulator.store_event(order_id, "STORE1", event_type, timestamp)
                result = scenario_simulator.check_sla(order_id)
                accuracies.append(result["violationType"] == expected_violation)

        append_row(
            config.results_dir,
            "centralized_baseline.csv",
            {
                "timestamp_utc": utc_now_iso(),
                "mode": config.mode,
                "workload_orders": workload,
                "avg_store_event_ms": mean(store_durations) if store_durations else 0.0,
                "avg_verify_sla_ms": mean(verify_durations) if verify_durations else 0.0,
                "throughput_tps": workload / total_duration_s,
                "sla_accuracy": mean(accuracies) if accuracies else 1.0,
                "notes": "In-memory centralized reference implementation",
            },
        )


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run the centralized baseline benchmark.")
    parser.add_argument("--results-dir", default=str(root / "evaluation" / "results"))
    parser.add_argument("--mode", choices=("quick", "full"), default="full")
    parser.add_argument("--workloads", nargs="+", type=int, default=None)
    parser.add_argument("--sla-samples-per-scenario", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    presets = {
        "quick": {"workloads": [10, 20, 50], "sla_samples_per_scenario": 2},
        "full": {"workloads": [10, 100, 1000], "sla_samples_per_scenario": 5},
    }
    selected = presets[args.mode]
    config = BaselineConfig(
        results_dir=Path(args.results_dir).resolve(),
        mode=args.mode,
        workloads=args.workloads or selected["workloads"],
        sla_samples_per_scenario=args.sla_samples_per_scenario or selected["sla_samples_per_scenario"],
    )
    run_baseline(config)


if __name__ == "__main__":
    main()
