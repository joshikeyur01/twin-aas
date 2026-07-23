"""Model schema teeth + generator equivalence: both artefacts carry exactly
the model's property tree — divergence is a build error, not a discovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from modelgen import load_model
from modelgen.aas import generate_environment, submodel_id
from modelgen.opcua import generate_spec
from modelgen.schema import Model


def _model_leaf_paths() -> set[tuple[str, str]]:
    return {(sm, path) for sm, path, _ in load_model().leaves()}


def test_model_loads_with_expected_shape() -> None:
    model = load_model()
    assert set(model.submodels) == {"Nameplate", "TechnicalData", "OperationalData", "Capability"}
    dynamic = [p for _, p, prop in model.leaves() if prop.source]
    assert len(dynamic) == 14  # 8 pose + 6 joints


def test_static_property_with_source_rejected() -> None:
    raw = yaml.safe_load(Path("model/ur5_model.yaml").read_text())
    raw["submodels"]["Nameplate"]["properties"]["SerialNumber"]["source"] = "pose.x"
    with pytest.raises(ValidationError, match="must have a value and no source"):
        Model.model_validate(raw)


def test_unknown_source_path_rejected() -> None:
    raw = yaml.safe_load(Path("model/ur5_model.yaml").read_text())
    props = raw["submodels"]["OperationalData"]["collections"]["EndEffectorPose"]["properties"]
    props["X"]["source"] = "gripper.force"
    with pytest.raises(ValidationError, match="not a known feed path"):
        Model.model_validate(raw)


def test_aas_environment_carries_exactly_the_model() -> None:
    env = generate_environment(load_model())
    aas_leaves = set()
    for submodel in env["submodels"]:
        for element in submodel["submodelElements"]:
            if element["modelType"] == "Property":
                aas_leaves.add((submodel["idShort"], element["idShort"]))
            else:
                for prop in element["value"]:
                    aas_leaves.add((submodel["idShort"], f"{element['idShort']}.{prop['idShort']}"))
    assert aas_leaves == _model_leaf_paths()


def test_opcua_spec_carries_exactly_the_model() -> None:
    spec = generate_spec(load_model())
    ua_leaves = set()
    for obj in spec["objects"]:
        for var in obj["variables"]:
            ua_leaves.add((obj["browse_name"], var["browse_name"]))
        for nested in obj["objects"]:
            for var in nested["variables"]:
                ua_leaves.add((obj["browse_name"], f"{nested['browse_name']}.{var['browse_name']}"))
    assert ua_leaves == _model_leaf_paths()


def test_stamp_is_wide_in_both_dialects() -> None:
    env = generate_environment(load_model())
    op = next(s for s in env["submodels"] if s["idShort"] == "OperationalData")
    pose = next(e for e in op["submodelElements"] if e["idShort"] == "EndEffectorPose")
    stamp = next(p for p in pose["value"] if p["idShort"] == "StampNs")
    assert stamp["valueType"] == "xs:long"
    spec = generate_spec(load_model())
    op_ua = next(o for o in spec["objects"] if o["browse_name"] == "OperationalData")
    pose_ua = next(o for o in op_ua["objects"] if o["browse_name"] == "EndEffectorPose")
    stamp_ua = next(v for v in pose_ua["variables"] if v["browse_name"] == "StampNs")
    assert stamp_ua["data_type"] == "Int64"


def test_generation_is_deterministic_and_ids_stable() -> None:
    model = load_model()
    assert json.dumps(generate_environment(model)) == json.dumps(generate_environment(model))
    assert submodel_id(model, "OperationalData") == (
        "https://twin-portfolio.example/submodels/operationaldata"
    )
