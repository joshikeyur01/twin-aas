# Roadmap

Six phases, two weeks. Same rule as the rest of the portfolio: if a phase
slips more than two days, cut scope inside the phase — do not push the next
phase. The filled COMPARISON.md matrix is the deliverable; everything else
is negotiable.

## Phase 0 · Scaffold (days 1–2)

- [ ] Repo skeleton, licence, `.gitignore`, pre-commit, CI, `.python-version`.
- [ ] `pyproject.toml` as a uv workspace: `model` (generators), `feeder`,
      `adapters/aas-populator`, `adapters/opcua-server`, `comparison`.
- [ ] `docker-compose.yml`: Mosquitto (conventions from `twin-services`,
      no `container_name`), BaSyx `aas-environment` booting empty, stubs
      answering `/healthz/ready`.
- [ ] `justfile`: `up`, `down`, `healthz`, `lint`, `typecheck`, `test`,
      `gen-model`, `compare`.

**DoD:** `just up && just healthz` green on a fresh clone.

## Phase 1 · One model, two generated artefacts (day 3)

- [ ] `model/ur5_model.yaml`: the property tree once — submodel structure,
      property names, types, units, semantic IDs.
- [ ] Generator → BaSyx submodel JSON (`deploy/basyx/`); generator →
      OPC-UA address-space spec consumed by the server.
- [ ] Equivalence tests: both artefacts contain exactly the model's
      properties, no more, no fewer. CI fails on stale generated files
      (same discipline as `twin-services` proto stubs).

**DoD:** `just gen-model` is deterministic; deleting a YAML property breaks
both artefacts' tests.

## Phase 2 · Feeder + synthetic source (day 4)

- [ ] `feeder/`: subscribes `twin/ur5/joint/#` (contracts wire format),
      computes FK (vendored from `twin-services`), publishes retained JSON
      pose to `twin/ur5/pose`. `/healthz` + `/metrics` per portfolio
      convention.
- [ ] `scripts/synthetic.py`: deterministic sine telemetry — the
      reproducible benchmark source; ROS/Gazebo never required for the
      matrix.

**DoD:** `mosquitto_sub -t twin/ur5/pose` shows live pose; a fresh
subscriber gets the retained value immediately.

## Phase 3 · AAS adapter (days 5–7)

- [ ] BaSyx environment loads the four generated submodels at startup.
- [ ] `aas-populator/`: MQTT → BaSyx REST PATCH for `OperationalData`
      (joints + pose), throttled to a configured update rate.
- [ ] Optional `--profile ui`: BaSyx web UI for eyeballing submodels.

**DoD:** `curl` against the BaSyx API returns a pose equal to the feeder's
retained value (within one update period), for all four submodels present.

## Phase 4 · OPC-UA adapter (days 8–9)

- [ ] `opcua-server/`: asyncua server builds its address space from the
      generated spec, subscribes MQTT, updates variables in place.
- [ ] Values agree with the AAS within one update period (scripted check,
      not eyeballs).

**DoD:** a generic OPC-UA client reads the pose variables; the agreement
check passes while the arm moves.

## Phase 5 · Comparison (days 10–12)

- [ ] Three minimal clients in `comparison/clients/` — written for
      idiomatic clarity, then frozen: their LOC is a measurement.
- [ ] Benchmark runner: warmup + N queries per adapter; latency p50/p95;
      bytes-on-the-wire per answered query (measured, not estimated);
      client LOC (counted by script).
- [ ] Cross-adapter agreement check runs before benchmarking; a matrix
      over disagreeing adapters is invalid by construction.
- [ ] `just compare` regenerates `docs/COMPARISON.md` — matrix plus
      methodology notes and honest non-generalisation caveats.

**DoD:** fresh clone → `just up && just compare` → COMPARISON.md filled
with real numbers, no hand edits, agreement check green in the output.

## Explicit non-goals for this repo

- Write paths through any adapter. Read-only views, by design.
- AAS registry/discovery infrastructure, companion-spec completeness,
  historical access. Noted as future work where relevant.
- Anomaly detection (`twin-anomaly`), multi-robot (`twin-fleet`),
  orbital anything (`twin-cubesat`).
