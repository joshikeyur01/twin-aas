"""MQTT in, address-space variable writes out.

Same shape as the AAS populator on purpose (fairness rule: same update
rate, same buffering): values accumulate from MQTT, a fixed-rate ticker
writes changed nodes. The topic bindings come from the generated spec's
``source`` fields — the same strings the populator resolves via the model.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiomqtt
import structlog
from asyncua import ua
from prometheus_client import Counter

from opcua_server.config import OpcUaConfig
from opcua_server.space import DynamicNodes

log = structlog.get_logger()

MESSAGES = Counter("twin_opcua_messages_total", "MQTT messages consumed.")
WRITES = Counter("twin_opcua_writes_total", "Variable writes applied.")

RECONNECT_DELAY_S = 2.0


class MqttUpdater:
    """Owns the MQTT→address-space pipeline and reports its readiness."""

    def __init__(self, config: OpcUaConfig, dynamic: DynamicNodes) -> None:
        self._config = config
        self._dynamic = dynamic
        # topic → source, compiled once (same pattern as the populator)
        self._topic_to_source: dict[str, str] = {}
        pose_topic = f"twin/{config.asset_name}/pose"
        for source in dynamic:
            if source.startswith("pose."):
                self._topic_to_source[pose_topic] = "pose"
            else:
                _, joint, field = source.split(".")
                topic = f"twin/{config.asset_name}/joint/{joint}/{field}"
                self._topic_to_source[topic] = source
        self._pending: dict[str, Any] = {}
        self._mqtt_connected = False
        self._serving = False

    def readiness(self) -> dict[str, bool]:
        return {"mqtt": self._mqtt_connected, "opcua": self._serving}

    def mark_serving(self) -> None:
        self._serving = True

    async def run(self) -> None:
        while True:
            try:
                async with aiomqtt.Client(self._config.mqtt_host, self._config.mqtt_port) as mqtt:
                    self._mqtt_connected = True
                    for topic in self._topic_to_source:
                        await mqtt.subscribe(topic)
                    log.info("consuming", topics=len(self._topic_to_source))
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._consume(mqtt), name="consume")
                        tg.create_task(self._write_loop(), name="write")
            except* aiomqtt.MqttError as group:
                self._mqtt_connected = False
                reasons = "; ".join(str(e) for e in group.exceptions)
                log.warning("mqtt_disconnected", error=reasons, retry_in_s=RECONNECT_DELAY_S)
                await asyncio.sleep(RECONNECT_DELAY_S)

    async def _consume(self, mqtt: aiomqtt.Client) -> None:
        async for message in mqtt.messages:
            MESSAGES.inc()
            raw = message.payload
            if not isinstance(raw, bytes | str):
                continue
            source = self._topic_to_source.get(str(message.topic))
            if source is None:
                continue
            try:
                payload = json.loads(raw)
            except ValueError:
                continue
            if source == "pose":
                for key, value in payload.items():
                    if f"pose.{key}" in self._dynamic:
                        self._pending[f"pose.{key}"] = value
            else:
                self._pending[source] = payload["value"]

    async def _write_loop(self) -> None:
        interval = 1.0 / self._config.update_rate_hz
        while True:
            await asyncio.sleep(interval)
            if not self._pending:
                continue
            batch, self._pending = self._pending, {}
            for source, value in batch.items():
                node, variant, coerce = self._dynamic[source]
                await node.write_value(ua.DataValue(ua.Variant(coerce(value), variant)))
                WRITES.inc()
