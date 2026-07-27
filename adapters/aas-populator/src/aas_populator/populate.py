"""MQTT in, one ValueOnly PATCH per tick out.

The binding (which topic feeds which submodel element) comes from
ur5_model.yaml via modelgen — NOT from the AAS JSON, which deliberately
stays a standards-conformant artefact with no implementation details.
At init the sources are compiled into a plain topic→source table, so the
hot path is dictionary lookups, no parsing.

BaSyx being down degrades readiness and skips ticks; it never kills the
loop (same degradation philosophy as the whole portfolio).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiomqtt
import httpx2
import structlog
from prometheus_client import Counter

from aas_populator.basyx import BasyxClient
from aas_populator.config import PopulatorConfig
from modelgen import Model, load_model
from modelgen.aas import submodel_id

log = structlog.get_logger()

MESSAGES = Counter("twin_populator_messages_total", "MQTT messages consumed.")
UPDATES = Counter("twin_populator_updates_total", "ValueOnly PATCHes accepted by BaSyx.")
PATCH_FAILURES = Counter("twin_populator_patch_failures_total", "PATCHes refused or failed.")

RECONNECT_DELAY_S = 2.0

_COERCE = {"double": float, "int": int, "boolean": bool, "string": str}


class Populator:
    """Owns the MQTT→BaSyx pipeline and reports its readiness."""

    def __init__(self, config: PopulatorConfig, model: Model | None = None) -> None:
        self._config = config
        model = model or load_model()

        # {submodel: {collection: {property: (source, coerce)}}} for dynamic submodels
        self._bindings: dict[str, dict[str, dict[str, tuple[str, Any]]]] = {}
        # topic → source, compiled once; the consume loop only does lookups
        self._topic_to_source: dict[str, str] = {}
        self._submodel_ids: dict[str, str] = {}
        pose = f"twin/{config.asset_name}/pose"
        for name, submodel in model.submodels.items():
            if submodel.kind != "dynamic":
                continue
            self._submodel_ids[name] = submodel_id(model, name)
            colls: dict[str, dict[str, tuple[str, Any]]] = {}
            for path, prop in submodel.leaves():
                assert prop.source is not None  # schema guarantees it for dynamic
                coll, _, leaf = path.rpartition(".")
                colls.setdefault(coll, {})[leaf] = (prop.source, _COERCE[prop.type])
                if prop.source.startswith("pose."):
                    self._topic_to_source[pose] = "pose"  # whole message binds
                else:
                    _, joint, field = prop.source.split(".")
                    topic = f"twin/{config.asset_name}/joint/{joint}/{field}"
                    self._topic_to_source[topic] = prop.source
            self._bindings[name] = colls

        self._values: dict[str, float | int | str | bool] = {}
        self._dirty = False
        self._mqtt_connected = False
        self._basyx_ok = False

    def readiness(self) -> dict[str, bool]:
        return {"mqtt": self._mqtt_connected, "basyx": self._basyx_ok}

    def collection_docs(self, submodel: str) -> dict[str, dict[str, str]] | None:
        """Per-collection ValueOnly documents for one submodel, or None until
        every bound source has reported at least once.

        Values are string-serialised: BaSyx milestone-13 rejects native JSON
        numbers (see basyx.py's empirical API notes).
        """
        docs: dict[str, dict[str, str]] = {}
        for coll, props in self._bindings[submodel].items():
            for leaf, (source, coerce) in props.items():
                if source not in self._values:
                    return None
                typed = coerce(self._values[source])
                text = ("true" if typed else "false") if isinstance(typed, bool) else str(typed)
                docs.setdefault(coll, {})[leaf] = text
        return docs

    async def run(self) -> None:
        clients = {
            name: BasyxClient(self._config.basyx_url, sm_id)
            for name, sm_id in self._submodel_ids.items()
        }
        try:
            while True:
                try:
                    async with aiomqtt.Client(
                        self._config.mqtt_host, self._config.mqtt_port
                    ) as mqtt:
                        self._mqtt_connected = True
                        for topic in self._topic_to_source:
                            await mqtt.subscribe(topic)
                        log.info("consuming", topics=len(self._topic_to_source))
                        async with asyncio.TaskGroup() as tg:
                            tg.create_task(self._consume(mqtt), name="consume")
                            tg.create_task(self._patch_loop(clients), name="patch")
                except* aiomqtt.MqttError as group:
                    self._mqtt_connected = False
                    reasons = "; ".join(str(e) for e in group.exceptions)
                    log.warning("mqtt_disconnected", error=reasons, retry_in_s=RECONNECT_DELAY_S)
                    await asyncio.sleep(RECONNECT_DELAY_S)
        finally:
            for client in clients.values():
                await client.aclose()

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
                    self._values[f"pose.{key}"] = value
            else:
                self._values[source] = payload["value"]
            self._dirty = True

    async def _patch_loop(self, clients: dict[str, BasyxClient]) -> None:
        interval = 1.0 / self._config.update_rate_hz
        while True:
            await asyncio.sleep(interval)
            if not self._dirty:
                continue
            self._dirty = False
            for name, client in clients.items():
                docs = self.collection_docs(name)
                if docs is None:
                    continue
                try:
                    for coll, values in docs.items():
                        await client.patch_collection(coll, values)
                    self._basyx_ok = True
                    UPDATES.inc()
                except httpx2.HTTPError as exc:
                    self._basyx_ok = False
                    PATCH_FAILURES.inc()
                    log.warning("basyx_patch_failed", submodel=name, error=str(exc))
