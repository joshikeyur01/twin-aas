"""Entrypoint: OPC-UA server, MQTT updater, and health server as siblings.

Same crash policy as the rest of the portfolio: if any task dies
unexpectedly the TaskGroup cancels the rest and the process exits nonzero —
fail fast, let the container restart policy revive us.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import structlog
import uvicorn
from asyncua import Server

from opcua_server.adapter import MqttUpdater
from opcua_server.config import OpcUaConfig
from opcua_server.health import build_health_app
from opcua_server.space import build_address_space, load_spec

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
    logging.getLogger("asyncua").setLevel(logging.WARNING)


async def main() -> None:
    configure_logging()
    config = OpcUaConfig.from_env()

    server = Server()
    await server.init()
    server.set_endpoint(config.endpoint)
    spec = load_spec(Path(config.spec_path))
    dynamic = await build_address_space(server, spec)

    updater = MqttUpdater(config, dynamic)
    health_app = build_health_app("opcua-server", updater.readiness)
    http_server = uvicorn.Server(
        uvicorn.Config(health_app, host="0.0.0.0", port=config.http_port, log_level="warning")
    )
    log.info(
        "starting",
        endpoint=config.endpoint,
        nodes=len(dynamic),
        http_port=config.http_port,
    )

    async with server:
        updater.mark_serving()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(updater.run(), name="updater")
            tg.create_task(http_server.serve(), name="health")


if __name__ == "__main__":
    asyncio.run(main())
