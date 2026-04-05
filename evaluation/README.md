# Evaluation Framework

This folder contains the benchmarking code for the darkstore research system.

## Components

- `run_benchmark.py`
  Runs blockchain experiments against the Fabric test-network.
- `centralized_baseline.py`
  Runs a simple non-blockchain baseline with in-memory `store_event()` and `check_sla()`.
- `export_results.py`
  Exports paper-facing artifacts into `../results/`.

## Run

Preferred entrypoint from the repository root:

```bash
./darkstore-governance/run_experiments.sh quick
```

Or for the full run:

```bash
./darkstore-governance/run_experiments.sh full
```

## Outputs

- raw CSVs: `darkstore-governance/evaluation/results/`
- exported plots and logs: `darkstore-governance/results/`
