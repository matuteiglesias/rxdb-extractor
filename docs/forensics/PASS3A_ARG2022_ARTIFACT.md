# Pass 3A — ARG2022 artifact acquisition and inspection

Audit date: 2026-09-03 (America/Argentina/Buenos_Aires).

## Scope, custody, and safety

- **OBSERVED:** `ARG2022.zip` was downloaded directly from the `pachadotdev/redatam-microdata` GitHub release asset into the sole newly authorized evidence directory, `/media/matias/Elements/CENSO_work/external/mauricio-arg2022/`.
- **OBSERVED:** no pre-existing evidence file was modified. The archive was never fully extracted. Headers and small metadata members were streamed from the ZIP; no census record is included in this report or in git.
- **OBSERVED:** the acquired file is 929,500,495 bytes and SHA-256 `1bd87c321be200ae7974ec8f0795004be5f658f5606dd4a86cc6cab4645cd90a`, exactly matching both the expected acquisition gate and the digest currently exposed by the [official GitHub release API](https://api.github.com/repos/pachadotdev/redatam-microdata/releases/tags/2.0.2).
- **OBSERVED:** `unzip -t` reports no compressed-data errors across all 96 members.
- **UNKNOWN:** local download mtime `2026-09-03 03:04:43 -0300` is an acquisition-system timestamp, not an upstream production date.

The complete central-directory metadata is in [arg2022_archive_inventory.tsv](evidence/arg2022_archive_inventory.tsv); logical table headers are in [arg2022_schema.tsv](evidence/arg2022_schema.tsv).

## Release metadata

- **OBSERVED:** GitHub identifies asset ID `401481928`, uploader account `pachadotdev`, creation `2026-04-21T10:09:56Z`, update `2026-04-21T10:16:49Z`, media type `application/zip`, size 929,500,495, and the matching SHA-256 digest. The release tag is `2.0.2`; the release itself was originally published in 2024 and updated in 2026.
- **OBSERVED:** the same release also exposes `ARG2022.rds` (973,756,705 bytes, a distinct recorded SHA-256), but that RDS was not acquired.
- **UNKNOWN:** the GitHub metadata does not name an upstream INDEC archive, source checksum, RedatamX version, extraction command, or source generation.

## Archive inventory and packaging

- **OBSERVED:** the ZIP has 96 root-level CSV members, no directories, no archive comment, no README, and no manifest. Total uncompressed size is 7,005,050,682 bytes; compressed member bytes total 929,488,959 (86.7% reduction).
- **OBSERVED:** 95 members are normally deflated; only the 46-byte `vivienda_labels_v06.csv` is stored. CRC-32, member sizes, compressed sizes, methods, and DOS timestamps are recorded in the inventory TSV.
- **OBSERVED:** member timestamps cluster between `2026-04-21T10:14:34` and `10:15:38`, shortly after the asset creation time. ZIP timestamps are metadata, not proof of source age.
- **OBSERVED:** eight data tables account for the corpus. The other 88 members are per-variable label tables: 3 province, 2 department, 13 dwelling, 30 household, and 40 person label files. No label members accompany the root, fraction, or radio tables.

## Logical schema

**OBSERVED:** header-only inspection establishes this explicit hierarchy:

```text
CPV2022(cpv2022_ref_id)
└── PROV(prov_ref_id → cpv2022_ref_id)
    └── DPTO(dpto_ref_id → prov_ref_id)
        └── FRAC(frac_ref_id → dpto_ref_id)
            └── RADIO(radio_ref_id → frac_ref_id)
                └── VIVIENDA(vivienda_ref_id → radio_ref_id)
                    └── HOGAR(hogar_ref_id → vivienda_ref_id)
                        └── PERSONA(persona_ref_id → hogar_ref_id)
```

- **OBSERVED:** entity column counts are CPV2022 2, PROV 6, DPTO 6, FRAC 5, RADIO 5, VIVIENDA 15, HOGAR 32, and PERSONA 42.
- **OBSERVED:** the schema separates person, household, dwelling, and four geography levels rather than materializing one denormalized intermediate table.
- **OBSERVED:** every table has a generated-looking `<entity>_ref_id`; every non-root table has exactly one immediate-parent reference. Geography also retains source-looking codes/names such as `idprov`, `iddpto`, `idfrac`, `idradio`, `redcoden`, `nomprov`, and `nomdpto`.
- **OBSERVED:** label members follow `<entity>_labels_<variable>.csv` and cover categorical fields selectively. Their presence is metadata evidence; no data rows were committed.
- **STRONG INFERENCE:** hierarchy is explicit at the exported relational level. Referential integrity and identifier generation semantics were not tested in Pass 3A, so uniqueness, completeness, and stability across conversions remain **UNKNOWN**.

## EDAD_EDU source-version fingerprint

Search scope included all 96 member names, all eight data-table headers, and decoded content of every small label/metadata member (all members at or below 200 KB). The three exact case-insensitive probes were `EDAD_EDU`, `EDADEDU`, and `Edad educativa`.

- **OBSERVED — ABSENT:** none of the three probes occurs in that scope. `persona.csv` contains `edadqui`, `edadgru`, and `edad`, but not `EDAD_EDU`/`EDADEDU`; no corresponding person-label member exists.
- **STRONG INFERENCE:** this artifact does not expose the stated July-replacement fingerprint in its names, schema, or label metadata.
- **UNKNOWN:** absence does not prove an April source. The converter could omit/rename a field, could use a different universe, or could have received another source generation. Determining source generation requires upstream content/checksum or a mapped April/July comparison.

## Comparison with ARG1991 and local census corpora

- **OBSERVED:** local `ARG1991.zip` is another release-style flat ZIP: root-level entity CSVs plus `<entity>_labels_<variable>.csv` members. It has 103 members and explicit reference links such as `depto_ref_id → provin_ref_id`, `fraccion_ref_id → depto_ref_id`, `radio_ref_id → fraccion_ref_id`, `segmento_ref_id → radio_ref_id`, `vivienda_ref_id → segmento_ref_id`, `hogar_ref_id → vivienda_ref_id`, and `persona_ref_id → hogar_ref_id`.
- **OBSERVED:** ARG1991 uses semicolon-delimited CSV and includes SEGMENTO; ARG2022 uses comma-delimited CSV and has RADIO directly parent dwelling. These are census-specific schema differences within the same packaging pattern.
- **OBSERVED:** local `Censo_1991` and `Censo_2010` directories contain traditional REDATAM binaries/dictionaries plus separately materialized entity/label CSVs. ARG2022 contains only the latter relational export products—no RXDB/RBFX/RBF/dictionary, executable, extraction log, or command manifest.
- **STRONG INFERENCE:** ARG2022 conforms closely to the corpus convention represented by local `ARG1991.zip`: normalized entity CSVs, explicit synthetic reference IDs, and per-variable label CSVs. This is evidence of common packaging/conversion lineage, not merely an arbitrary externally produced wide table.
- **OBSERVED:** the tagged [publisher README](https://github.com/pachadotdev/redatam-microdata/blob/2.0.2/README.md) states that the publicly available REDATAM microdata was converted with software from `litalbarkai/open-redatam`.
- **STRONG INFERENCE:** archive structure plus the publisher's tagged statement supports the repository claim that this release belongs to an Open REDATAM conversion pipeline.
- **UNKNOWN:** the archive itself does not record the converter, converter version, invocation, input file hashes, or transformation log. Therefore Open REDATAM as the exact converter for these specific ARG2022 bytes is externally asserted and structurally compatible, but not self-authenticating. Subsequent repackaging or post-processing cannot be excluded.

## Contradictions and open provenance questions

### What did Pablo provide?

- **OBSERVED:** Pass 3A acquired the artifact from GitHub, not from Pablo. No local message, receipt, checksum statement, or custody note attributes these bytes to Pablo.
- **UNKNOWN:** whether Pablo previously provided this ZIP, the RDS sibling, an upstream REDATAM database, a link, or only contextual information. Interview or message evidence is still required.

### Which source generation does ARG2022 reflect?

- **OBSERVED:** the archive lacks the EDAD_EDU fingerprint described for the 2025-07-08 replacement.
- **WEAK INFERENCE:** the absence is more compatible with a pre-July schema than with an unmodified, complete July-or-later private-dwelling population export.
- **UNKNOWN:** April, July, or another generation cannot be assigned because absence is non-dispositive and no source checksum/mapping is embedded.

### Was Open REDATAM converter or packaging lineage?

- **OBSERVED:** the publisher expressly says the corpus was converted with Open REDATAM, and ARG2022 matches the ARG1991 relational/labels convention.
- **STRONG INFERENCE:** Open REDATAM is the likely conversion lineage.
- **UNKNOWN:** exact execution-level attribution for ARG2022 remains unproved without a converter manifest, logs, version, command, or reproducible input/output comparison. Packaging lineage alone does not establish untouched converter output.

### Mauricio attribution

- **OBSERVED:** the acquisition URL and API identify the GitHub account `pachadotdev`; the bytes match GitHub's digest.
- **UNKNOWN:** this artifact alone does not legally or forensically establish the account holder's identity, who performed the conversion, or whether “Mauricio” personally created/uploaded it. The directory label records the investigation's source lead, not a proven authorship claim.

## Readiness and next evidence

- **OBSERVED:** Pass 3A closes the prior “artifact absent locally” gap for the ZIP and establishes archive identity, integrity, logical schema, hierarchy, labels, and the negative EDAD_EDU result.
- **UNKNOWN:** record counts, FK integrity, identifier uniqueness, value/missingness semantics, and exact equivalence with RXDB-derived outputs were outside this metadata-first pass.
- **UNKNOWN:** a three-way comparison still needs a bounded, key-mapped comparison contract and a defensible source-generation mapping.
- **UNKNOWN:** source provenance still needs the converter's input archive/hash, Open REDATAM version and command/log, and Pablo/Mauricio custody testimony with corroborating records.

## Commands executed

```text
mkdir -p <authorized external evidence directory>
curl --fail --location --output <authorized path>/ARG2022.zip <release URL>
stat; sha256sum
zipinfo -l; unzip -Z -v; unzip -Z -1; unzip -t
python3 zipfile header-only and small-member metadata searches
zipinfo/unzip inventory and header-only comparison against local ARG1991.zip
find (bounded, read-only comparison of Censo_1991/Censo_2010 filenames)
curl official GitHub release API and tagged README (read-only)
```

No full extraction, census query, national extraction, source-directory write, or microdata commit occurred.

## Conclusions

- **OBSERVED:** acquired ARG2022 is byte-identical to the expected and GitHub-recorded release asset.
- **OBSERVED:** it is an eight-table hierarchical relational CSV corpus with 88 label files and explicit parent references.
- **OBSERVED:** EDAD_EDU/EDADEDU/“Edad educativa” is **ABSENT** from member names, table headers, and small metadata members.
- **STRONG INFERENCE:** its layout shares the Open-REDATAM-style corpus convention seen in ARG1991 and supports the publisher's Open REDATAM conversion claim.
- **WEAK INFERENCE:** the missing fingerprint is compatible with a pre-July source, but is insufficient to identify April.
- **UNKNOWN:** precise source generation, converter execution/version, Pablo's contribution, and Mauricio's personal role.
- **UNKNOWN:** no novelty or three-way equivalence conclusion is made.
