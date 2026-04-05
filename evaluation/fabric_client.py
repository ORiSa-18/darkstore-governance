from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TXID_PATTERN = re.compile(r"txid\s*\[([0-9a-f]+)\]", re.IGNORECASE)
PAYLOAD_PATTERN = re.compile(r'payload:"((?:\\.|[^"])*)"', re.DOTALL)


@dataclass
class CommandResult:
    command: list[str]
    stdout: str
    stderr: str
    returncode: int
    duration_ms: float


class FabricClient:
    """Thin wrapper around the Fabric CLI for reproducible local experiments."""

    def __init__(
        self,
        repo_root: Path,
        network_dir: Path,
        chaincode_path: Path,
        channel_name: str = "mychannel",
        chaincode_name: str = "darkstore",
        orderer_address: str = "localhost:7050",
        peer0_org1_address: str = "localhost:7051",
        peer0_org2_address: str = "localhost:9051",
        peer0_org2_container: str = "peer0.org2.example.com",
    ) -> None:
        self.repo_root = repo_root
        self.network_dir = network_dir
        self.chaincode_path = chaincode_path
        self.channel_name = channel_name
        self.chaincode_name = chaincode_name
        self.orderer_address = orderer_address
        self.peer0_org1_address = peer0_org1_address
        self.peer0_org2_address = peer0_org2_address
        self.peer0_org2_container = peer0_org2_container

        self._base_env = os.environ.copy()
        self._base_env["PATH"] = (
            f"{self.repo_root / 'bin'}{os.pathsep}{self._base_env.get('PATH', '')}"
        )
        self._base_env["FABRIC_CFG_PATH"] = str(self.repo_root / "config")
        self._base_env["CORE_PEER_TLS_ENABLED"] = "true"
        self._base_env["CORE_PEER_LOCALMSPID"] = "Org1MSP"
        self._base_env["CORE_PEER_TLS_ROOTCERT_FILE"] = str(
            self.network_dir
            / "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        )
        self._base_env["CORE_PEER_MSPCONFIGPATH"] = str(
            self.network_dir
            / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
        )
        self._base_env["CORE_PEER_ADDRESS"] = self.peer0_org1_address
        self._base_env["ORDERER_CA"] = str(
            self.network_dir
            / "organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem"
        )
        self._base_env["PEER0_ORG1_CA"] = str(
            self.network_dir
            / "organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
        )
        self._base_env["PEER0_ORG2_CA"] = str(
            self.network_dir
            / "organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"
        )

    @property
    def orderer_ca(self) -> str:
        return self._base_env["ORDERER_CA"]

    @property
    def peer0_org1_ca(self) -> str:
        return self._base_env["PEER0_ORG1_CA"]

    @property
    def peer0_org2_ca(self) -> str:
        return self._base_env["PEER0_ORG2_CA"]

    def ensure_prereqs(self) -> None:
        lookup_path = self._base_env.get("PATH", "")
        missing = [
            name for name in ("peer", "docker") if shutil.which(name, path=lookup_path) is None
        ]
        if shutil.which("bash", path=lookup_path) is None:
            missing.append("bash")
        if missing:
            raise RuntimeError(
                "Missing required executables for the benchmark framework: "
                + ", ".join(sorted(set(missing)))
            )

    def network_up(self) -> CommandResult:
        return self._run(
            ["bash", "./network.sh", "up", "createChannel", "-ca"],
            cwd=self.network_dir,
        )

    def deploy_chaincode(self) -> CommandResult:
        return self._run(
            [
                "bash",
                "./network.sh",
                "deployCC",
                "-ccn",
                self.chaincode_name,
                "-ccp",
                str(self.chaincode_path),
                "-ccl",
                "java",
            ],
            cwd=self.network_dir,
        )

    def network_down(self) -> CommandResult:
        return self._run(
            ["bash", "./network.sh", "down"],
            cwd=self.network_dir,
            check=False,
        )

    def invoke(
        self,
        function: str,
        args: list[str],
        *,
        wait_for_event: bool = True,
        include_org2: bool = True,
        check: bool = True,
    ) -> dict[str, Any]:
        payload = {"function": function, "Args": args}
        command = [
            "peer",
            "chaincode",
            "invoke",
            "-o",
            self.orderer_address,
            "--ordererTLSHostnameOverride",
            "orderer.example.com",
            "--tls",
            "--cafile",
            self.orderer_ca,
            "-C",
            self.channel_name,
            "-n",
            self.chaincode_name,
            "--peerAddresses",
            self.peer0_org1_address,
            "--tlsRootCertFiles",
            self.peer0_org1_ca,
        ]
        if include_org2:
            command.extend(
                [
                    "--peerAddresses",
                    self.peer0_org2_address,
                    "--tlsRootCertFiles",
                    self.peer0_org2_ca,
                ]
            )
        if wait_for_event:
            command.append("--waitForEvent")
        command.extend(["-c", json.dumps(payload, separators=(",", ":"))])

        result = self._run(command, cwd=self.network_dir, check=check)
        return {
            "command": result.command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "duration_ms": result.duration_ms,
            "txid": self.extract_txid(result.stdout + result.stderr),
            "payload": self.extract_payload(result.stdout + result.stderr),
        }

    def query(self, function: str, args: list[str]) -> str:
        payload = {"function": function, "Args": args}
        result = self._run(
            [
                "peer",
                "chaincode",
                "query",
                "-C",
                self.channel_name,
                "-n",
                self.chaincode_name,
                "-c",
                json.dumps(payload, separators=(",", ":")),
            ],
            cwd=self.network_dir,
        )
        return result.stdout.strip()

    def query_json(self, function: str, args: list[str]) -> Any:
        output = self.query(function, args)
        return json.loads(output) if output else None

    def get_block_height(self) -> int:
        result = self._run(
            ["peer", "channel", "getinfo", "-c", self.channel_name],
            cwd=self.network_dir,
        )
        content = result.stdout.strip()
        match = re.search(r"Blockchain info:\s*(\{.*\})", content)
        if not match:
            raise RuntimeError(f"Unable to parse block info from output: {content}")
        return int(json.loads(match.group(1))["height"])

    def measure_block_confirmation(
        self,
        function: str,
        args: list[str],
        *,
        include_org2: bool = True,
        timeout_seconds: float = 30.0,
        poll_interval: float = 0.2,
    ) -> dict[str, Any]:
        before_height = self.get_block_height()
        start = time.perf_counter()
        invoke_result = self.invoke(
            function,
            args,
            wait_for_event=False,
            include_org2=include_org2,
        )
        observed_height = before_height
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            observed_height = self.get_block_height()
            if observed_height > before_height:
                break
            time.sleep(poll_interval)
        confirmation_ms = (time.perf_counter() - start) * 1000.0
        return {
            **invoke_result,
            "pre_block_height": before_height,
            "post_block_height": observed_height,
            "block_confirmation_ms": confirmation_ms,
            "block_confirmed": observed_height > before_height,
        }

    def stop_peer(self, container_name: str | None = None) -> CommandResult:
        return self._run(
            ["docker", "stop", container_name or self.peer0_org2_container],
            cwd=self.repo_root,
            check=False,
        )

    def start_peer(self, container_name: str | None = None) -> CommandResult:
        return self._run(
            ["docker", "start", container_name or self.peer0_org2_container],
            cwd=self.repo_root,
            check=False,
        )

    def wait_for_peer(
        self,
        host: str,
        port: int,
        *,
        timeout_seconds: float = 45.0,
        poll_interval: float = 1.0,
    ) -> bool:
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(poll_interval)
                try:
                    sock.connect((host, port))
                    return True
                except OSError:
                    time.sleep(poll_interval)
        return False

    def extract_txid(self, output: str) -> str | None:
        match = TXID_PATTERN.search(output)
        return match.group(1) if match else None

    def extract_payload(self, output: str) -> Any:
        match = PAYLOAD_PATTERN.search(output)
        if not match:
            return None
        payload = match.group(1).encode("utf-8").decode("unicode_escape")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        check: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> CommandResult:
        env = self._base_env.copy()
        if extra_env:
            env.update(extra_env)

        start = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        result = CommandResult(
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            duration_ms=duration_ms,
        )
        if check and completed.returncode != 0:
            raise RuntimeError(
                "Command failed: "
                + " ".join(command)
                + f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        return result
