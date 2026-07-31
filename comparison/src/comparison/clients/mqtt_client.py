"""mqtt-raw client: read the retained pose message."""

from __future__ import annotations

import asyncio
import json

import aiomqtt


async def read_pose(host: str = "localhost", asset: str = "ur5") -> dict[str, float]:
    async with aiomqtt.Client(host) as client:
        await client.subscribe(f"twin/{asset}/pose")
        message = await asyncio.wait_for(anext(client.messages), timeout=5)
        assert isinstance(message.payload, bytes)
        pose: dict[str, float] = json.loads(message.payload)
        pose.pop("schema_version", None)
        return pose
