"""Schema and loader for ur5_model.yaml — the YAML is validated, not trusted.

The rules live here so a bad model dies at `just gen-model`, not at adapter
runtime three containers deep: static submodels carry literal values and no
sources; dynamic submodels carry sources and no values; every source must
match a feeder-feed path the adapters know how to bind.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

PropertyType = Literal["string", "double", "int", "boolean"]

_SOURCE = re.compile(
    r"^(pose\.(?P<pose_field>[a-z_]+)|joint\.(?P<joint>[a-z0-9_]+)\.(?P<joint_field>[a-z]+))$"
)

_PYTHON_TYPES: dict[PropertyType, type | tuple[type, ...]] = {
    "string": str,
    "double": (float, int),  # YAML "5.0" may parse as int if written "5"
    "int": int,
    "boolean": bool,
}


class Property(BaseModel):
    type: PropertyType
    unit: str | None = None
    value: str | float | int | bool | None = None
    source: str | None = None
    semantic_id: str | None = None

    @model_validator(mode="after")
    def _value_matches_type(self) -> Property:
        if self.value is not None and not isinstance(self.value, _PYTHON_TYPES[self.type]):
            raise ValueError(f"value {self.value!r} does not match declared type {self.type}")
        if self.source is not None and _SOURCE.match(self.source) is None:
            raise ValueError(f"source {self.source!r} is not a known feed path")
        return self


class Collection(BaseModel):
    semantic_id: str | None = None
    properties: dict[str, Property] = Field(min_length=1)


class Submodel(BaseModel):
    kind: Literal["static", "dynamic"]
    semantic_id: str | None = None
    properties: dict[str, Property] = {}
    collections: dict[str, Collection] = {}

    @model_validator(mode="after")
    def _kind_discipline(self) -> Submodel:
        for path, prop in self.leaves():
            if self.kind == "static" and (prop.value is None or prop.source is not None):
                raise ValueError(f"static property {path} must have a value and no source")
            if self.kind == "dynamic" and (prop.source is None or prop.value is not None):
                raise ValueError(f"dynamic property {path} must have a source and no value")
        if not self.properties and not self.collections:
            raise ValueError("submodel has no properties")
        return self

    def leaves(self) -> Iterator[tuple[str, Property]]:
        """Yield (dotted path, property) for every leaf, collections included."""
        for name, prop in self.properties.items():
            yield name, prop
        for coll_name, collection in self.collections.items():
            for name, prop in collection.properties.items():
                yield f"{coll_name}.{name}", prop


class Asset(BaseModel):
    id_short: str
    aas_id: str
    global_asset_id: str
    kind: Literal["Instance", "Type"]


class Model(BaseModel):
    asset: Asset
    submodels: dict[str, Submodel] = Field(min_length=1)

    def leaves(self) -> Iterator[tuple[str, str, Property]]:
        """Yield (submodel name, dotted path, property) across the whole model."""
        for submodel_name, submodel in self.submodels.items():
            for path, prop in submodel.leaves():
                yield submodel_name, path, prop


DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "ur5_model.yaml"


def load_model(path: Path = DEFAULT_MODEL_PATH) -> Model:
    with path.open() as fh:
        return Model.model_validate(yaml.safe_load(fh))
