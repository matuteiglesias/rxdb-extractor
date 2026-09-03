# Pass 2.5 local provenance audit

Audit date: 2026-09-03 (America/Argentina/Buenos_Aires).

## Scope and safety

This was a bounded, local, read-only evidence acquisition. `/media/matias/Elements` was treated as immutable: no writes, extraction, rename, move, deletion, permission change, or timestamp change were performed there. No national extraction was run. No sibling repository was changed. ZIP members were read with `zipinfo`/`unzip -p`; no archive needed extraction. No census records are reproduced here.

Statements are deliberately labelled **OBSERVED**, **INFERRED**, or **UNKNOWN**. Filenames and mtimes are inventory attributes, not provenance proof.

## Evidence roots

- **OBSERVED:** source/legacy root: `/media/matias/Elements/CENSO_dirs`.
- **OBSERVED:** current evidence root: `/media/matias/Elements/CENSO_work` (`provenance`, `logs`, `profiles`, `rxdb`, `frames`, `samples`, `targets`, plus test debris under `tmp`).
- **OBSERVED:** static implementation roots: `/home/matias/repos/censo2022arg_1.0.1/censo2022arg`, this repository, and `/home/matias/repos/argentina-censo2022-rxdb`.
- **OBSERVED:** the bounded filesystem census returned 1,199 entries through depth 3 in `CENSO_dirs` and 100 in `CENSO_work`; deeper `CENSO_work/tmp` contains voluminous test debris and was not promoted to evidence.

The reproducible metadata inventories are [local_artifact_manifest.tsv](evidence/local_artifact_manifest.tsv), [archive_inventory.tsv](evidence/archive_inventory.tsv), [candidate_source_hashes.tsv](evidence/candidate_source_hashes.tsv), and [radio_evidence.tsv](evidence/radio_evidence.tsv). The artifact manifest intentionally records relevant primary sources and durable work products, rather than recursively hashing legacy 1991/2001/2010 microdata, large derived frames, samples, or test debris. Those exclusions avoid giant, low-value reads.

## Source artifact inventory

**OBSERVED:** four top-level files are directly relevant: the 1,188,760,157-byte bases ZIP, 5,348,532-byte metadata ZIP, 56,859,538-byte portable runtime ZIP, and 10,582-byte `PERSONA.parquet`. Their byte sizes, filesystem mtimes, and SHA-256 values are in the manifests. `Censo_2010/` and `Censo_2010_p/` are older-census trees and were identified but not recursively hashed. The bases ZIP has 26 entries and 1,188,756,335 uncompressed bytes.

**OBSERVED:** the bases ZIP contains exactly:

- `Base_VP`: eight RBFX companions plus `cpv2022.rxdb`;
- `Base_ PO_A_IG` (note the literal space): six RBFX companions plus `cpv2022.rxdb`;
- `Base_VC_PSC`: five RBFX companions plus `cpv2022_col.rxdb`;
- three directory entries and `LEEME.txt`.

All member sizes and ZIP timestamps are in `archive_inventory.tsv`. The archive is effectively stored (only `LEEME.txt` is deflated). The three RXDB hashes were independently streamed from the ZIP. Existing `legacy-source-manifest-check.txt` reports `OK` for all 23 RXDB/RBFX members against `source-april-2025.json`.

## April-source custody assessment

**OBSERVED:** the bases archive SHA-256 is `fc72bd93…f58b2838`, identical to `CENSO_work/provenance/archive-zips.sha256`. Its three streamed RXDB hashes are:

- VP: `abcc06e8…15edb246` (1,423,033 bytes);
- PO_A_IG: `c6adab6d…9cbed84` (229,847 bytes);
- VC_PSC: `d444ac25…f8689fe` (81,265 bytes).

**OBSERVED:** those hashes/sizes and all 20 RBFX hash/size pairs match `source-april-2025.json`; the recorded all-member check is also complete. This is content identity, not a filename/mtime inference.

**INFERRED (strong):** the preserved ZIP contains the exact three-database corpus fingerprinted as `release_label: april-2025` and used as the source reference for the April/May research. Twenty-three independent member content matches plus the archive checksum strongly identify the bytes. The inference concerns the historical act of use: the later custody JSON names an old `/home/matias/Documents/...` root, and no contemporaneous acquisition receipt or immutable run manifest binds the April/May process directly to this archive object.

**UNKNOWN:** who downloaded the archive, the upstream URL and download time, and whether the filesystem mtime reflects acquisition are not established.

