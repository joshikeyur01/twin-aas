"""The measurements behind COMPARISON.md.

Methodology (also rendered into the report):
- Latency: wall-clock around each frozen client's read_pose(), N runs after
  warmup, connection setup included — "cold single query" is the honest
  unit for a "what is the pose right now?" question.
- Verbosity: application-payload bytes for one answered query, measured by
  independent probes so the frozen clients stay untouched. Protocol framing
  (TCP/IP, MQTT fixed headers, HTTP headers) is excluded; for OPC-UA the
  payload is the binary-encoded DataValues. Apples-to-apples enough to
  compare orders of magnitude, and stated so nobody mistakes it for pcap.
- Client LOC: non-blank, non-comment, non-docstring lines of each frozen
  client module, counted by this file.
- The agreement gate runs first: a matrix over disagreeing adapters is
  invalid by construction.
"""

from __future__ import annotations

import asyncio
import base64
import io
import statistics
import time
import tokenize
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import aiomqtt
import httpx2
from asyncua import Client, ua
from asyncua.ua.ua_binary import variant_to_binary

from comparison.clients import aas_client, mqtt_client, opcua_client

AGREEMENT_TOLERANCE_M = 0.2  # one 10 Hz update period of arm motion, generously
_SUBMODEL_ID = "https://twin-portfolio.example/submodels/operationaldata"


@dataclass(frozen=True, slots=True)
class AdapterResult:
    name: str
    p50_ms: float
    p95_ms: float
    payload_bytes: int
    client_loc: int


async def check_agreement() -> dict[str, dict[str, float]]:
    """All three answers, asserted to agree; returns them for the report."""
    mqtt, aas, opcua = await asyncio.gather(
        mqtt_client.read_pose(), aas_client.read_pose(), opcua_client.read_pose()
    )
    answers = {"mqtt-raw": mqtt, "aas": aas, "opcua": opcua}
    for axis in ("x", "y", "z"):
        values = [pose[axis] for pose in answers.values()]
        if max(values) - min(values) > AGREEMENT_TOLERANCE_M:
            raise RuntimeError(f"adapters disagree on {axis}: {values} — matrix invalid")
    return answers


async def measure_latency(name: str, runs: int, warmup: int) -> tuple[float, float]:
    readers: dict[str, Callable[[], Awaitable[dict[str, float]]]] = {
        "mqtt-raw": mqtt_client.read_pose,
        "aas": aas_client.read_pose,
        "opcua": opcua_client.read_pose,
    }
    read = readers[name]
    for _ in range(warmup):
        await read()
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        await read()
        samples.append((time.perf_counter() - start) * 1e3)
    samples.sort()
    return statistics.median(samples), samples[int(0.95 * len(samples))]


async def payload_bytes_mqtt(host: str = "localhost") -> int:
    async with aiomqtt.Client(host) as client:
        await client.subscribe("twin/ur5/pose")
        message = await asyncio.wait_for(anext(client.messages), timeout=5)
        assert isinstance(message.payload, bytes)
        return len(message.payload)


async def payload_bytes_aas(base_url: str = "http://localhost:8081") -> int:
    submodel = base64.urlsafe_b64encode(_SUBMODEL_ID.encode()).decode().rstrip("=")
    async with httpx2.AsyncClient(base_url=base_url) as client:
        response = await client.get(
            f"/submodels/{submodel}/submodel-elements/EndEffectorPose/$value"
        )
        response.raise_for_status()
        return len(response.content)


async def payload_bytes_opcua(endpoint: str = "opc.tcp://localhost:4840/twin/") -> int:
    async with Client(endpoint) as client:
        index = ua.Int16(await client.get_namespace_index(opcua_client._NAMESPACE))
        nodes = [
            client.get_node(ua.NodeId(ua.String(f"{opcua_client._BASE}.{name}"), index))
            for name in opcua_client._FIELDS
        ]
        values = await client.read_values(nodes)
    return sum(len(variant_to_binary(ua.Variant(value))) for value in values)


def client_loc(module_file: str) -> int:
    """Non-blank, non-comment, non-docstring lines."""
    source = Path(module_file).read_text()
    code_lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (
            tokenize.COMMENT,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENDMARKER,
            tokenize.ENCODING,
        ):
            continue
        if token.type == tokenize.STRING and token.start[1] == 0:
            continue  # module docstring
        code_lines.update(range(token.start[0], token.end[0] + 1))
    return len(code_lines)


async def run_benchmarks(runs: int = 100, warmup: int = 5) -> list[AdapterResult]:
    probes = {
        "mqtt-raw": payload_bytes_mqtt,
        "aas": payload_bytes_aas,
        "opcua": payload_bytes_opcua,
    }
    modules = {
        "mqtt-raw": mqtt_client.__file__,
        "aas": aas_client.__file__,
        "opcua": opcua_client.__file__,
    }
    results = []
    for name in ("mqtt-raw", "aas", "opcua"):
        p50, p95 = await measure_latency(name, runs, warmup)
        results.append(
            AdapterResult(
                name=name,
                p50_ms=round(p50, 2),
                p95_ms=round(p95, 2),
                payload_bytes=await probes[name](),
                client_loc=client_loc(modules[name]),
            )
        )
    return results
