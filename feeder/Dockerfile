# Build context is the repo root (see docker-compose.yml). Template:
# twin-services' service Dockerfiles, adapted to this workspace's members.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Manifests first: dependency layers survive source-only changes. uv needs
# every workspace member's pyproject present to resolve, so copy them all.
COPY pyproject.toml uv.lock .python-version ./
COPY model/pyproject.toml model/
COPY feeder/pyproject.toml feeder/
COPY adapters/aas-populator/pyproject.toml adapters/aas-populator/
COPY adapters/opcua-server/pyproject.toml adapters/opcua-server/
COPY comparison/pyproject.toml comparison/

RUN uv sync --frozen --no-dev --no-install-workspace --package feeder

# Now the source that actually changes.
COPY feeder/ feeder/

RUN uv sync --frozen --no-dev --package feeder

RUN useradd --create-home --uid 10001 svc
USER svc

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8090
CMD ["python", "-m", "feeder.main"]