## Search for July replacement

The local search was restricted to the two evidence roots and the three supplied repositories. It matched case-insensitive alternate `bases_censo2022_RedatamX*.zip`, `cpv2022.rxdb`, the three `Base_*` directory spellings, and likely old work copies.

**OBSERVED (negative):** only the preserved bases ZIP was found; no standalone `cpv2022.rxdb` or alternate Census-2022 `Base_VP`, `Base_PO_A_IG`/`Base_ PO_A_IG`, or `Base_VC_PSC` tree was present in those roots. No July-labelled candidate was present.

**UNKNOWN:** an April-vs-July byte/schema comparison cannot be performed without July bytes or a trustworthy July manifest. The search says nothing about unsearched disks/roots.

## Search for ARG2022

**OBSERVED (negative):** no `ARG2022.rds`, `ARG2022.zip`, `ARG2022.csv`, or comparably named data artifact was found in the supplied roots. Only `docs/spec/03_ARG2022_ADAPTER_SPEC.md` appeared in the two project repositories. Searches for `Mauricio` and `Open-REDATAM` yielded no local data candidate.

**UNKNOWN:** ARG2022 schema, content, creator, chain of custody, and relationship to Open-REDATAM remain unavailable locally.

## PERSONA.parquet assessment

**OBSERVED:** `PERSONA.parquet` is 10,582 bytes, SHA-256 `d6c9fb0b…4357de1`, one row group, five rows, and 15 nullable `int64` columns: `PERSONA_REF_ID`, `HOGAR_REF_ID`, `P01`, `P02`, `P03`, `P05`, `P06`, `P07`, `P12`, `EDADAGRU`, `EDADQUI`, `P08`, `P09`, `P10`, `CONDACT`. Footer metadata says `parquet-cpp-arrow 17.0.0`, PyArrow 17.0.0, pandas 2.2.2, and a range index of five rows.

**OBSERVED:** its footer has no source URL, source hash, author, execution command, geography, or ARG2022/Mauricio marker. Nearby top-level files do not supply a manifest binding it to a producer.

**INFERRED:** it is a tiny development/sample artifact, not a national corpus. **UNKNOWN:** how it was generated and by whom. It must not be attributed to Mauricio.

## Existing CENSO_work evidence timeline

Filesystem mtimes order the surviving artifacts but do not prove event time:

1. **OBSERVED:** 2026-09-02 01:13–01:16 — `source-april-2025.json`, archive checksums, and the 23-member `OK` check establish custody fingerprints.
2. **OBSERVED:** 01:32 — `vp-inspection.json` records redatamx 1.1.3 / RedEngine 1.1.0-final capabilities: selection, NUMBER, inherited DEFINE, and FREQ true; `cmpcode` and TABLE VIEW false; inspected hierarchy marked incomplete.
3. **OBSERVED:** 01:34–01:57 — repeated radio `061120902` runs fail first on missing/non-integer identity and then null inherited `XVID`. `redengine11-generated-ids-061120902.txt` shows NUMBER-derived IDs and FREQ masks. Version `v5` passes after selection-code geography fallback and corrected ancestor definitions.
4. **OBSERVED:** 02:01–02:08 — accepted runs for `061120902` and `061471101`; the latter is copied into the `m3-*` manifest, validation, and artifact checksum set.
5. **OBSERVED:** 02:17 — frame `arg-cpv2022-frame-8e135fba13e79073` passes with 73 dwellings, 56 households, 137 persons, one department.
6. **OBSERVED:** 02:28 — `064279901` passes; `/usr/bin/time` reports 150.36 seconds wall time and 1,342,200 KB maximum RSS.

**INFERRED:** this is a coherent source-fingerprint → inspection → generated-ID experiments → accepted radio slices → frame sequence. **UNKNOWN:** the logs do not cryptographically bind each extraction to the preserved RXDB; their database path points to the old Documents tree.

## Duran vs rxdb-extractor mechanism comparison

`argentina-censo2022-rxdb` is an adapter/frame layer, not a third engine extractor: it discovers source layouts and builds/hashes a frame from validated `rxdb-extractor` Parquet slices (`sources.py:57-85`, `manifest.py:36-85`, `frame.py:77-85,199-250,271-395`).

