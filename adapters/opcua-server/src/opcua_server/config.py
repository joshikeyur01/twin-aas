"""Runtime configuration, loaded from environment variables.

Defaults match docker-compose.yml; localhost fallbacks exist so the server
can run outside a container against `just up` infra.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpcUaConfig:
    mqtt_host: str
    mqtt_port: int
    asset_name: str
    endpoint: str
    spec_path: str
    update_rate_hz: float
    http_port: int

    @classmethod
    def from_env(cls) -> OpcUaConfig:
        return cls(
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            asset_name=os.getenv("ASSET_NAME", "ur5"),
            endpoint=os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/twin/"),
            spec_path=os.getenv("SPEC_PATH", "adapters/opcua-server/spec/ur5_addressspace.json"),
            # Fairness rule (AGENTS.md): keep equal to the AAS populator's rate.
            update_rate_hz=float(os.getenv("UPDATE_RATE_HZ", "10")),
            http_port=int(os.getenv("HTTP_PORT", "8092")),
        )
