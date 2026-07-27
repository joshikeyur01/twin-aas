"""Value-only PATCH client for an unmodified BaSyx AAS environment.

Empirical API notes (BaSyx 2.0.0-milestone-13, probed 2026-07-17, recorded
in COMPARISON.md's methodology):

- Submodel-level ``PATCH /submodels/<id>/$value`` → 400. Unsupported.
- Element values must be JSON **strings** ("0.5"); native numbers → 500.
- Collection-level ``PATCH .../submodel-elements/<path>/$value`` → 204. ✓

So the update unit is one PATCH per collection per tick — still the plain
REST surface any integrator gets, no BaSyx extensions (fairness rule).
"""

from __future__ import annotations

import base64
from typing import Any

import httpx2
import structlog

log = structlog.get_logger()


def _b64url(identifier: str) -> str:
    """AAS Part 2 identifier encoding: base64url without padding."""
    return base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")


class BasyxClient:
    def __init__(self, base_url: str, submodel_id: str) -> None:
        self._client = httpx2.AsyncClient(base_url=base_url, timeout=5.0)
        self._elements_path = f"/submodels/{_b64url(submodel_id)}/submodel-elements"
        self._meta_path = f"/submodels/{_b64url(submodel_id)}"

    async def is_up(self) -> bool:
        """True when BaSyx serves the submodel we intend to patch."""
        try:
            response = await self._client.get(self._meta_path)
        except httpx2.HTTPError:
            return False
        return response.status_code == httpx2.codes.OK

    async def patch_collection(self, id_short_path: str, values: dict[str, Any]) -> None:
        """Push one collection's ValueOnly document (string-serialised values);
        raises on any non-2xx answer."""
        response = await self._client.patch(
            f"{self._elements_path}/{id_short_path}/$value", json=values
        )
        response.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()
