"""`python -m modelgen` — regenerate both artefacts from ur5_model.yaml."""

from __future__ import annotations

from pathlib import Path

from modelgen.aas import write_aas
from modelgen.opcua import write_opcua
from modelgen.schema import load_model

REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    model = load_model()
    aas_path = write_aas(model, REPO_ROOT / "deploy" / "basyx")
    opcua_path = write_opcua(model, REPO_ROOT / "adapters" / "opcua-server" / "spec")
    for path in (aas_path, opcua_path):
        print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
