# rxdb-extractor

A provenance-first extractor for recovering relational records from hierarchical RedatamX/RXDB databases through supported RedEngine query semantics.

The production design is based on `SELECTION + NUMBER + inherited parent IDs + unique-ID FREQ`, with Parquet output, explicit hierarchy, deterministic checkpoints, and exact validation. It does **not** depend on `TABLE VIEW`, binary patching, or direct RBFX decoding.

Argentina Census 2022 is the first reference use case, implemented separately in [`argentina-censo2022-rxdb`](https://github.com/matuteiglesias/argentina-censo2022-rxdb).

## Status

Early development. Feasibility and RedEngine 1.3.0 compatibility have been established; implementation is proceeding from a validated thin vertical slice before national-scale orchestration.

See [`docs/spec/00_START_HERE.md`](docs/spec/00_START_HERE.md) for the development specification.

## Intended interface

```bash
rxdb inspect database.rxdb
rxdb extract database.rxdb --entity PERSONA --output ./out
rxdb validate ./out
```

The CLI/library interface is intended to be language-neutral. A Python package is the first user-facing implementation target; RedEngine remains the database execution runtime.

## Development rule

Correctness, identity, provenance, and restartability come before scale. No national extraction work should precede the M3 one-RADIO acceptance slice defined in the specifications.
