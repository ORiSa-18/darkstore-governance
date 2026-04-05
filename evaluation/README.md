# Darkstore Evaluation Framework

This directory contains a cross-platform benchmarking framework for the `darkstore` Hyperledger Fabric chaincode.

## What It Does

The benchmark runner:

- starts the Fabric test network with `./network.sh up createChannel -ca`
- deploys the Java chaincode with `./network.sh deployCC -ccn darkstore -ccp ../darkstore-governance/chaincode/darkstore-java -ccl java`
- runs automated experiments for:
  - transaction latency
  - transaction throughput
  - scalability at 10, 100, and 1000 orders
  - SLA detection accuracy
  - `verifySLA` execution time
  - block confirmation time
  - fault tolerance with one peer stopped
  - immutability / tamper-resistance validation
- writes experiment results to CSV files in `darkstore-governance/evaluation/results/`
- always shuts the Fabric network down with `./network.sh down`, even if an experiment fails

## Requirements

- Python 3
- Hyperledger Fabric test-network prerequisites installed
- `peer` CLI available on `PATH`
- Docker available on `PATH`
- The `darkstore` chaincode present at `darkstore-governance/chaincode/darkstore-java`

Python dependencies used:

- `pandas`
- `matplotlib`
- `seaborn`

## Run The Benchmark

From the repository root:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py
```

By default, this runs in `full` mode.

### Quick Mode

Use this for a smoke test before the longer benchmark run:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py --mode quick
```

`quick` mode uses:

- workloads: `10 20 50`
- latency samples: `5`
- block-time samples: `3`
- SLA samples per scenario: `2`
- fault-tolerance samples: `2`

Typical runtime: about `5 to 15 minutes`, depending on machine and Docker/Fabric startup time.

### Full Mode

Use this for the full research evaluation:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py --mode full
```

`full` mode uses:

- workloads: `10 100 1000`
- latency samples: `20`
- block-time samples: `10`
- SLA samples per scenario: `5`
- fault-tolerance samples: `6`

Typical runtime: about `30 to 90 minutes`, depending on machine and Docker/Fabric startup time.

You can still override workload sizes and sample counts manually if needed:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py \
  --mode full \
  --workloads 10 100 1000 \
  --latency-samples 20 \
  --block-time-samples 10 \
  --sla-samples-per-scenario 5 \
  --fault-tolerance-samples 6
```

## Output Files

Benchmark CSV outputs are written to:

- `darkstore-governance/evaluation/results/latency.csv`
- `darkstore-governance/evaluation/results/throughput.csv`
- `darkstore-governance/evaluation/results/scalability.csv`
- `darkstore-governance/evaluation/results/sla_accuracy.csv`
- `darkstore-governance/evaluation/results/block_times.csv`
- `darkstore-governance/evaluation/results/fault_tolerance.csv`
- `darkstore-governance/evaluation/results/execution_time.csv`
- `darkstore-governance/evaluation/results/immutability.csv`

The runner also saves the benchmark configuration to:

- `darkstore-governance/evaluation/results/experiment_config.json`

## Analyze Results

Open the notebook:

- `darkstore-governance/analysis/results_analysis.ipynb`

The notebook loads the CSV files and writes paper-style figures to:

- `darkstore-governance/figures/latency_plot.png`
- `darkstore-governance/figures/throughput_plot.png`
- `darkstore-governance/figures/scalability_plot.png`
- `darkstore-governance/figures/sla_accuracy_plot.png`
- `darkstore-governance/figures/block_confirmation_plot.png`
- `darkstore-governance/figures/fault_tolerance_plot.png`

## Notes

- The benchmark runner assumes the Fabric test-network is located at `test-network/`.
- Fault-tolerance experiments stop `peer0.org2.example.com` using Docker and then restart it.
- Since the framework uses CLI invocation, it is intended for controlled local experiments rather than production traffic replay.
