"""Build the asyncua address space from the generated spec.

The spec (adapters/opcua-server/spec/ur5_addressspace.json) is produced by
`just gen-model` from the same YAML as the AAS submodels — this module only
instantiates it: one object per submodel, one nested object per collection,
one variable per property. String NodeIds come from the spec verbatim, so
clients can address e.g. ``UR5Twin.OperationalData.EndEffectorPose.X``.

Equivalence notes (ADR-0004): semantic references ride in node Descriptions
(OPC-UA has no first-class semanticId), and units ride as a plain ``Unit``
string property — deliberately symmetric with the AAS side's lightweight
Qualifier, so neither model pays more ceremony than the other.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from asyncua import Node, Server, ua

_VARIANTS: dict[str, ua.VariantType] = {
    "String": ua.VariantType.String,
    "Double": ua.VariantType.Double,
    "Int64": ua.VariantType.Int64,
    "Boolean": ua.VariantType.Boolean,
}

_INITIAL: dict[str, Any] = {"String": "", "Double": 0.0, "Int64": 0, "Boolean": False}

_COERCE: dict[str, Callable[[Any], Any]] = {
    "String": str,
    "Double": float,
    "Int64": int,
    "Boolean": bool,
}

# source string -> (node, variant type, coercion) for the MQTT updater
DynamicNodes = dict[str, tuple[Node, ua.VariantType, Callable[[Any], Any]]]


def load_spec(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        spec: dict[str, Any] = json.load(fh)
    return spec


async def build_address_space(server: Server, spec: dict[str, Any]) -> DynamicNodes:
    """Instantiate the spec under Objects; return the dynamic-node table."""
    idx = await server.register_namespace(spec["namespace_uri"])
    dynamic: DynamicNodes = {}

    root = await server.nodes.objects.add_object(
        ua.NodeId(spec["root"], ua.Int16(idx)), ua.QualifiedName(spec["root"], idx)
    )
    for obj_spec in spec["objects"]:
        await _add_object(root, idx, obj_spec, dynamic)
    return dynamic


async def _add_object(
    parent: Node, idx: int, obj_spec: dict[str, Any], dynamic: DynamicNodes
) -> None:
    node = await parent.add_object(
        ua.NodeId(obj_spec["node_id"], ua.Int16(idx)),
        ua.QualifiedName(obj_spec["browse_name"], idx),
    )
    await _describe(node, obj_spec.get("description"))
    for var_spec in obj_spec.get("variables", []):
        await _add_variable(node, idx, var_spec, dynamic)
    for nested in obj_spec.get("objects", []):
        await _add_object(node, idx, nested, dynamic)


async def _add_variable(
    parent: Node, idx: int, var_spec: dict[str, Any], dynamic: DynamicNodes
) -> None:
    data_type = var_spec["data_type"]
    variant = _VARIANTS[data_type]
    coerce = _COERCE[data_type]
    value = var_spec["value"] if var_spec["value"] is not None else _INITIAL[data_type]
    node = await parent.add_variable(
        ua.NodeId(var_spec["node_id"], ua.Int16(idx)),
        ua.QualifiedName(var_spec["browse_name"], idx),
        ua.Variant(coerce(value), variant),
    )
    await _describe(node, var_spec.get("description"))
    if var_spec.get("unit") is not None:
        await node.add_property(idx, "Unit", var_spec["unit"])
    if var_spec.get("source") is not None:
        dynamic[var_spec["source"]] = (node, variant, coerce)


async def _describe(node: Node, description: str | None) -> None:
    if description is None:
        return
    await node.write_attribute(
        ua.AttributeIds.Description,
        ua.DataValue(ua.Variant(ua.LocalizedText(description), ua.VariantType.LocalizedText)),
    )