| Dimension | Duran `censo2022arg` | `rxdb-extractor` / Argentina adapter |
|---|---|---|
| Extraction primitive | Native C/C++ RedEngine output iteration and `TABLE VIEW` (`src/red_execute.cpp:82-162,331-400`; `R/extraer_rxdb.R:247-250`) | R/JSON bridge emits SPC `FREQ`; planner composes FREQ (`src/rxdb_extractor/frequency.py:32-44`, `planner.py:45-85`) |
| Identity | Reconstructs dwelling/household identifiers by scanning flat rows (`R/extrae_censo.R:113-166`) | Defines entity sequences with `NUMBER RADIO`; canonical key is `radio:sequence` (`hierarchy.py:20-55`, `identity.py:14-52`) |
| Hierarchy | Reconstructed from changing hierarchy variables in TABLE VIEW rows | Explicit ancestor definitions and foreign keys; profile topology compensates for incomplete engine hierarchy (`hierarchy.py:29-55`, `dataset.py:104-138`) |
| Batching | Variable blocks with repeated control columns, default bounded width (`R/extrae_censo.R:42-100`; `R/extraer_rxdb.R:212-224`) | Identity backbone plus payload batches, merged by explicit IDs (`planner.py:45-85`, `executor.py:37-91`) |
| Row position | Validates equal row counts/control columns, then appends columns by position (`R/extrae_censo.R:355-405`; `R/extraer_rxdb.R:313-335`) | Explicitly merges by identity tuple, never row position (`executor.py:50-91`, `merge.py:19-75`) |
| TABLE VIEW | Core primitive | Capability-probed but not used; local 1.1 inspection says false |
| FREQ | Not the extraction primitive | Core record-cell primitive; masks/margins normalized (`frequency.py:32-44`, `normalizer.py:15-105`) |
| NUMBER IDs | Not used in the shown extraction path | Required generated identities for each record entity (`hierarchy.py:29-55`) |
| Binary patch | C++ wrapper dynamically calls engine API; package comments describe an engine crash constraint, but no required binary-patch step is present (`R/extrae_censo.R:213-221`) | No binary patch; specifications reject production dependence on one (`../argentina-censo2022-rxdb/docs/spec/09_EVIDENCE_BASELINE.md:146-160`) |
| Checkpoints | Province/block files and skip-if-final-output-exists behavior (`R/extrae_censo.R:786-852`) | Atomic success checkpoints bind source/schema/query/runtime identity and artifact hash; mismatches invalidate (`checkpoint.py:13-124`, `manifest.py:16-28`, `orchestration.py:128-216`) |
| Source provenance | User/configured RXDB paths and official-control tables; no content hash in extraction output found | Source-manifest hashing exists in adapter (`manifest.py:36-85`), but current radio manifests omit source hash |
| Validation | Cross-block controls, row counts, and province totals against bundled INDEC controls (`R/extrae_censo.R:355-390,705-766`) | Unique keys, FK integrity, expected counts/reaggregation model, validation JSON (`validation.py:36-133`, `dataset.py:159-218`) |
| Output schema | Wide person-grain VP plus person/household/dwelling/collective exports; Parquet/CSV/SAV/SAS (`R/extrae_censo.R:411-435,518-533`) | Separate typed entity Parquets with value/mask fields and canonical keys; adapter adds neutral frame IDs and frame tables (`artifacts.py:50-94`; adapter `frame.py:210-224,315-404`) |

**OBSERVED:** the implementations therefore differ materially in primitive, identity, hierarchy, merge contract, checkpointing, and canonical schema. Static similarity or difference is not bounded-radio output equivalence.

## Known radio fixtures and exact evidence

All use batch width 5, RADIO identity scope, semantic profile hash `13cb1cf0…5d3608`, RedEngine 1.1.0-final (compiled 2025-04-27), redatamx 1.1.3, selection-code fallback, and passing unique-key/FK checks.

| Radio | VIVIENDA | HOGAR | PERSONA | Output |
|---|---:|---:|---:|---|
| 061120902 | 1 | 1 | 1 | `CENSO_work/rxdb/vp-radio-061120902` |
| 061471101 | 73 | 56 | 137 | `CENSO_work/rxdb/vp-radio-061471101` |
| 064279901 | 1,663 | 1,627 | 6,992 | `CENSO_work/rxdb/vp-radio-064279901` |

**OBSERVED:** exact entity artifact hashes are embedded in each dataset manifest; `m3-artifacts.sha256` independently records the accepted `061471101` set. **UNKNOWN:** source RXDB hash is absent from each radio manifest, so association with the April archive is contextual rather than cryptographically closed. `061471101` alone has an acceptance-target file and generated frame evidence.

