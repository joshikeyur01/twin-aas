# Changelog

Format: Keep a Changelog; SemVer.

## [Unreleased]

### Added
- Model-first scaffold: ur5_model.yaml + generators for BaSyx AAS
  environment JSON and OPC-UA address-space spec (CI staleness gates).
- feeder (FK once, retained pose), aas-populator (ValueOnly REST PATCH,
  with empirical BaSyx milestone-13 API notes), opcua-server (asyncua,
  spec-built address space).
- comparison harness: three frozen clients, agreement gate, benchmark
  runner regenerating docs/COMPARISON.md with measured numbers.
- 16 tests incl. generator-equivalence and frozen-LOC tripwire; ADRs
  0001-0004; compose stack verified live end-to-end.
