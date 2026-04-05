from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

import pandas as pd

from evaluation.fabric_client import FabricClient
from evaluation.metrics import append_row, ensure_results_files, utc_now_iso, write_experiment_config


FUNCTION_BY_EVENT = {
    "ORDER_PLACED": "recordOrderPlaced",
    "ORDER_PICKED": "recordOrderPicked",
    "ORDER_PACKED": "recordOrderPacked",
    "ORDER_DISPATCHED": "recordOrderDispatched",
    "ORDER_DELIVERED": "recordOrderDelivered",
}


@dataclass
class BenchmarkConfig:
    repo_root: str
    network_dir: str
    chaincode_path: str
    results_dir: str
    channel_name: str = "mychannel"
    chaincode_name: str = "darkstore"
    workloads: list[int] = field(default_factory=lambda: [10, 100, 1000])
    latency_samples: int = 20
    block_time_samples: int = 10
    sla_samples_per_scenario: int = 5
    fault_tolerance_samples: int = 6
    base_timestamp_ms: int = 1710600000000


class ExperimentRunner:
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.results_dir = Path(config.results_dir)
        ensure_results_files(self.results_dir)
        write_experiment_config(self.results_dir, asdict(config))
        self.client = FabricClient(
            repo_root=Path(config.repo_root),
            network_dir=Path(config.network_dir),
            chaincode_path=Path(config.chaincode_path),
            channel_name=config.channel_name,
            chaincode_name=config.chaincode_name,
        )

    def run_all(self) -> None:
        self.client.ensure_prereqs()
        try:
            self.client.network_up()
            self.client.deploy_chaincode()
            self.run_latency_benchmark()
            self.run_throughput_benchmark()
            self.run_scalability_benchmark()
            self.run_sla_accuracy_benchmark()
            self.run_block_confirmation_benchmark()
            self.run_fault_tolerance_benchmark()
            self.run_immutability_benchmark()
        finally:
            self.client.network_down()

    def run_latency_benchmark(self) -> None:
        for sample_index in range(self.config.latency_samples):
            order_id = self._new_order_id("LAT")
            timestamp = self.config.base_timestamp_ms + (sample_index * 1000)
            result = self.client.invoke(
                "recordOrderPlaced",
                [order_id, "STORE1", str(timestamp)],
            )
            append_row(
                self.results_dir,
                "latency.csv",
                {
                    "timestamp_utc": utc_now_iso(),
                    "experiment": "transaction_latency",
                    "order_id": order_id,
                    "transaction_name": "recordOrderPlaced",
                    "txid": result["txid"],
                    "duration_ms": result["duration_ms"],
                    "success": True,
                    "notes": "",
                },
            )

    def run_throughput_benchmark(self) -> None:
        for workload in self.config.workloads:
            durations = []
            successes = 0
            start_marker = pd.Timestamp.utcnow()
            for offset in range(workload):
                order_id = self._new_order_id("TPS")
                timestamp = self.config.base_timestamp_ms + (offset * 1000)
                result = self.client.invoke(
                    "recordOrderPlaced",
                    [order_id, "STORE1", str(timestamp)],
                )
                durations.append(result["duration_ms"])
                successes += 1
            total_duration_ms = (pd.Timestamp.utcnow() - start_marker).total_seconds() * 1000.0
            append_row(
                self.results_dir,
                "throughput.csv",
                {
                    "timestamp_utc": utc_now_iso(),
                    "experiment": "throughput",
                    "workload_orders": workload,
                    "transactions_submitted": workload,
                    "transactions_succeeded": successes,
                    "total_duration_ms": total_duration_ms,
                    "throughput_tps": successes / max(total_duration_ms / 1000.0, 1e-9),
                    "notes": f"mean_latency_ms={mean(durations):.2f}",
                },
            )

    def run_scalability_benchmark(self) -> None:
        for workload in self.config.workloads:
            latencies = []
            successes = 0
            start_marker = pd.Timestamp.utcnow()
            for offset in range(workload):
                order_id = self._new_order_id(f"SCALE{workload}")
                timestamp = self.config.base_timestamp_ms + (offset * 1000)
                result = self.client.invoke(
                    "recordOrderPlaced",
                    [order_id, "STORE1", str(timestamp)],
                )
                latencies.append(result["duration_ms"])
                successes += 1
            total_duration_ms = (pd.Timestamp.utcnow() - start_marker).total_seconds() * 1000.0
            series = pd.Series(latencies)
            append_row(
                self.results_dir,
                "scalability.csv",
                {
                    "timestamp_utc": utc_now_iso(),
                    "experiment": "scalability",
                    "workload_orders": workload,
                    "avg_latency_ms": float(series.mean()),
                    "p95_latency_ms": float(series.quantile(0.95)),
                    "throughput_tps": successes / max(total_duration_ms / 1000.0, 1e-9),
                    "success_rate": successes / max(workload, 1),
                },
            )

    def run_sla_accuracy_benchmark(self) -> None:
        scenarios = [
            ("COMPLIANT", self._compliant_timestamps(), "NONE", True),
            ("PICKING", self._violation_timestamps("PICKING_SLA_BREACH"), "PICKING_SLA_BREACH", False),
            ("PACKING", self._violation_timestamps("PACKING_SLA_BREACH"), "PACKING_SLA_BREACH", False),
            ("DISPATCH", self._violation_timestamps("DISPATCH_SLA_BREACH"), "DISPATCH_SLA_BREACH", False),
            ("DELIVERY", self._violation_timestamps("DELIVERY_SLA_BREACH"), "DELIVERY_SLA_BREACH", False),
        ]

        for scenario_name, timestamps, expected_violation, expected_sla_satisfied in scenarios:
            for _ in range(self.config.sla_samples_per_scenario):
                order_id = self._new_order_id(scenario_name)
                self._submit_order_flow(order_id, timestamps)
                verify_result = self.client.invoke("verifySLA", [order_id])
                payload = verify_result["payload"] or {}
                actual_violation = payload.get("violationType", "UNKNOWN")
                predicted_sla_satisfied = bool(payload.get("slaSatisfied"))
                append_row(
                    self.results_dir,
                    "sla_accuracy.csv",
                    {
                        "timestamp_utc": utc_now_iso(),
                        "order_id": order_id,
                        "scenario": scenario_name,
                        "expected_violation": expected_violation,
                        "actual_violation": actual_violation,
                        "predicted_sla_satisfied": predicted_sla_satisfied,
                        "expected_sla_satisfied": expected_sla_satisfied,
                        "is_correct": (
                            actual_violation == expected_violation
                            and predicted_sla_satisfied == expected_sla_satisfied
                        ),
                        "verify_latency_ms": verify_result["duration_ms"],
                        "txid": verify_result["txid"],
                    },
                )
                append_row(
                    self.results_dir,
                    "execution_time.csv",
                    {
                        "timestamp_utc": utc_now_iso(),
                        "order_id": order_id,
                        "scenario": scenario_name,
                        "function_name": "verifySLA",
                        "duration_ms": verify_result["duration_ms"],
                        "txid": verify_result["txid"],
                    },
                )

    def run_block_confirmation_benchmark(self) -> None:
        for sample_index in range(self.config.block_time_samples):
            order_id = self._new_order_id("BLK")
            timestamp = self.config.base_timestamp_ms + (sample_index * 1000)
            result = self.client.measure_block_confirmation(
                "recordOrderPlaced",
                [order_id, "STORE1", str(timestamp)],
            )
            append_row(
                self.results_dir,
                "block_times.csv",
                {
                    "timestamp_utc": utc_now_iso(),
                    "order_id": order_id,
                    "transaction_name": "recordOrderPlaced",
                    "txid": result["txid"],
                    "pre_block_height": result["pre_block_height"],
                    "post_block_height": result["post_block_height"],
                    "block_confirmed": result["block_confirmed"],
                    "block_confirmation_ms": result["block_confirmation_ms"],
                },
            )

    def run_fault_tolerance_benchmark(self) -> None:
        baseline_order = self._new_order_id("FTBASE")
        baseline_result = self.client.invoke(
            "recordOrderPlaced",
            [baseline_order, "STORE1", str(self.config.base_timestamp_ms)],
        )
        append_row(
            self.results_dir,
            "fault_tolerance.csv",
            {
                "timestamp_utc": utc_now_iso(),
                "phase": "baseline",
                "order_id": baseline_order,
                "transaction_name": "recordOrderPlaced",
                "success": True,
                "duration_ms": baseline_result["duration_ms"],
                "txid": baseline_result["txid"],
                "notes": "Both peers available",
            },
        )

        self.client.stop_peer()
        try:
            for sample_index in range(self.config.fault_tolerance_samples):
                order_id = self._new_order_id("FT")
                timestamp = self.config.base_timestamp_ms + (sample_index * 2000)
                try:
                    result = self.client.invoke(
                        "recordOrderPlaced",
                        [order_id, "STORE1", str(timestamp)],
                        include_org2=True,
                        check=True,
                    )
                    success = True
                    notes = "Succeeded while org2 peer was unavailable"
                    duration_ms = result["duration_ms"]
                    txid = result["txid"]
                except RuntimeError as exc:
                    success = False
                    notes = str(exc).splitlines()[0]
                    duration_ms = 0.0
                    txid = None

                append_row(
                    self.results_dir,
                    "fault_tolerance.csv",
                    {
                        "timestamp_utc": utc_now_iso(),
                        "phase": "peer0.org2_stopped",
                        "order_id": order_id,
                        "transaction_name": "recordOrderPlaced",
                        "success": success,
                        "duration_ms": duration_ms,
                        "txid": txid,
                        "notes": notes,
                    },
                )
        finally:
            self.client.start_peer()
            peer_ready = self.client.wait_for_peer("localhost", 9051)
            append_row(
                self.results_dir,
                "fault_tolerance.csv",
                {
                    "timestamp_utc": utc_now_iso(),
                    "phase": "peer0.org2_restarted",
                    "order_id": "",
                    "transaction_name": "docker start",
                    "success": peer_ready,
                    "duration_ms": 0.0,
                    "txid": "",
                    "notes": "Peer restart readiness check",
                },
            )
            if not peer_ready:
                raise RuntimeError("peer0.org2 did not become reachable after restart")

    def run_immutability_benchmark(self) -> None:
        order_id = self._new_order_id("IMM")
        placed_ts = self.config.base_timestamp_ms
        self.client.invoke("recordOrderPlaced", [order_id, "STORE1", str(placed_ts)])

        tamper_attempt_blocked = False
        notes = ""
        try:
            self.client.invoke("recordOrderPlaced", [order_id, "STORE1", str(placed_ts + 1)])
        except RuntimeError as exc:
            tamper_attempt_blocked = True
            notes = str(exc).splitlines()[0]

        history = self.client.query_json("queryOrderHistory", [order_id]) or []
        append_row(
            self.results_dir,
            "immutability.csv",
            {
                "timestamp_utc": utc_now_iso(),
                "order_id": order_id,
                "tamper_attempt_blocked": tamper_attempt_blocked,
                "history_preserved": len(history) == 1,
                "history_size": len(history),
                "notes": notes,
            },
        )

    def _submit_order_flow(self, order_id: str, timestamps: dict[str, int]) -> None:
        for event_name in (
            "ORDER_PLACED",
            "ORDER_PICKED",
            "ORDER_PACKED",
            "ORDER_DISPATCHED",
            "ORDER_DELIVERED",
        ):
            self.client.invoke(
                FUNCTION_BY_EVENT[event_name],
                [order_id, "STORE1", str(timestamps[event_name])],
            )

    def _compliant_timestamps(self) -> dict[str, int]:
        base = self.config.base_timestamp_ms
        return {
            "ORDER_PLACED": base,
            "ORDER_PICKED": base + 2 * 60 * 1000,
            "ORDER_PACKED": base + 9 * 60 * 1000,
            "ORDER_DISPATCHED": base + 13 * 60 * 1000,
            "ORDER_DELIVERED": base + 25 * 60 * 1000,
        }

    def _violation_timestamps(self, violation_type: str) -> dict[str, int]:
        timestamps = self._compliant_timestamps()
        if violation_type == "PICKING_SLA_BREACH":
            timestamps["ORDER_PICKED"] = timestamps["ORDER_PLACED"] + 4 * 60 * 1000
        elif violation_type == "PACKING_SLA_BREACH":
            timestamps["ORDER_PACKED"] = timestamps["ORDER_PICKED"] + 11 * 60 * 1000
        elif violation_type == "DISPATCH_SLA_BREACH":
            timestamps["ORDER_DISPATCHED"] = timestamps["ORDER_PACKED"] + 6 * 60 * 1000
        elif violation_type == "DELIVERY_SLA_BREACH":
            timestamps["ORDER_DELIVERED"] = timestamps["ORDER_PLACED"] + 31 * 60 * 1000
        return timestamps

    def _new_order_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:10].upper()}"
