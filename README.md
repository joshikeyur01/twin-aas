# twin-aas

> Three information models, one robot, a stopwatch. The same UR5 twin
> exposed through Eclipse BaSyx AAS, OPC-UA, and raw MQTT — with a
> benchmark harness that measures what each standard costs to answer one
> question. Third rung of the `twin-*` portfolio.

## What this is

An empirical standards comparison with running code. A feeder computes the
end-effector pose once (FK vendored from twin-services) and publishes it
retained on MQTT; three parallel adapters re-model it — an unmodified BaSyx
AAS environment (REST-populated), an asyncua OPC-UA server, and the raw
topics themselves as the control group. `just compare` asks all three
"what is the current pose?", checks they agree, and regenerates
[docs/COMPARISON.md](docs/COMPARISON.md) with measured latency, payload
bytes, and frozen-client LOC. Numbers without provenance are adjectives.

## Quick start

Prerequisites: Docker, `just`, `uv`. No ROS needed.

```bash
just up                      # broker, BaSyx, feeder, populator, OPC-UA server
just healthz                 # all green
uv run python scripts/synthetic.py --duration 60 &   # deterministic motion
just compare                 # agreement gate + benchmarks -> docs/COMPARISON.md
just ui                      # optional BaSyx web UI on :8082
```

## Repo layout

```
model/            # ur5_model.yaml (THE property tree) + generators
deploy/basyx/     # generated AAS environment (checked in, CI-gated)
adapters/         # aas-populator, opcua-server (+ generated spec), mqtt-raw = the broker
feeder/           # MQTT joints -> FK -> retained pose (the only FK)
comparison/       # three frozen clients + benchmark runner
docs/adr/         # decisions, incl. empirical BaSyx API findings
docs/COMPARISON.md  # the deliverable — regenerated, never hand-edited
```

## Licence

Apache-2.0 — see [LICENSE](LICENSE).
