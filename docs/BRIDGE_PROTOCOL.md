# RXDB runtime bridge protocol v1

The generic extractor does not require a particular language binding to RedEngine. A runtime bridge adapts RedEngine I/O to the protocol below; the Python core owns hierarchy planning, identity, margin filtering, variable batching, explicit-key merges, Parquet, checkpoints and validation.

The reference bridge is `bridges/redatamx_bridge.R`. It uses supported `redatamx` APIs only and never patches RedEngine or uses `TABLE VIEW`.

## Transports

Protocol payloads are identical in both supported transports.

### One-shot JSON

The subprocess reads one JSON request from stdin, writes one JSON response to stdout, and exits. This is the simplest compatibility path.

### Persistent JSON-lines

Starting the reference bridge with `--serve` makes it read one JSON request per line and write one response per line until stdin closes. It keeps `redatamx` loaded and caches opened RXDB handles for the process lifetime.

The Python CLI enables this transport with:

```bash
rxdb --bridge "Rscript bridges/redatamx_bridge.R" --persistent-bridge ...
```

Each `extract-many --workers N` worker owns an independent bridge process and RedEngine handle. The protocol does not permit concurrent requests within one bridge process.

## Envelope

Request:

```json
{
  "protocol_version": "1",
  "action": "capabilities"
}
```

Successful response:

```json
{
  "protocol_version": "1",
  "ok": true,
  "result": {}
}
```

Failed response:

```json
{
  "protocol_version": "1",
  "ok": false,
  "error": "human-readable failure"
}
```

Protocol-level errors should still produce a valid response. A process failure or invalid/missing response is a transport failure.

## `capabilities`

Required result fields:

```json
{
  "redengine_version": "1.3.0-final",
  "redatamx_version": "1.3.0",
  "selection": true,
  "number": true,
  "inherited_define": true,
  "freq": true,
  "cmpcode": true,
  "table_view": false
}
```

`selection`, `number`, `inherited_define`, and `freq` are launch-critical for record extraction.

`cmpcode` is capability-dependent:

- when true, profiles may materialize stable geography such as `RADIO@cmpcode` and may select a coarser entity than the record identity scope;
- when false, a safe fallback is permitted only when `selection_entity == identity_scope`, in which case the exact selection code anchors that scope. This is the qualified RedEngine-1.1 RADIO path.

`table_view` is informational and is not a production backend.

## `inspect`

Request:

```json
{
  "protocol_version": "1",
  "action": "inspect",
  "database": "/path/to/database.rxdb"
}
```

Result schema:

```json
{
  "entities": [
    {
      "name": "RADIO",
      "alias": null,
      "parent": null,
      "selectable": true,
      "variables": []
    },
    {
      "name": "PERSONA",
      "alias": null,
      "parent": null,
      "selectable": false,
      "variables": [
        {"name":"P02","alias":"SEXO","label":"...","type_name":"INTEGER"}
      ]
    }
  ],
  "metadata": {
    "database": "/path/to/database.rxdb",
    "hierarchy_complete": false
  }
}
```

The public `redatamx` entity inventory may be flat. In that case the bridge must say so rather than invent parent relationships; a portable adapter profile may supply a separately validated `parent_map`, which must agree with any runtime parent evidence that does exist.

## `execute_record_plan`

The bridge receives the exact SPC prepared by the Python planner and MUST execute it rather than regenerate record semantics.

Example PERSONA identity-backbone plan:

```json
{
  "protocol_version": "1",
  "action": "execute_record_plan",
  "database": "/path/to/database.rxdb",
  "plan": {
    "entity": "PERSONA",
    "selection_entity": "RADIO",
    "selection_code": "061471101",
    "identity_scope": "RADIO",
    "own_id": "XPID",
    "prelude_definitions": [
      ["VIVIENDA","XVID","NUMBER RADIO"],
      ["HOGAR","XHID","NUMBER RADIO"]
    ],
    "parent_ids": ["XVID","XHID"],
    "geography_fields": [],
    "variables": [],
    "variable_fields": [],
    "dimension_fields": ["XPID","XVID","XHID"],
    "spc": "RUNDEF RXDB_ROWS\nSELECTION RADIO == \"061471101\"\nDEFINE VIVIENDA.XVID AS NUMBER RADIO\nDEFINE HOGAR.XHID AS NUMBER RADIO\nDEFINE PERSONA.XPID AS NUMBER RADIO\nDEFINE PERSONA.XVID AS VIVIENDA.XVID\nDEFINE PERSONA.XHID AS HOGAR.XHID\nFREQ PERSONA.XPID BY PERSONA.XVID BY PERSONA.XHID"
  }
}
```

The direct-ancestor rule is normative: `PERSONA.XVID` is inherited directly from `VIVIENDA.XVID`; it is not relayed through a generated `HOGAR.XVID`. This rule was confirmed by the live RedEngine-1.1 qualification.

A substantive variable batch is narrower, for example `XPID BY P02 BY EDAD`. The identity backbone and payload batches are merged later by explicit `XPID`.

Result:

```json
{
  "rows": [
    {
      "XPID": 1,
      "XPID__mask": 0,
      "XVID": 1,
      "XVID__mask": 0,
      "XHID": 1,
      "XHID__mask": 0,
      "count": 1
    }
  ],
  "mask_fields": {
    "XPID": "XPID__mask",
    "XVID": "XVID__mask",
    "XHID": "XHID__mask"
  },
  "count_field": "count"
}
```

Requirements:

1. every `plan.dimension_fields` item appears as a canonical row field;
2. every dimension has an explicit mask field;
3. frequency count is exposed through `count_field`;
4. margins are preserved at this boundary so the Python normalizer can reject/filter them explicitly;
5. non-unit cells are not silently discarded;
6. the bridge does not join variable blocks or infer parent identity;
7. RedEngine warnings/errors become protocol errors unless explicitly proven benign;
8. source values are not relabeled or semantically transformed.

The Python core removes margin cells using masks, requires non-null structural identity dimensions, requires `count == 1`, normalizes exact integer-valued generated IDs, merges batches by explicit record ID, builds canonical keys, and validates PK/FKs.

## Versioning

Changes to field meaning, schema semantics, mask semantics, or error behavior require a new `protocol_version`. Optional metadata and new transport modes that preserve payload semantics are backwards-compatible.

## Qualified runtimes

The Argentina VP record primitive has been live-qualified on:

```text
redatamx 1.1.3
RedEngine 1.1.0-final
```

using RADIO selection with exact selection-code scope fallback.

The preferred modern target remains RedEngine 1.3-capable operation with `@cmpcode`, because that enables stable engine-provided geography and coarser FRAC selection while retaining RADIO-scoped record identity. That runtime must be qualified separately before a production FRAC run.
