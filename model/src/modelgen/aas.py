"""Render the model as a BaSyx v2 environment file (AAS Part 2 JSON).

One JSON file, deterministic output: same model in, byte-identical file out
— that is what lets CI diff the artefact for staleness. Dynamic properties
are emitted with zero values; the populator overwrites them at runtime and
never changes the structure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modelgen.schema import Model, Property, PropertyType, Submodel

_XSD: dict[PropertyType, str] = {
    "string": "xs:string",
    "double": "xs:double",
    # xs:long, not xs:int: StampNs is nanoseconds since epoch (> 2^31).
    "int": "xs:long",
    "boolean": "xs:boolean",
}

_INITIAL: dict[PropertyType, str] = {
    "string": "",
    "double": "0.0",
    "int": "0",
    "boolean": "false",
}


def submodel_id(model: Model, name: str) -> str:
    """The submodel identifier, derived deterministically from the asset IRI.

    Exposed so runtime consumers (the populator) and this generator can
    never disagree about which submodel they are talking about.
    """
    base_iri = model.asset.aas_id.rsplit("/aas/", 1)[0]
    return f"{base_iri}/submodels/{name.lower()}"


def _semantic_id(iri_or_irdi: str) -> dict[str, Any]:
    return {
        "type": "ExternalReference",
        "keys": [{"type": "GlobalReference", "value": iri_or_irdi}],
    }


def _property_element(name: str, prop: Property) -> dict[str, Any]:
    # AAS JSON serialises Property values as strings.
    value = str(prop.value) if prop.value is not None else _INITIAL[prop.type]
    if prop.type == "boolean" and prop.value is not None:
        value = "true" if prop.value else "false"
    element: dict[str, Any] = {
        "modelType": "Property",
        "idShort": name,
        "valueType": _XSD[prop.type],
        "value": value,
    }
    if prop.semantic_id is not None:
        element["semanticId"] = _semantic_id(prop.semantic_id)
    if prop.unit is not None:
        # Full IEC 61360 data specifications would be ceremony out of
        # proportion to this repo; a standard Qualifier keeps units visible
        # and conformant. Noted in COMPARISON.md's methodology.
        element["qualifiers"] = [
            {
                "kind": "ConceptQualifier",
                "type": "Unit",
                "valueType": "xs:string",
                "value": prop.unit,
            }
        ]
    return element


def _submodel_json(model: Model, name: str, submodel: Submodel) -> dict[str, Any]:
    elements: list[dict[str, Any]] = [
        _property_element(prop_name, prop) for prop_name, prop in submodel.properties.items()
    ]
    for coll_name, collection in submodel.collections.items():
        coll: dict[str, Any] = {
            "modelType": "SubmodelElementCollection",
            "idShort": coll_name,
            "value": [
                _property_element(prop_name, prop)
                for prop_name, prop in collection.properties.items()
            ],
        }
        if collection.semantic_id is not None:
            coll["semanticId"] = _semantic_id(collection.semantic_id)
        elements.append(coll)

    result: dict[str, Any] = {
        "modelType": "Submodel",
        "id": submodel_id(model, name),
        "idShort": name,
        "kind": "Instance",
        "submodelElements": elements,
    }
    if submodel.semantic_id is not None:
        result["semanticId"] = _semantic_id(submodel.semantic_id)
    return result


def generate_environment(model: Model) -> dict[str, Any]:
    submodels = [
        _submodel_json(model, name, submodel) for name, submodel in model.submodels.items()
    ]
    shell = {
        "modelType": "AssetAdministrationShell",
        "id": model.asset.aas_id,
        "idShort": model.asset.id_short,
        "assetInformation": {
            "assetKind": model.asset.kind,
            "globalAssetId": model.asset.global_asset_id,
        },
        "submodels": [
            {
                "type": "ModelReference",
                "keys": [{"type": "Submodel", "value": submodel["id"]}],
            }
            for submodel in submodels
        ],
    }
    return {
        "assetAdministrationShells": [shell],
        "submodels": submodels,
        "conceptDescriptions": [],
    }


def write_aas(model: Model, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "ur5_environment.json"
    target.write_text(json.dumps(generate_environment(model), indent=2) + "\n")
    return target
