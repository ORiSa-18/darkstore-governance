from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (PROJECT_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evaluation.experiment_runner import BenchmarkConfig, ExperimentRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reproducible benchmarks for the darkstore Fabric chaincode."
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Path to the fabric-samples repository root.",
    )
    parser.add_argument(
        "--network-dir",
        default=str(REPO_ROOT / "test-network"),
        help="Path to the Fabric test-network directory.",
    )
    parser.add_argument(
        "--chaincode-path",
        default="../darkstore-governance/chaincode/darkstore-java",
        help="Path to the Java chaincode, relative to the test-network directory or absolute.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(PROJECT_ROOT / "evaluation" / "results"),
        help="Directory where CSV outputs should be stored.",
    )
    parser.add_argument(
        "--mode",
        choices=("quick", "full"),
        default="full",
        help="Run a shorter smoke test (`quick`) or the full benchmark suite (`full`).",
    )
    parser.add_argument(
        "--workloads",
        nargs="+",
        type=int,
        default=None,
        help="Workload sizes for throughput and scalability experiments.",
    )
    parser.add_argument("--latency-samples", type=int, default=None)
    parser.add_argument("--block-time-samples", type=int, default=None)
    parser.add_argument("--sla-samples-per-scenario", type=int, default=None)
    parser.add_argument("--fault-tolerance-samples", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    network_dir = Path(args.network_dir).resolve()
    chaincode_path = Path(args.chaincode_path)
    if not chaincode_path.is_absolute():
        chaincode_path = (network_dir / chaincode_path).resolve()

    presets = {
        "quick": {
            "workloads": [10, 20, 50],
            "latency_samples": 5,
            "block_time_samples": 3,
            "sla_samples_per_scenario": 2,
            "fault_tolerance_samples": 2,
        },
        "full": {
            "workloads": [10, 100, 1000],
            "latency_samples": 20,
            "block_time_samples": 10,
            "sla_samples_per_scenario": 5,
            "fault_tolerance_samples": 6,
        },
    }
    selected = presets[args.mode]

    config = BenchmarkConfig(
        repo_root=str(repo_root),
        network_dir=str(network_dir),
        chaincode_path=str(chaincode_path),
        results_dir=str(Path(args.results_dir).resolve()),
        workloads=args.workloads or selected["workloads"],
        latency_samples=args.latency_samples or selected["latency_samples"],
        block_time_samples=args.block_time_samples or selected["block_time_samples"],
        sla_samples_per_scenario=(
            args.sla_samples_per_scenario or selected["sla_samples_per_scenario"]
        ),
        fault_tolerance_samples=args.fault_tolerance_samples or selected["fault_tolerance_samples"],
    )
    ExperimentRunner(config).run_all()


if __name__ == "__main__":
    main()
