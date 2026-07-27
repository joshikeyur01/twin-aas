"""Entrypoint: the populate loop and the health server as sibling tasks.

Same crash policy as the rest of the portfolio: if either task dies
unexpectedly the TaskGroup cancels the other and the process exits nonzero —
fail fast, let the container restart policy revive us.
"""

from __future__ import annotations

import asyncio
import logging

import structlog
import uvicorn

from aas_populator.config import PopulatorConfig
from aas_populator.health import build_health_app
from aas_populator.populate import Populator

log = structlog.get_logger()


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


async def main() -> None:
    configure_logging()
    config = PopulatorConfig.from_env()
    populator = Populator(config)
    app = build_health_app("aas-populator", populator.readiness)
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=config.http_port, log_level="warning")
    )
    log.info("starting", http_port=config.http_port, mqtt=config.mqtt_host, basyx=config.basyx_url)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(populator.run(), name="populate")
        tg.create_task(server.serve(), name="health")


if __name__ == "__main__":
    asyncio.run(main())
