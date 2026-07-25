"""Runtime configuration, loaded from environment variables.

Defaults match docker-compose.yml; localhost fallbacks exist so the feeder
can run outside a container against `just up` infra.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeederConfig:
    mqtt_host: str
    mqtt_port: int
    asset_name: str
    http_port: int
    pose_rate_hz: float

    @classmethod
    def from_env(cls) -> FeederConfig:
        return cls(
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
            asset_name=os.getenv("ASSET_NAME", "ur5"),
            http_port=int(os.getenv("HTTP_PORT", "8090")),
            pose_rate_hz=float(os.getenv("POSE_RATE_HZ", "50")),
        )
