"""Render the model as the OPC-UA address-space spec.

The asyncua server consumes this JSON at startup and builds one object per
submodel, one nested object per collection, one variable per property.
Deterministic output, same reason as the AAS side: CI diffs it.

Equivalence note (ADR-0004): OPC-UA has no first-class semanticId slot, so
semantic references ride in each node's Description. That asymmetry is a
finding, not a bug — it is exactly the kind of difference the comparison
exists to surface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modelgen.schema import Model, Property, PropertyType, Submodel

_UA_TYPES: dict[PropertyType, str] = {
    "string": "String",
    "double": "Double",
    # Int64, not Int32: StampNs is nanoseconds since epoch (> 2^31).
    "int": "Int64",
    "boolean": "Boolean",
}


def _variable(node_prefix: str, name: str, prop: Property) -> dict[str, Any]:
    return {
        "browse_name": name,
        "node_id": f"{node_prefix}.{name}",
        "data_type": _UA_TYPES[prop.type],
        "value": prop.value,  # None for dynamic; server initialises to zero
        "unit": prop.unit,  # server attaches EUInformation when set
        "source": prop.source,  # None for static; MQTT binding otherwise
        "description": f"semantic: {prop.semantic_id}" if prop.semantic_id else None,
    }


def _object(node_prefix: str, name: str, submodel: Submodel) -> dict[str, Any]:
    node_id = f"{node_prefix}.{name}"
    nested = [
        {
            "browse_name": coll_name,
            "node_id": f"{node_id}.{coll_name}",
            "description": f"semantic: {c.semantic_id}" if c.semantic_id else None,
            "variables": [
                _variable(f"{node_id}.{coll_name}", prop_name, prop)
                for prop_name, prop in c.properties.items()
            ],
        }
        for coll_name, c in submodel.collections.items()
    ]
    return {
        "browse_name": name,
        "node_id": node_id,
        "description": f"semantic: {submodel.semantic_id}" if submodel.semantic_id else None,
        "variables": [
            _variable(node_id, prop_name, prop) for prop_name, prop in submodel.properties.items()
        ],
        "objects": nested,
    }


def generate_spec(model: Model) -> dict[str, Any]:
    root = model.asset.id_short
    return {
        "namespace_uri": "https://twin-portfolio.example/opcua",
        "root": root,
        "objects": [_object(root, name, submodel) for name, submodel in model.submodels.items()],
    }


def write_opcua(model: Model, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "ur5_addressspace.json"
    target.write_text(json.dumps(generate_spec(model), indent=2) + "\n")
    return target
