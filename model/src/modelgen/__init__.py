"""modelgen: the UR5 information model's schema, loader, and generators.

`python -m modelgen` renders model/ur5_model.yaml into the BaSyx submodel
JSON and the OPC-UA address-space spec. Both are checked in; CI fails on
drift. The YAML is the only file a human edits."""

from modelgen.schema import Model, Property, Submodel, load_model

__all__ = ["Model", "Property", "Submodel", "load_model"]
