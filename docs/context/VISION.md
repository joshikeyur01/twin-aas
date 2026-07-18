# Vision

## Why this repo exists

The digital-twin standards debate — Asset Administration Shell versus
OPC-UA versus "just use MQTT" — is conducted almost entirely in tables
copied from other people's tables. Everyone cites interoperability;
almost nobody publishes the running code behind the comparison.

This repo is the empirical version. The same UR5 twin, the same live
telemetry stream, exposed through three parallel information-model
adapters:

- **`adapters/aas-basyx/`** — an Eclipse BaSyx AAS server with submodels
  `Nameplate`, `TechnicalData`, `OperationalData`, and `Capability`,
  live-populated from MQTT.
- **`adapters/opcua/`** — an OPC-UA server (`asyncua`) exposing an
  equivalent address space.
- **`adapters/mqtt-raw/`** — the twin-hello baseline: raw topics, no
  semantic layer. The control group.

One question is asked through all three — *"what is the current
end-effector pose?"* — and a `comparison/` package measures what each
standard actually costs to answer it: query latency, payload verbosity,
and client lines of code.

This is L3 of the 5-layer stack, the layer `twin-hello` and
`twin-services` deliberately left empty. The one-sentence version:
**`twin-services` decomposed the twin; this repo makes it mean something —
three different ways, with a stopwatch running.**

## What "done" looks like

- `just up` starts the broker, the three adapters, and a telemetry source;
  all three adapters answer the pose query with live, agreeing values.
- The BaSyx AAS passes its own API for all four submodels;
  `OperationalData` visibly tracks the moving arm.
- The OPC-UA address space browses cleanly in any generic client and
  mirrors the same structure the AAS exposes — equivalence is a design
  input, not an accident.
- `just compare` runs the benchmark against all three adapters and
  regenerates **`docs/COMPARISON.md`**: a filled matrix of latency
  (p50/p95), verbosity (bytes on the wire per answered query), and client
  LOC, each number traceable to code in `comparison/`.
- The comparison is reproducible on a fresh clone: matrix numbers come
  from `just compare` output, never typed in by hand.
- ADRs record the modelling decisions someone will want to argue with —
  submodel structure, address-space mapping, and what "equivalent" means
  across the three.

## What "done" does not look like

- New services. The four `twin-services` services are not rebuilt here;
  this repo adds adapters beside the stack, not another architecture.
- Anomaly detection, ML. That's `twin-anomaly`.
- More than one robot. That's `twin-fleet`.
- A verdict pretending to be universal. The deliverable is a matrix with
  measured numbers for *this* asset and *this* question, plus honest notes
  on what would not generalise.
- Full AAS Part 2 compliance or exhaustive OPC-UA companion-spec coverage.
  Four submodels and one equivalent address space are enough to measure
  what the thesis needs measured.

## Audience

Same three people, in order:

1. **Me, six months from now**, writing the standards chapter and needing
   numbers with provenance instead of adjectives.
2. **A thesis examiner** checking whether "we compared the standards
   empirically" means benchmarks or vibes — this repo is the difference.
3. **A recruiter or PI** who reads COMPARISON.md's matrix and sees that I
   can hold three modelling ideologies in one codebase without letting any
   of them win by default.

If a change doesn't help at least one of those three, it doesn't ship.
