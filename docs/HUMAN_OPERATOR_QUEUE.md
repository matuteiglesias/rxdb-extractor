# Human operator queue

These tasks are intentionally deferred because they require access to the local census corpus, the validated RedEngine runtime, or a human policy/licensing decision.

## Runtime / local-machine actions

- Run the first live `rxdb inspect` integration against the local `Base_VP/cpv2022.rxdb` under the validated RedEngine 1.3.0 container/runtime.
- Capture the exact native/runtime paths and any ABI/runtime diagnostics needed for the production RedEngine bridge.
- Run the M3 live one-RADIO slice on `061471101` once the bridge is wired.
- Run the FRAC identity-scope qualification on `0614711` and compare canonical IDs against RADIO-scoped runs.

## Source acquisition

- Acquire or recover the corrected July-2025 RedatamX corpus if possible.
- Preserve April and July sources separately and record hashes; do not overwrite the April research corpus.

## Governance / distribution

- Review RedEngine redistribution/licensing before publishing a container image that bundles the engine.
- Review confidentiality/statistical-secrecy implications before publishing reconstructed person-level national data.

## Rule

None of these items blocks pure extractor engineering. Development should continue against typed runtime boundaries, fixtures, provenance contracts, CLI behavior, Parquet writing, validation, and adapter logic until a live local run becomes necessary.
