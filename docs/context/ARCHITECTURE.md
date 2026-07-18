# Architecture

## The 5-layer stack

Same vocabulary as every `twin-*` repo. This repo's contribution is L3 —
three parallel information models over one telemetry stream — plus the
comparison harness that judges them.

```
┌─────────────────────────────────────────────────────────────────────┐
│ L5  Application         comparison harness · BaSyx web UI (optional)│
├─────────────────────────────────────────────────────────────────────┤
│ L3  Information model   AAS (BaSyx) ─┬─ OPC-UA (asyncua) ─┬─ raw MQTT│
│                                      │ (parallel adapters)│         │
├─────────────────────────────────────────────────────────────────────┤
│ L4  Services            feeder (pose derivation — the one survivor) │
├─────────────────────────────────────────────────────────────────────┤
│ L2  Transport           MQTT (Mosquitto), BaSyx REST, OPC-UA TCP    │
├─────────────────────────────────────────────────────────────────────┤
│ L1  Physical asset      UR5 (Gazebo via bridge, or synthetic source)│
└─────────────────────────────────────────────────────────────────────┘
```

L3 and L4 are drawn out of order above because that is the truth of this
repo: the adapters (L3) sit *on top of* one thin derived-state feeder (L4),
and everything else from `twin-services` stays out.

## Components

```
                       ┌───────────────┐   ┌──────────────┐   ┌──────────────┐
   comparison/  ──────▶│ BaSyx AAS env │   │ OPC-UA server│   │ raw MQTT     │
   (one question,      │ (Java, REST)  │   │ (asyncua)    │   │ (the broker) │
    three clients)     └──────▲────────┘   └──────▲───────┘   └──────▲───────┘
                              │ REST PATCH        │ MQTT sub         │
                       ┌──────┴────────┐          │                  │
                       │ aas populator │──────────┘   MQTT sub       │
                       │ (Python)      │◀────────────────────────────┤
                       └───────────────┘                             │
                                     twin/ur5/pose (retained) + joints
                       ┌──────────────────────────────────────────────┐
                       │                Mosquitto                     │
                       └──────▲───────────────────────────────▲───────┘
                              │ twin/ur5/pose                 │ twin/ur5/joint/#
                       ┌──────┴────────┐               ┌──────┴───────┐
                       │    feeder     │◀──────────────│ telemetry src│
                       │ (joints→FK)   │  twin/ur5/joint/#  (sim+bridge
                       └───────────────┘                or synthetic) │
                                                       └──────────────┘
```

## Data flows

1. A telemetry source publishes the contracts wire format on
   `twin/ur5/joint/<joint>/<field>` — the real sim+bridge from
   `twin-services`, or `scripts/synthetic.py` (the default for benchmarks:
   reproducible motion, no ROS needed).
2. **feeder** subscribes to joint telemetry, computes forward kinematics
   (vendored from `twin-services`), and publishes one JSON pose to
   `twin/ur5/pose` — **retained**, so "read the current pose" is a
   well-defined operation for every consumer.
3. The three adapters expose that same truth, each in its own idiom:
   - **aas-basyx** — an unmodified `eclipsebasyx/aas-environment` container
     serves the AAS. Static submodels (`Nameplate`, `TechnicalData`,
     `Capability`) load from JSON at startup; a Python **populator**
     subscribes to MQTT and PATCHes `OperationalData` values (joints +
     end-effector pose) over the BaSyx REST API.
   - **opcua** — an `asyncua` server subscribes to MQTT directly and
     mirrors the identical structure as an address space: one object per
     submodel, one variable per property.
   - **mqtt-raw** — no process at all. The baseline *is* the broker's
     topics; its "adapter" is purely the client-side access pattern.
4. **comparison/** asks each adapter the same question — current
   end-effector pose — via BaSyx REST (HTTP+JSON), OPC-UA read (binary
   TCP), and MQTT retained-message read, measuring latency, bytes on the
   wire, and client LOC. `just compare` regenerates `docs/COMPARISON.md`.

## Equivalence discipline

The comparison is only meaningful if the three models say the same thing.
One YAML file (`model/ur5_model.yaml`) defines the property tree once —
names, types, units, semantic IDs — and both the AAS submodel JSON and the
OPC-UA address space are generated from it. Divergence becomes a build
error, not a discovered embarrassment. (ADR-0004 defines what "equivalent"
does and does not mean across the three.)

## Ports

| Component        | Port | Protocol |
| ---------------- | ---- | -------- |
| Mosquitto        | 1883 | MQTT     |
| BaSyx AAS env    | 8081 | HTTP (AAS REST API) |
| BaSyx web UI     | 8082 | HTTP (optional, `--profile ui`) |
| OPC-UA server    | 4840 | opc.tcp  |
| OPC-UA server    | 8092 | HTTP (healthz/metrics) |
| feeder           | 8090 | HTTP (healthz/metrics) |
| aas populator    | 8091 | HTTP (healthz/metrics) |

## Design decisions (summaries — the ADRs argue them)

### One feeder, one pose — [ADR-0002](../adr/0002-single-feeder.md)

FK runs exactly once, upstream of all three adapters. The benchmark then
measures *information-model overhead*, not arithmetic; and the adapters can
never disagree about the answer, only about how expensively they say it.

### AAS via unmodified BaSyx + REST populator — [ADR-0003](../adr/0003-basyx-modelling.md)

No BaSyx forks, no Java code, no Python AAS SDK: submodels are JSON
artefacts, dynamic values go through the same REST API any client would
use. What we benchmark is what a standards-compliant integrator would ship.

### OPC-UA mapping and the meaning of "equivalent" — [ADR-0004](../adr/0004-opcua-mapping-and-equivalence.md)

Generated from the same model file as the AAS; equivalence means same
property tree, same values, same units — not same semantics registry, which
is precisely one of the measured differences.

## What this repo intentionally omits

- **Write paths.** All three models are read-only views; commanding the
  robot stays `twin-services`' job. Modelling writable operations is noted
  as future work in COMPARISON.md.
- **AAS registry / discovery.** One asset, one shell; registry
  infrastructure would add containers without adding evidence.
- **History.** Every model answers "now" only. Time series stay in
  InfluxDB, one repo back.
- **Auth on any adapter.** Localhost scope, same rationale as the rest of
  the portfolio.
