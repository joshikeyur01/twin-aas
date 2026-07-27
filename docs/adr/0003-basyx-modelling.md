# 3. AAS via unmodified BaSyx, JSON artefacts, REST populator

Date: 2026-07-17
Status: Accepted

## Context
The AAS side could be a Python AAS SDK, a forked server, or an unmodified
BaSyx environment fed over its public API.

## Decision
Unmodified `eclipsebasyx/aas-environment:2.0.0-milestone-13`; submodels are
generated JSON artefacts loaded at startup; dynamic values go through the
plain REST API from a Python populator. Bindings come from ur5_model.yaml,
never from the AAS JSON (which stays standards-conformant).

## Consequences
- We benchmark what a standards-compliant integrator would ship.
- Empirical API findings became data: milestone-13 rejects submodel-level
  ValueOnly PATCH (400) and native JSON numbers (500); collection-level
  PATCH with string values works (204). Two PATCHes per tick.
- Units ride as lightweight Qualifiers, not IEC 61360 data specifications —
  ceremony proportional to the question being asked (see ADR-0004).
