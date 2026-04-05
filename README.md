# Darkstore Governance Project

This folder consolidates the darkstore research work into one place.

## Repository Placement

Clone the Hyperledger Fabric samples repository first:

```bash
git clone https://github.com/hyperledger/fabric-samples.git
```

Add this project inside the cloned `fabric-samples` repository as:

```text
fabric-samples/darkstore-governance/
```

The README commands assume this exact placement so the project can reuse `test-network/`.

## What Each Folder Does

- `chaincode/`
  Darkstore Java chaincode for recording order events, verifying SLA compliance, and storing/querying violations.
- `evaluation/`
  Python benchmarking framework for latency, throughput, scalability, SLA accuracy, block confirmation, fault tolerance, and immutability tests.
- `analysis/`
  Jupyter notebook and exported analysis artifacts for paper figures.

## Run The Test Network

From the repository root:

```bash
cd test-network
./network.sh up createChannel -ca
./network.sh deployCC -ccn darkstore -ccp ../darkstore-governance/chaincode/darkstore-java -ccl java
```

To stop the network:

```bash
./network.sh down
```

## Run The Benchmark

From the repository root:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py --mode quick
```

For the full benchmark:

```bash
python3 darkstore-governance/evaluation/run_benchmark.py --mode full
```

## Architecture

```mermaid
flowchart TB
    Client["Client / Fabric CLI
    peer chaincode invoke
    peer chaincode query"]

    subgraph FabricNet["Docker network: fabric_test"]
        subgraph Channel["Channel: mychannel"]
            Orderer["Orderer Org
            orderer.example.com
            Port 7050
            Raft orderer"]

            subgraph Org1["Org1MSP"]
                Peer1["peer0.org1.example.com
                Endorser + Ledger + Gossip
                Port 7051"]
                CC1["darkstore chaincode runtime
                on peer0.org1"]
            end

            subgraph Org2["Org2MSP"]
                Peer2["peer0.org2.example.com
                Endorser + Ledger + Gossip
                Port 9051"]
                CC2["darkstore chaincode runtime
                on peer0.org2"]
            end
        end

        subgraph CAPlane["Certificate Authorities"]
            CA1["ca_org1
            Port 7054"]
            CA2["ca_org2
            Port 8054"]
            CAO["ca_orderer
            Port 9054"]
        end
    end

    Client -->|"submit / query"| Peer1
    Client -->|"submit / query"| Peer2
    Client -->|"broadcast tx"| Orderer

    Peer1 -->|"endorsement + ledger state"| CC1
    Peer2 -->|"endorsement + ledger state"| CC2

    Peer1 <-->|"gossip / block delivery"| Peer2
    Orderer -->|"blocks"| Peer1
    Orderer -->|"blocks"| Peer2

    CA1 -.->|"issues MSP + TLS certs"| Peer1
    CA2 -.->|"issues MSP + TLS certs"| Peer2
    CAO -.->|"issues MSP + TLS certs"| Orderer
```