## Contradictions register

- **OBSERVED:** archive directory is literally `Base_ PO_A_IG`, while Duran configuration expects `Base_PO_A_IG` (`R/Censo_config.R:196-200`). Source discovery supports alternatives; consumers must not silently normalize without recording it.
- **OBSERVED:** `vp-inspection.json` says `table_view: false`; Duran relies on TABLE VIEW. This may reflect wrapper/runtime/API differences, not a universal engine fact.
- **OBSERVED:** `source-april-2025.json` records `/home/matias/Documents/...`; durable evidence now resides under `/media/...`, and extraction manifests still name the old path.
- **OBSERVED:** profile file SHA-256 `6ab5c047…3c22ec` differs from semantic profile hash `13cb1cf0…5d3608`; these are different hash domains, not corruption.
- **OBSERVED:** the inspected engine hierarchy is incomplete while the project profile supplies hierarchy. That is an explicit reconstruction assumption.
- **OBSERVED:** early `061120902` outputs contain partial Parquets despite failed logs; only directories with passing `validation.json` are accepted.

## Missing evidence

- **A — ARG2022:** actual artifact, hash, schema, creator/export method, geography/identity semantics, and custody record.
- **B — Duran vs ours:** same source hash, runtime characterization, bounded radio query, canonical column mapping, sorted key-based row comparison, masks/null semantics, and count/reaggregation report.
- **C — April vs July:** acquired July archive plus checksum/acquisition record, full member manifest, RXDB/RBFX hashes, schema inspections, and bounded semantic diff.
- **D — three-way equivalence:** A–C plus ARG2022 mapping and a common comparison contract for records, IDs, missingness, labels, and universes.
- **E — interviews:** dated, attributable notes/recordings with Pablo and Mauricio covering source acquisition, transformations, corrections, versions, and custody; claims must remain testimony until corroborated.

## Pass-3 readiness matrix

| Workstream | Local evidence | Readiness | Blocking item |
|---|---|---|---|
| A ARG2022 schema/provenance | Negative search only | Not ready | Obtain artifact and custody evidence |
| B Duran-vs-ours bounded-radio equivalence | Code and three ours fixtures | Partly ready | Run Duran on same hashed source/radio; define mapping |
| C April-vs-July byte/schema diff | April fully fingerprinted | Not ready | July candidate absent in supplied roots |
| D Three-way equivalence | Ours only; Duran static | Not ready | A, B, and C |
| E Pablo/Mauricio interviews | No local evidence | Not ready | Conduct and preserve interviews |

No novelty claim is assessed.

## Commands executed

Read-only commands (with bounded `find` roots) included:

```text
git status --short; git branch --show-current
find <supplied-root> -maxdepth 3 -printf ...
find <five-supplied-roots> -type f/d <bounded name predicates>
zipinfo -l/-v bases_censo2022_RedatamX.zip
unzip -Z -1 bases_censo2022_RedatamX.zip
unzip -p bases_censo2022_RedatamX.zip <three RXDB members> | sha256sum
sha256sum <source archives, PERSONA.parquet, bounded CENSO_work artifacts>
python3 (pyarrow.parquet footer/schema inspection only)
rg -n <mechanism/radio/provenance terms> <three repositories>
jq <selected manifest/runtime/count fields> <radio manifests>
sed/cat/nl -ba <provenance, logs, and implementation files>
```

No `unzip` extraction command, write command targeting `/media`, source-code test, or national extraction command was executed.

## Conclusions

- **OBSERVED:** the preserved bases ZIP and all 23 database members match the existing April-labelled custody manifest byte-for-byte.
- **INFERRED:** this strongly identifies the preserved archive as the source corpus represented by the April/May research evidence, but does not independently prove the historical download/use event.
- **OBSERVED:** no July replacement or ARG2022 data artifact exists in the supplied local roots.
- **UNKNOWN:** July-source differences and ARG2022 provenance/schema.
- **OBSERVED:** `PERSONA.parquet` is only a five-row sample with no author/source binding.
- **OBSERVED:** three local radio slices pass structural validation, but their manifests omit a source-content hash.
- **OBSERVED:** Duran and `rxdb-extractor` use materially different extraction and identity mechanisms; equivalence requires a controlled Pass-3 comparison.
- **UNKNOWN:** three-way equivalence and interview-derived provenance.
