"""Runtime configuration, loaded from environment variables.

Defaults match docker-compose.yml; localhost fallbacks exist so the
populator can run outside a container against `just up` infra.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PopulatorConfig:
    mqtt_host: str
    mqtt_port: int
    asset_name: str
    basyx_url: str
    update_rate_hz: float
    http_port: int

    @classmethod
    def from_env(cls) -> PopulatorConfig:
        return cls(
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            asset_name=os.getenv("ASSET_NAME", "ur5"),
            basyx_url=os.getenv("BASYX_URL", "http://localhost:8081"),
            # Fairness rule (AGENTS.md): keep equal to the OPC-UA server's rate.
            update_rate_hz=float(os.getenv("UPDATE_RATE_HZ", "10")),
            http_port=int(os.getenv("HTTP_PORT", "8091")),
        )
