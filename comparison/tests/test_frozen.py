"""The freeze, enforced: client LOC values are pinned. Changing a frozen
client changes a measurement — this test makes that a conscious act that
must also update COMPARISON.md's methodology (AGENTS.md fairness rules)."""

from __future__ import annotations

from pathlib import Path

from comparison.bench import client_loc
from comparison.clients import aas_client, mqtt_client, opcua_client

FROZEN_LOC = {"mqtt-raw": 12, "aas": 16, "opcua": 22}


def test_frozen_client_loc() -> None:
    measured = {
        "mqtt-raw": client_loc(mqtt_client.__file__),
        "aas": client_loc(aas_client.__file__),
        "opcua": client_loc(opcua_client.__file__),
    }
    assert measured == FROZEN_LOC, (
        "a frozen client changed — if deliberate, update this pin AND "
        "COMPARISON.md's methodology note in the same commit"
    )


def test_loc_counter_ignores_noise(tmp_path: object) -> None:
    target = Path(str(tmp_path)) / "sample.py"
    target.write_text('"""Docstring\nspanning lines."""\n\n# comment\nx = 1\ny = 2\n')
    assert client_loc(str(target)) == 2
