# rxdb-extractor

A provenance-first extractor for recovering relational records from hierarchical RedatamX/RXDB databases through supported RedEngine query semantics.

The production backend is based on `SELECTION + NUMBER + direct ancestor IDs + FREQ`, with an identity-backbone query, narrow variable batches, explicit-key merges, Parquet output, deterministic checkpoints and exact PK/FK validation. It does **not** depend on `TABLE VIEW`, binary patching, or direct RBFX decoding.

Argentina Census 2022 is the first reference use case, implemented separately in [`argentina-censo2022-rxdb`](https://github.com/matuteiglesias/argentina-censo2022-rxdb).

## Status

The record primitive is qualified against the preserved Argentina Census 2022 VP corpus on Linux with `redatamx 1.1.3` / `RedEngine 1.1.0-final` using the RADIO selection-code compatibility path.

Permanent live laboratories qualified on 2026-09-02 include:

- RADIO `061120902`: 1 VIVIENDA / 1 HOGAR / 1 PERSONA;
- RADIO `061471101`: 73 / 56 / 137, with all PK/FK checks passing;
- RADIO `064279901`: 1,663 / 1,627 / 6,992, with all PK/FK checks passing.

The large-radio all-variable run took about 2m30s and peaked near 1.34 GB RSS on the qualifying host using the original one-shot bridge. This motivated the persistent bridge and explicit bounded worker controls now provided for production-scale runs.

RedEngine 1.3 remains the preferred runtime for `@cmpcode` and coarser FRAC partitioning. It is a separate runtime qualification gate, not a prerequisite for the proven RADIO compatibility path.

## CLI

Configure the reference R bridge:

```bash
export RXDB_BRIDGE="Rscript $HOME/repos/rxdb-extractor/bridges/redatamx_bridge.R"
```

Inspect runtime/database capabilities:

```bash
rxdb --bridge "$RXDB_BRIDGE" inspect /data/cpv2022.rxdb
```

Extract one profile-defined slice:

```bash
rxdb --bridge "$RXDB_BRIDGE" \
  extract /data/cpv2022.rxdb \
  --profile ./profile.json \
  --selection-code 061471101 \
  --output ./out/radio-061471101

rxdb validate ./out/radio-061471101
```

Run an explicit partition inventory with verified resume checkpoints:

```bash
rxdb --bridge "$RXDB_BRIDGE" \
  --persistent-bridge \
  extract-many /data/cpv2022.rxdb \
  --profile ./profile.json \
  --partitions ./radios.json \
  --output-root ./out/vp-radio \
  --workers 2
```

`--workers` defaults to `1`. Each worker owns its own bridge/RedEngine process, so higher values must be chosen explicitly against available RAM. `--limit N` is useful for bounded qualification before a long run. Re-running the same command resumes only checkpoints whose provenance and artifacts still verify.

Partition inventories may be JSON, CSV/TSV, or one-code-per-line text. JSON entries may carry exact expected entity counts for acceptance laboratories.

## Runtime bridge

The reference bridge has two transports with identical protocol-v1 semantics:

- one-shot JSON: one R subprocess per request, simplest compatibility path;
- persistent JSON-lines (`--persistent-bridge`): one R process per worker, opened RXDBs cached across requests.

The persistent transport is intended for long extraction runs and should be live-qualified on the target runtime before launching a national job.

## Correctness rules

- row position never defines identity;
- descendant records inherit each generated ancestor ID directly from the ancestor that owns it;
- parent relationships are established in a narrow identity backbone before substantive variable batches;
- variable batches merge only by explicit generated record ID;
- FREQ margins are filtered using masks and complete record cells require `count == 1`;
- output partitions are immutable/checkpointed against source, schema, profile and runtime identities;
- no national person-level output should be publicly redistributed without a separate disclosure/privacy review.

See [`docs/spec/00_START_HERE.md`](docs/spec/00_START_HERE.md) and [`docs/BRIDGE_PROTOCOL.md`](docs/BRIDGE_PROTOCOL.md) for the detailed contracts.
