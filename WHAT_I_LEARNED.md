# What I learned

- **Spec and implementation are different standards.** AAS Part 2 says
  ValueOnly uses native JSON types; BaSyx milestone-13 returns 400/500 for
  exactly that and accepts string values on collection-level PATCH only.
  Empirical probing beat documentation in under ten minutes, and the
  workaround (2 PATCHes/tick) became a measured cost in the matrix.
- **The raw baseline earns its place.** mqtt-raw is ~2x faster than either
  standard and its client is no shorter — which quantifies what the
  semantic layers actually charge and what they don't.
- **OPC-UA's binary efficiency is real (72 vs ~220 bytes) but session
  setup dominates one-shot queries** — highest p50 of the three. Transport
  encoding and interaction pattern are separate axes; conflating them is
  how standards debates go wrong.
- **Generate both models from one file.** Equivalence promised in prose
  drifts; equivalence generated from ur5_model.yaml with leaf-set-equality
  tests cannot. The asymmetries that remain (semanticId vs Description)
  are then genuine findings, not modelling accidents.
- **Freeze your measuring instruments.** The frozen-LOC pin caught its
  first "tamper" the same day — the code formatter. Right response, per
  the rule: update pin and matrix together, in the open.
