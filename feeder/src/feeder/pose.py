"""MQTT joints in, one retained pose out.

The feeder is the single place FK runs (fairness rule). It tracks the
latest position per joint, and a fixed-rate ticker recomputes the pose and
republishes ``twin/<asset>/pose`` — retained, so any adapter or client can
read the current answer without waiting for the next sample.

Same failure policy as the rest of the portfolio: broker loss flips
readiness and retries forever; recovery needs no manual step.
"""

from __future__ import annotations

import asyncio

import aiomqtt
import structlog
from prometheus_client import Counter
from pydantic import ValidationError

from feeder.config import FeederConfig
from feeder.kinematics import forward
from feeder.wire import (
    UR5_JOINT_NAMES,
    JointTelemetry,
    PoseMessage,
    parse_telemetry_topic,
    pose_topic,
    telemetry_wildcard,
)

log = structlog.get_logger()

MESSAGES = Counter("twin_feeder_messages_total", "Telemetry messages received from MQTT.")
REJECTED = Counter(
    "twin_feeder_rejected_total",
    "Messages dropped for failing the wire format.",
    ["reason"],  # "topic" | "joint" | "payload"
)
POSES = Counter("twin_feeder_poses_total", "Poses published (retained).")

RECONNECT_DELAY_S = 2.0


class PoseFeeder:
    """Owns the MQTT loop and reports its readiness."""

    def __init__(self, config: FeederConfig) -> None:
        self._config = config
        self._positions: dict[str, float] = {}
        self._stamp_ns = 0
        self._dirty = False
        self._connected = False

    def readiness(self) -> dict[str, bool]:
        return {"mqtt": self._connected}

    async def run(self) -> None:
        while True:
            try:
                async with aiomqtt.Client(self._config.mqtt_host, self._config.mqtt_port) as client:
                    self._connected = True
                    await client.subscribe(telemetry_wildcard(self._config.asset_name))
                    log.info("consuming", asset=self._config.asset_name)
                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._consume(client), name="consume")
                        tg.create_task(self._publish_loop(client), name="publish")
            except* aiomqtt.MqttError as group:
                self._connected = False
                reasons = "; ".join(str(exc) for exc in group.exceptions)
                log.warning("mqtt_disconnected", error=reasons, retry_in_s=RECONNECT_DELAY_S)
                await asyncio.sleep(RECONNECT_DELAY_S)

    async def _consume(self, client: aiomqtt.Client) -> None:
        async for message in client.messages:
            MESSAGES.inc()
            raw = message.payload
            if not isinstance(raw, bytes | str):
                REJECTED.labels(reason="payload").inc()
                continue
            self._observe(str(message.topic), raw)

    def _observe(self, topic: str, payload: bytes | str) -> None:
        try:
            _asset, joint, field = parse_telemetry_topic(topic)
        except ValueError:
            REJECTED.labels(reason="topic").inc()
            return
        if joint not in UR5_JOINT_NAMES:
            REJECTED.labels(reason="joint").inc()
            return
        if field != "position":
            return  # valid telemetry, but not pose input
        try:
            sample = JointTelemetry.model_validate_json(payload)
        except ValidationError:
            REJECTED.labels(reason="payload").inc()
            return
        self._positions[joint] = sample.value
        self._stamp_ns = max(self._stamp_ns, sample.stamp_ns)
        self._dirty = True

    async def _publish_loop(self, client: aiomqtt.Client) -> None:
        interval = 1.0 / self._config.pose_rate_hz
        topic = pose_topic(self._config.asset_name)
        while True:
            await asyncio.sleep(interval)
            if not self._dirty or len(self._positions) < len(UR5_JOINT_NAMES):
                continue
            self._dirty = False
            pose = forward([self._positions[name] for name in UR5_JOINT_NAMES])
            message = PoseMessage(
                x=pose.x,
                y=pose.y,
                z=pose.z,
                qx=pose.qx,
                qy=pose.qy,
                qz=pose.qz,
                qw=pose.qw,
                stamp_ns=self._stamp_ns,
            )
            # Retained: the broker hands the latest pose to any new subscriber
            # immediately — this is what makes "read the current pose" a
            # well-defined operation for the mqtt-raw baseline.
            await client.publish(topic, message.model_dump_json(), qos=0, retain=True)
            POSES.inc()
