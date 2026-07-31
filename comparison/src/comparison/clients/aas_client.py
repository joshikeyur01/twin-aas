"""AAS client: read EndEffectorPose from the BaSyx submodel API."""

from __future__ import annotations

import base64

import httpx2

_SUBMODEL_ID = "https://twin-portfolio.example/submodels/operationaldata"
_FIELDS = {"X": "x", "Y": "y", "Z": "z", "Qx": "qx", "Qy": "qy", "Qz": "qz", "Qw": "qw"}


async def read_pose(base_url: str = "http://localhost:8081") -> dict[str, float]:
    submodel = base64.urlsafe_b64encode(_SUBMODEL_ID.encode()).decode().rstrip("=")
    async with httpx2.AsyncClient(base_url=base_url) as client:
        response = await client.get(
            f"/submodels/{submodel}/submodel-elements/EndEffectorPose/$value"
        )
        response.raise_for_status()
        values = response.json()
    pose = {ours: float(values[theirs]) for theirs, ours in _FIELDS.items()}
    pose["stamp_ns"] = int(values["StampNs"])
    return pose
