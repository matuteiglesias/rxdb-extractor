# RXDB runtime bridge protocol v1

The generic extractor does not require a particular language binding to RedEngine.
A runtime bridge is any subprocess that reads one JSON request from stdin, writes one
JSON response to stdout, and implements the protocol below.

This boundary is intentionally narrow. The bridge owns **RedEngine I/O adaptation**;
the Python core owns record identity, hierarchy planning, margin filtering, count=1
invariants, variable batching, key construction, Parquet, checkpoints and validation.

## Envelope

Request:

```json
{
  "protocol_version": "1",
  "action": "capabilities",
  "...": "action-specific fields"
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

The bridge should return exit status 0 for protocol-level error responses. A non-zero
process exit indicates the bridge itself failed before producing a valid protocol response.

## `capabilities`

Request:

```json
{"protocol_version":"1","action":"capabilities"}
```

Required result:

```json
{
  "redengine_version": "1.3.0-final",
  "selection": true,
  "number": true,
  "inherited_define": true,
  "freq": true,
  "cmpcode": true,
  "table_view": false
}
```

`selection`, `number`, `inherited_define`, and `freq` are launch-critical for the
production record backend. `cmpcode` is currently required by the canonical composite-key
profile path. `table_view` is informational and is not a production backend.

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
      "parent": "FRAC",
      "selectable": true,
      "variables": []
    },
    {
      "name": "PERSONA",
      "alias": null,
      "parent": "HOGAR",
      "selectable": false,
      "variables": [
        {"name":"P02","alias":"SEXO","label":"..."}
      ]
    }
  ],
  "metadata": {
    "database": "/path/to/database.rxdb"
  }
}
```

Requirements:

- every entity has a stable source `name`;
- `parent` is the source entity name or null;
- `selectable` reflects RedEngine metadata;
- stored variables retain source name/alias/label where available;
- the bridge must not invent hierarchy;
- output order is preserved for diagnostics but the core does not use "last entity = leaf".

## `execute_record_plan`

Request:

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
      ["HOGAR","XHID","NUMBER RADIO"],
      ["HOGAR","XVID","VIVIENDA.XVID"]
    ],
    "parent_ids": ["XVID","XHID"],
    "geography_fields": ["XPROV","XDPTO","XFRAC","XRADIO"],
    "variables": ["PERSONA.P02","PERSONA.EDAD"],
    "variable_fields": ["P02","EDAD"],
    "dimension_fields": ["XPID","XVID","XHID","XPROV","XDPTO","XFRAC","XRADIO","P02","EDAD"],
    "spc": "RUNDEF RXDB_ROWS\n..."
  }
}
```

The bridge MUST execute the provided `plan.spc` rather than regenerate record semantics.
It then translates the engine table into canonical names.

Result:

```json
{
  "rows": [
    {
      "XPID": 1,
      "XPID__mask": 0,
      "XVID": 1,
      "XVID__mask": 0,
      "P02": 1,
      "P02__mask": 0,
      "count": 1
    }
  ],
  "mask_fields": {
    "XPID": "XPID__mask",
    "XVID": "XVID__mask",
    "P02": "P02__mask"
  },
  "count_field": "count"
}
```

Requirements:

1. every item in `plan.dimension_fields` appears as a canonical row field;
2. every dimension has an explicit corresponding mask field;
3. frequency count is exposed through `count_field`;
4. the bridge MUST NOT silently remove margins;
5. the bridge MUST NOT silently remove non-unit cells;
6. the bridge MUST NOT join variable blocks or infer parent identity;
7. warnings/errors from RedEngine must become protocol errors unless explicitly known benign;
8. source values should not be relabeled or semantically transformed at this boundary.

The Python core filters margins using masks, requires exactly one complete cell per record,
requires count=1, joins batches by generated ID, builds canonical keys, and validates PK/FK
integrity.

## Versioning

Protocol changes that alter field meaning, schema semantics, mask semantics, or error
behavior require a new `protocol_version`.

Adding optional metadata fields is backwards-compatible.

## Current production target

The first concrete bridge should target the validated:

```text
redatamx 1.3.0
RedEngine 1.3.0-final
```

It must not patch the engine binary and must not use `TABLE VIEW`.
