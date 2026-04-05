from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Export paper-facing result artifacts.")
    parser.add_argument(
        "--results-dir",
        default=str(project_root / "evaluation" / "results"),
        help="Directory containing benchmark CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "results"),
        help="Directory for exported PNGs and logs.csv.",
    )
    return parser.parse_args()


def export_results(results_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="paper")

    latency = pd.read_csv(results_dir / "latency.csv")
    throughput = pd.read_csv(results_dir / "throughput.csv")
    centralized = pd.read_csv(results_dir / "centralized_baseline.csv")

    if not latency.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.histplot(latency["duration_ms"], kde=True, ax=ax, color="#1f77b4")
        ax.set_title("Blockchain Transaction Latency")
        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Count")
        fig.tight_layout()
        fig.savefig(output_dir / "latency.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    if not throughput.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.lineplot(data=throughput, x="workload_orders", y="throughput_tps", marker="o", ax=ax, label="Blockchain")
        if not centralized.empty:
            sns.lineplot(
                data=centralized,
                x="workload_orders",
                y="throughput_tps",
                marker="s",
                ax=ax,
                label="Centralized",
            )
        ax.set_title("Throughput Comparison")
        ax.set_xlabel("Orders")
        ax.set_ylabel("Throughput (TPS)")
        fig.tight_layout()
        fig.savefig(output_dir / "throughput.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    logs_rows = []
    if not latency.empty:
        logs_rows.append(
            {
                "metric": "blockchain_avg_latency_ms",
                "value": float(latency["duration_ms"].mean()),
                "source": "latency.csv",
            }
        )
    if not throughput.empty:
        logs_rows.append(
            {
                "metric": "blockchain_avg_throughput_tps",
                "value": float(throughput["throughput_tps"].mean()),
                "source": "throughput.csv",
            }
        )
    if not centralized.empty:
        logs_rows.extend(
            [
                {
                    "metric": "centralized_avg_store_event_ms",
                    "value": float(centralized["avg_store_event_ms"].mean()),
                    "source": "centralized_baseline.csv",
                },
                {
                    "metric": "centralized_avg_verify_sla_ms",
                    "value": float(centralized["avg_verify_sla_ms"].mean()),
                    "source": "centralized_baseline.csv",
                },
                {
                    "metric": "centralized_avg_throughput_tps",
                    "value": float(centralized["throughput_tps"].mean()),
                    "source": "centralized_baseline.csv",
                },
            ]
        )

    pd.DataFrame(logs_rows).to_csv(output_dir / "logs.csv", index=False)


def main() -> None:
    args = parse_args()
    export_results(Path(args.results_dir).resolve(), Path(args.output_dir).resolve())


if __name__ == "__main__":
    main()
