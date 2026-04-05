# Dark Store Chaincode

Java chaincode for Hyperledger Fabric v2.x that logs fulfillment events and verifies SLA compliance for a quick-commerce workflow.

## Features

- Records `ORDER_PLACED`, `ORDER_PICKED`, `ORDER_PACKED`, `ORDER_DISPATCHED`, and `ORDER_DELIVERED` events.
- Stores each event under a composite key made from `orderId` and `eventType`.
- Queries all events for an order in timestamp order.
- Verifies picking, packing, dispatch, and delivery SLA windows.
- Emits an `SLA_VIOLATION` chaincode event and stores violation data on-ledger when an SLA breach is detected.
- Exposes `queryViolation(orderId)` and `queryAllViolations()` to retrieve stored violation records.

## Project Structure

```text
darkstore-chaincode/
├── build.gradle
├── settings.gradle
├── README.md
└── src/main/
    ├── java/org/example/
    │   ├── DarkStoreContract.java
    │   ├── OrderEvent.java
    │   ├── SLAResult.java
    │   └── ViolationRecord.java
    └── resources/META-INF/services/
        └── org.hyperledger.fabric.contract.ContractInterface
```

## Prerequisites

- Java 17 or newer for the Gradle wrapper used by this project
- Gradle wrapper in this repository
- Hyperledger Fabric 2.x network and peer CLI

Timestamps are expected to be Unix epoch milliseconds.

## Build

```bash
cd darkstore-chaincode
./gradlew installDist
```

The runnable distribution is generated at:

```text
build/install/darkstore/
```

## Working Run Guide

The steps below are copied as-is from the validated run guide.

### 1. Navigate to the Fabric Test Network

```bash
cd ~/fabric-samples/test-network
```

### 2. Start the Fabric Network

```bash
./network.sh up createChannel -ca
```

### 3. Deploy the Chaincode

```bash
./network.sh deployCC -ccn darkstore -ccp ../darkstore-governance/chaincode/darkstore-java -ccl java
```

### 4. Configure Peer Environment Variables

```bash
export PATH=${PWD}/../bin:$PATH
export FABRIC_CFG_PATH=$PWD/../config
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=${PWD}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051
export ORDERER_CA=${PWD}/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export PEER0_ORG1_CA=${PWD}/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
```

### 5. Place an Order

```bash
peer chaincode invoke -o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls --cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD1","STORE1","1710600000000"]}'
```

### 6. Record Order Packing

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD1","STORE1","1710600300000"]}'
```

### 7. Deliver the Order (Normal Case)

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD1","STORE1","1710600500000"]}'
```

### 8. Query the Ledger

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryOrderHistory","Args":["ORD1"]}'
```

### 9. Demonstrate SLA Violation

Create a New Order

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD2","STORE1","1710600000000"]}'
```

Pack the Order

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD2","STORE1","1710600300000"]}'
```

Deliver Late (Triggers SLA Violation)

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD2","STORE1","1710602400000"]}'
```

### 10. Verify SLA Violation

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD2"]}'
```

### 11. Query Violation Details for One Order

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryViolation","Args":["ORD2"]}'
```

### 12. Query All Recorded Violations

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryAllViolations","Args":[]}'
```

## Additional Steps for the Expanded SLA Checks

The current chaincode also supports:

- `recordOrderPicked`
- `recordOrderDispatched`

The SLA thresholds enforced by `verifySLA` are:

- Picking within 3 minutes of placement
- Packing within 10 minutes after picking
- Dispatch within 5 minutes after packing
- Delivery within 30 minutes of placement

Stored violation records include:

- `orderId`
- `violationType`
- `verificationTransactionId`
- `recordedAtMillis`
- full `slaResult`
- full `orderEvents` history used during verification

### Happy Path With All Events

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD100","STORE1","1710600000000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPicked","Args":["ORD100","STORE1","1710600120000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD100","STORE1","1710600600000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDispatched","Args":["ORD100","STORE1","1710600840000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD100","STORE1","1710601500000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD100"]}'
```

### Replicate a Picking SLA Violation

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD201","STORE1","1710600000000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPicked","Args":["ORD201","STORE1","1710600240000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD201","STORE1","1710600600000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDispatched","Args":["ORD201","STORE1","1710600840000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD201","STORE1","1710601500000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD201"]}'
```

Expected violation type: `PICKING_SLA_BREACH`

Inspect the stored violation:

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryViolation","Args":["ORD201"]}'
```

### Replicate a Packing SLA Violation

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD202","STORE1","1710600000000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPicked","Args":["ORD202","STORE1","1710600120000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD202","STORE1","1710600900000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDispatched","Args":["ORD202","STORE1","1710601140000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD202","STORE1","1710601500000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD202"]}'
```

Expected violation type: `PACKING_SLA_BREACH`

Inspect the stored violation:

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryViolation","Args":["ORD202"]}'
```

### Replicate a Dispatch SLA Violation

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD203","STORE1","1710600000000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPicked","Args":["ORD203","STORE1","1710600120000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD203","STORE1","1710600600000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDispatched","Args":["ORD203","STORE1","1710601020000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD203","STORE1","1710601500000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD203"]}'
```

Expected violation type: `DISPATCH_SLA_BREACH`

Inspect the stored violation:

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryViolation","Args":["ORD203"]}'
```

### Replicate a Delivery SLA Violation

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPlaced","Args":["ORD204","STORE1","1710600000000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPicked","Args":["ORD204","STORE1","1710600120000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderPacked","Args":["ORD204","STORE1","1710600600000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDispatched","Args":["ORD204","STORE1","1710600840000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"recordOrderDelivered","Args":["ORD204","STORE1","1710602400000"]}'
```

```bash
peer chaincode invoke \
-o localhost:7050 \
--ordererTLSHostnameOverride orderer.example.com \
--tls \
--cafile $ORDERER_CA \
-C mychannel \
-n darkstore \
--peerAddresses localhost:7051 \
--tlsRootCertFiles $PEER0_ORG1_CA \
--peerAddresses localhost:9051 \
--tlsRootCertFiles ${PWD}/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
--waitForEvent \
-c '{"function":"verifySLA","Args":["ORD204"]}'
```

Expected violation type: `DELIVERY_SLA_BREACH`

Inspect the stored violation:

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryViolation","Args":["ORD204"]}'
```

### Query Order History for Any Test Order

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryOrderHistory","Args":["ORD204"]}'
```

### Query All Violations After Running the Scenarios

```bash
peer chaincode query \
-C mychannel \
-n darkstore \
-c '{"function":"queryAllViolations","Args":[]}'
```
