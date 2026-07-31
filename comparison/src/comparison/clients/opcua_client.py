"""OPC-UA client: batch-read the EndEffectorPose variables."""

from __future__ import annotations

from asyncua import Client, ua

_NAMESPACE = "https://twin-portfolio.example/opcua"
_BASE = "UR5Twin.OperationalData.EndEffectorPose"
_FIELDS = {
    "X": "x",
    "Y": "y",
    "Z": "z",
    "Qx": "qx",
    "Qy": "qy",
    "Qz": "qz",
    "Qw": "qw",
    "StampNs": "stamp_ns",
}


async def read_pose(endpoint: str = "opc.tcp://localhost:4840/twin/") -> dict[str, float]:
    async with Client(endpoint) as client:
        index = ua.Int16(await client.get_namespace_index(_NAMESPACE))
        nodes = [
            client.get_node(ua.NodeId(ua.String(f"{_BASE}.{name}"), index)) for name in _FIELDS
        ]
        values = await client.read_values(nodes)
    return dict(zip(_FIELDS.values(), values, strict=True))
