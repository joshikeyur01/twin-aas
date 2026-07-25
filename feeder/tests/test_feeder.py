"""Feeder unit tests — no broker."""

from __future__ import annotations

import pytest

from feeder.config import FeederConfig
from feeder.kinematics import forward
from feeder.pose import PoseFeeder
from feeder.wire import UR5_JOINT_NAMES, PoseMessage, parse_telemetry_topic


def _feeder() -> PoseFeeder:
    return PoseFeeder(FeederConfig.from_env())


def test_zero_pose_matches_closed_form() -> None:
    pose = forward([0.0] * 6)
    assert pose.x == pytest.approx(-0.81725)
    assert pose.y == pytest.approx(-0.19145)


def test_observe_gates_on_all_six_joints() -> None:
    feeder = _feeder()
    for i, joint in enumerate(UR5_JOINT_NAMES[:5]):
        feeder._observe(f"twin/ur5/joint/{joint}/position", f'{{"value": 0.0, "stamp_ns": {i}}}')
    assert len(feeder._positions) == 5  # publish loop would skip
    feeder._observe(
        f"twin/ur5/joint/{UR5_JOINT_NAMES[5]}/position", '{"value": 0.0, "stamp_ns": 9}'
    )
    assert len(feeder._positions) == 6 and feeder._stamp_ns == 9


def test_velocity_and_unknown_joint_are_not_pose_input() -> None:
    feeder = _feeder()
    feeder._observe("twin/ur5/joint/elbow_joint/velocity", '{"value": 1.0, "stamp_ns": 1}')
    feeder._observe("twin/ur5/joint/phantom/position", '{"value": 1.0, "stamp_ns": 1}')
    assert feeder._positions == {}


def test_pose_message_field_names_are_load_bearing() -> None:
    # ur5_model.yaml sources (pose.x ... pose.stamp_ns) resolve against these.
    fields = set(PoseMessage.model_fields)
    assert fields == {"schema_version", "x", "y", "z", "qx", "qy", "qz", "qw", "stamp_ns"}


def test_topic_parse_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_telemetry_topic("twin/ur5/pose")
