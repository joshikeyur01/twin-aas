"""Deterministic sine telemetry — the reproducible benchmark source.

Publishes the twin-services contracts wire format on the joint topics at a
fixed rate, with a fixed phase pattern, so `just compare` produces the same
motion profile on every machine and no benchmark ever needs ROS or Gazebo.

Usage: uv run python scripts/synthetic.py [--duration 60] [--rate 50]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time

import aiomqtt

JOINTS = (
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
)
AMPLITUDE_RAD = 1.2
ANGULAR_FREQ = 0.8  # rad/s of the sine sweep — slow, visible motion


async def run(host: str, port: int, asset: str, rate_hz: float, duration_s: float) -> None:
    interval = 1.0 / rate_hz
    t0 = time.monotonic()
    async with aiomqtt.Client(host, port) as client:
        while (elapsed := time.monotonic() - t0) < duration_s:
            stamp_ns = time.time_ns()
            for i, joint in enumerate(JOINTS):
                position = AMPLITUDE_RAD * math.sin(ANGULAR_FREQ * elapsed + i * 0.6)
                velocity = AMPLITUDE_RAD * ANGULAR_FREQ * math.cos(ANGULAR_FREQ * elapsed + i * 0.6)
                for field, value in (("position", position), ("velocity", velocity)):
                    await client.publish(
                        f"twin/{asset}/joint/{joint}/{field}",
                        json.dumps({"value": round(value, 6), "stamp_ns": stamp_ns}),
                    )
            await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--asset", default="ur5")
    parser.add_argument("--rate", type=float, default=50.0)
    parser.add_argument("--duration", type=float, default=60.0)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.asset, args.rate, args.duration))


if __name__ == "__main__":
    main()
