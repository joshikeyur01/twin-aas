"""The MQTT wire formats this repo touches.

Inbound: the twin-services contracts telemetry format, vendored minimally —
just what the feeder consumes (JointTelemetry payloads on the joint topics).
Field names and topic shapes must match twin-services/contracts exactly; if
they drift, the bridge and the synthetic source stop feeding us.

Outbound: the pose message on ``twin/<asset>/pose`` — retained, so "read
the current pose" is a single well-defined operation for every adapter and
for the mqtt-raw baseline. This topic is defined here and nowhere else.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

UR5_JOINT_NAMES: tuple[str, ...] = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
)

_TELEMETRY_TOPIC = re.compile(
    r"^twin/(?P<asset>[^/]+)/joint/(?P<joint>[^/]+)"
    r"/(?P<field>position|velocity|effort)$"
)


def telemetry_wildcard(asset: str = "+") -> str:
    return f"twin/{asset}/joint/+/+"


def parse_telemetry_topic(topic: str) -> tuple[str, str, str]:
    """Split a telemetry topic into (asset, joint, field); raise on anything else."""
    match = _TELEMETRY_TOPIC.match(topic)
    if match is None:
        raise ValueError(f"not a telemetry topic: {topic!r}")
    return match["asset"], match["joint"], match["field"]


def pose_topic(asset: str) -> str:
    return f"twin/{asset}/pose"


class JointTelemetry(BaseModel):
    """The twin-services contracts wire payload (consumers ignore extras)."""

    schema_version: int = Field(default=1, ge=1)
    value: float
    stamp_ns: int = Field(..., ge=0)


class PoseMessage(BaseModel):
    """The retained pose payload — the answer every adapter re-models.

    Field names are load-bearing: the model's dynamic sources (``pose.x`` …
    ``pose.stamp_ns`` in ur5_model.yaml) resolve against this JSON.
    """

    schema_version: int = Field(default=1, ge=1)
    x: float
    y: float
    z: float
    qx: float
    qy: float
    qz: float
    qw: float
    stamp_ns: int = Field(..., ge=0)
