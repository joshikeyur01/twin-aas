# Style

Inherits twin-services' conventions (uv workspace, mypy --strict, ruff,
health endpoints, structlog JSON, Conventional Commits with member scopes,
.python-version pinning, the iCloud chflags guard). Deltas:

- **Model-first:** ur5_model.yaml is the only hand-edited model artefact;
  `just gen-model` regenerates the rest, checked in, CI-gated.
- **Fairness rules are style rules** (AGENTS.md): frozen clients, FK only
  in the feeder, same update rate for both structured adapters, agreement
  before measurement.
- COMPARISON.md is generated output; editing it by hand is a bug.
- Empirical API findings (server quirks, spec-vs-implementation gaps) get
  recorded in the nearest module docstring and surfaced in COMPARISON.md's
  methodology.
