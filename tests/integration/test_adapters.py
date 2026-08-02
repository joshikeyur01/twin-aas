"""End-to-end against the running compose stack (`just up`). Marked slow;
skips itself when the stack is down."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

import pytest

from comparison.bench import check_agreement

pytestmark = pytest.mark.slow

PORTS = {"feeder": 8090, "aas-populator": 8091, "opcua-server": 8092}


def _up() -> bool:
    try:
        for port in PORTS.values():
            with urllib.request.urlopen(f"http://localhost:{port}/healthz/live", timeout=2):
                pass
        with urllib.request.urlopen("http://localhost:8081/shells", timeout=2):
            pass
        return True
    except (urllib.error.URLError, OSError):
        return False


@pytest.fixture(autouse=True, scope="module")
def require_stack() -> None:
    if not _up():
        pytest.skip("compose stack not running — `just up` first")


def test_basyx_serves_all_four_submodels() -> None:
    with urllib.request.urlopen("http://localhost:8081/submodels", timeout=3) as response:
        submodels = {s["idShort"] for s in json.load(response)["result"]}
    assert submodels == {"Nameplate", "TechnicalData", "OperationalData", "Capability"}


async def test_three_adapters_agree() -> None:
    answers = await asyncio.wait_for(check_agreement(), timeout=30)
    assert set(answers) == {"mqtt-raw", "aas", "opcua"}
