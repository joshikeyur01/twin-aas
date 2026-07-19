# 2. One feeder, one pose

Date: 2026-07-17
Status: Accepted

## Context
Every adapter must answer "current end-effector pose". FK could run in each
adapter, or once upstream.

## Decision
FK runs exactly once, in `feeder/` (kinematics vendored verbatim from
twin-services), publishing a retained `twin/ur5/pose` message all adapters
and the mqtt-raw baseline consume.

## Consequences
- The benchmark measures information-model overhead, not arithmetic; the
  adapters can only disagree about *how* they say the answer.
- Retained delivery makes "read the current pose" a well-defined one-shot
  operation for every client, including the baseline.
- The feeder is a single point of failure — acceptable: it is shared
  infrastructure for a benchmark, not a production topology.
- Verified live: three adapters agreed within one 10 Hz update period.
