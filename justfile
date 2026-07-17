# twin-aas task runner. `just` for a listing.

set shell := ["bash", "-euo", "pipefail", "-c"]

# ─── setup ─────────────────────────────────────────────────────────────────

# Install dev dependencies for the whole workspace with uv.
install:
    uv sync --all-groups --all-packages
    # iCloud's fileproviderd asynchronously sets the macOS hidden flag on
    # dot-dirs; Python >= 3.12 skips hidden .pth files, silently breaking
    # editable installs (setuptools#4595). Clearing is idempotent.
    chflags -R nohidden .venv 2>/dev/null || true

# Regenerate the AAS submodels + OPC-UA spec from model/ur5_model.yaml
# (checked in — commit the diff).
gen-model: _unhide
    uv run python -m modelgen

# ─── quality gates ─────────────────────────────────────────────────────────

# iCloud re-hides .pth files after every sync (see install); run before any
# uv-run recipe so editable imports never silently vanish.
_unhide:
    @chflags -R nohidden .venv 2>/dev/null || true

lint: _unhide
    uv run ruff check .
    uv run ruff format --check .

format: _unhide
    uv run ruff format .
    uv run ruff check --fix .

typecheck: _unhide
    uv run mypy model feeder adapters comparison

test: _unhide
    uv run pytest -m "not slow and not bench"

check: lint typecheck test

# ─── stack ─────────────────────────────────────────────────────────────────

up:
    docker compose up -d --build
    @echo "BaSyx AAS API: http://localhost:8081"
    @echo "OPC-UA:        opc.tcp://localhost:4840"
    @echo "MQTT:          localhost:1883"

down:
    docker compose down

# Optional BaSyx web UI for eyeballing submodels (not part of any benchmark).
ui:
    docker compose --profile ui up -d aas-web-ui
    @echo "BaSyx web UI:  http://localhost:8082"

logs svc="":
    docker compose logs -f {{svc}}

# ─── health ────────────────────────────────────────────────────────────────

_check name url:
    @curl -sf {{url}} >/dev/null && echo "{{name}} ✓" || echo "{{name}} ✗"

# Smoke check: infra and all adapters answer.
healthz:
    @just _check basyx     http://localhost:8081/shells
    @just _check feeder    http://localhost:8090/healthz/ready
    @just _check populator http://localhost:8091/healthz/ready
    @just _check opcua     http://localhost:8092/healthz/ready
    @docker compose exec -T mosquitto mosquitto_sub -t '$SYS/broker/uptime' -C 1 -W 2 >/dev/null 2>&1 \
        && echo "mqtt ✓" || echo "mqtt ✗"

# ─── telemetry + benchmark ─────────────────────────────────────────────────

# Deterministic sine telemetry — the reproducible benchmark source (no ROS).
synthetic: _unhide
    uv run python scripts/synthetic.py

# Run the cross-adapter agreement check + benchmarks; regenerate
# docs/COMPARISON.md. The matrix is never edited by hand.
compare: _unhide
    uv run python -m comparison --output docs/COMPARISON.md
