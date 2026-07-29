# 4. OPC-UA mapping and what "equivalent" means

Date: 2026-07-17
Status: Accepted

## Context
The comparison is invalid unless the three models say the same thing; but
the standards differ in what they *can* say.

## Decision
Both structured artefacts are generated from `model/ur5_model.yaml`
(divergence is a build error; tests pin exact leaf-set equality). Mapping:
submodel → object, collection → nested object, property → variable;
`int` → xs:long / Int64 (nanosecond stamps overflow 32 bits). Equivalent
means: same property tree, same values, same units, same update rate.
It does NOT mean same semantics machinery — AAS carries first-class
semanticIds; OPC-UA gets them as node Descriptions; units are a Qualifier
vs a `Unit` string property. Those asymmetries are findings the comparison
exists to surface, and the agreement gate checks values, not metadata.

## Consequences
- One YAML edit updates both models or breaks CI trying.
- The matrix's differences are attributable to the standards and their
  implementations, not to modelling drift.

## Dependency notes
`asyncua` (server+client), `httpx2` (REST), `pyyaml`+`pydantic` (modelgen),
`numpy` (vendored FK), `aiomqtt`/`fastapi`/`uvicorn`/`structlog`/
`prometheus-client` per portfolio baseline.
