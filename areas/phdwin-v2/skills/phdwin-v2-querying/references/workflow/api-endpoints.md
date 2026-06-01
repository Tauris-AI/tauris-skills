# PhdWIN API Endpoints

This reference captures the verified endpoint patterns exposed by the local PhdWIN implementation.

## Required Headers

- `datasource`: required on requests; points to the dataset folder or other supported source.
- `mimetype`: optional; when omitted, directories default to PhdWIN/Topspeed and files default to Access.
- `schema`: optional; used by other datasource types, not the normal PhdWIN folder flow.

## Schema Discovery

List available tables:

```http
POST /api/schema
datasource: <dataset-folder>
content-type: application/json

{
  "schemaName": "tables"
}
```

Inspect the schema for one table:

```http
POST /api/schematable
datasource: <dataset-folder>
content-type: application/json

"{{phd}}\\&MAINLSE"
```

Generate scaffold code from a table:

```http
POST /api/scaffold
datasource: <dataset-folder>
content-type: application/json

"{{phd}}\\&FORCAST"
```

## Raw SQL

Read-only ad hoc query:

```http
POST /api/query
datasource: <dataset-folder>
content-type: application/json

{
  "query": "SELECT LSE_ID, LSE_NAME, FLD, RESERVOIR FROM {{phd}}\\&MAINLSE"
}
```

Scalar query:

```http
POST /api/queryscalar
datasource: <dataset-folder>
content-type: application/json

{
  "query": "SELECT MAX(LSE_ID) FROM {{phd}}\\&MAINLSE"
}
```

## Common Typed Endpoints

The generated entities expose table-level routes through `[GeneratedController(...)]` annotations. Verified examples:

- `/api/mainlse`
- `/api/groups`
- `/api/filter`
- `/api/filterline`
- `/api/sort`
- `/api/owner`
- `/api/monhist`
- `/api/forcast`

Typical use:

```http
GET /api/mainlse
datasource: <dataset-folder>
```

## Higher-Level Business Endpoints

Verified from the UI service layer:

- `/api/projecttree`
- `/api/projecttree/filtered?flt_id=<id>&grp_id=<id>`
- `/api/project/<lse_id>`
- `/api/projectvariable?lse_id=<id>`
- `/api/projectvariable/investments?lse_id=<id>`
- `/api/forecastvariable/formulas?lse_id=<id>`
- `/api/forecastvariable/segments?lse_id=<id>`
- `/api/forecastvariable/params?lse_id=<id>`
- `/api/ownership?lse_id=<id>`
- `/api/ownership?lse_id=<id>&grp_id=<id>`

Use these before raw SQL when the question is already aligned to an existing view model.

## Notes

- `{{phd}}` and `{{mod}}` substitutions are resolved by the server from the files present in the datasource directory.
- The PhdWIN path is folder-based. The datasource should usually point at the uncompressed `.phz` contents, not the zip file itself.
