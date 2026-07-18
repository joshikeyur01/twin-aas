# Project context & conventions

Read this before touching code. It sets the architecture, conventions, and
guardrails for any work in this repository.

## Mission

The empirical standards comparison: one UR5 twin exposed through three
parallel information-model adapters — Eclipse BaSyx AAS, OPC-UA
(`asyncua`), and raw MQTT — with a benchmark harness that answers "what is
the current end-effector pose?" through each and measures latency,
verbosity, and client LOC.

Success criterion: `just up && just compare` on a fresh clone regenerates
`docs/COMPARISON.md` with real numbers and a green cross-adapter agreement
check. The matrix is the thesis artefact.

## Stack

Python 3.12 · Eclipse BaSyx (`aas-environment` container, REST API) ·
`asyncua` · Mosquitto (MQTT) · Docker Compose · `uv` workspace · `just` ·
contracts wire format inherited from `twin-services`.

## Non-negotiable conventions

- Type hints everywhere; `mypy --strict` passes. `ruff` for lint/format.
- **Model-first:** `model/ur5_model.yaml` is the single source of the
  property tree. The BaSyx submodel JSON and the OPC-UA address-space spec
  are generated from it (`just gen-model`), checked in, and CI-gated for
  staleness. Hand-editing a generated artefact is a bug even if it works.
- MQTT payloads crossing this repo's boundary use the `twin-services`
  contracts wire format; the pose topic (`twin/ur5/pose`, retained) is
  defined once in the feeder and documented in `docs/`.
- Every long-running Python process exposes `/healthz/live`,
  `/healthz/ready`, and `/metrics` (portfolio convention, ADR-0004 in
  `twin-services`).
- Conventional Commits, scope = member: `feat(feeder):`, `fix(opcua):`.
- No new runtime dependency without an ADR note.
- `.python-version` pins 3.12. Run `chflags -R nohidden .venv` after any
  sync (iCloud gotcha; the justfile recipes do it for you).

## Fairness rules (the ones that make the thesis defensible)

The comparison is the product. Anything that quietly favours one adapter
invalidates it:

- **FK runs only in the feeder.** No adapter computes, caches, or
  interpolates pose on its own; adapters transport and model, nothing else.
- **BaSyx stays unmodified.** Configuration and REST only — we benchmark
  what a standards-compliant integrator would ship, not a tuned fork.
- **Frozen clients.** Once Phase 5 freezes `comparison/clients/`, they are
  measurements, not code to improve. Optimising a client after freezing is
  data tampering; if a client is unidiomatic, fix it *before* the freeze
  and note the change in COMPARISON.md's methodology section.
- **Same update rate everywhere.** The populator and the OPC-UA server use
  the same configured refresh; a faster adapter must be faster by design,
  not by config skew.
- **Agreement before measurement.** The benchmark aborts if the three
  adapters disagree about the pose beyond one update period's tolerance.

## When you touch code

1. Read the ADRs, especially the equivalence definition (ADR-0004).
2. Model changes land in `ur5_model.yaml` + regenerated artefacts first,
   adapters second — never the reverse.
3. Update tests in the same commit; keep functions under ~40 lines and
   modules under ~200.
4. New public surface (topic, REST path, node id, config key) gets
   documented in `docs/`.

## What to refuse

- A fourth adapter (FIWARE, DTDL, ...). Tempting, out of scope; note it in
  COMPARISON.md future work instead.
- Write paths through any adapter — read-only views, by design.
- Editing generated artefacts by hand, editing frozen clients, or letting
  any adapter bypass the feeder.
- Rebuilding twin-services machinery here (Grafana, InfluxDB, command
  path). This repo answers one question three ways; it does not run a
  fleet of dashboards to do it.

This repo exists to be argued with. Keep it small enough to re-run.
