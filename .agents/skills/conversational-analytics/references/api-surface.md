# CAI API Surface (verified 2026-07-16)

Full agent + context surface for `geminidataanalytics` (v0.3.0), verified against
current Google docs. The skill functions expose all of this.

## ⚠️ SDK VERSION PIN: use >= 0.11.0 (0.3.0 breaks answer parsing)

**Pin `google-cloud-geminidataanalytics>=0.11.0`.** Found live (2026-07-17) running
the lab notebook: **SDK 0.3.0 does NOT carry `text_type` on text messages at all**
(the proto only has `parts`). Without `text_type`, THOUGHT / FINAL_RESPONSE /
FOLLOWUP_QUESTIONS cannot be distinguished, so `parse_stream` dumps the entire
reasoning stream into the answer. 0.11.0+ carries `text_type` (matching the REST
`textType`), so bucketing works. Verified working on 0.11.0 and 0.13.1; full API
surface (agents, conversations, context, example_queries, glossary_terms) is
unchanged across these versions.

> Lesson: pin AND test in the pinned environment. Earlier "live-verified" runs used
> base-python 0.11.0 while the notebook's uv env had 0.3.0 — same code, different
> behavior. The `_text_type` value-mapping is kept as defensive belt-and-suspenders.

## ⚠️ Data agents SOFT-DELETE (breaks naive re-create)

Found live (2026-07-17). `delete_data_agent` **soft-deletes**: the agent gets a
`delete_time` and is purged ~30 days later. Consequences:

- `get_data_agent` still RETURNS a soft-deleted agent (with `delete_time` set).
  The skill now treats `delete_time`-present as **not found**.
- The id stays **reserved** until purge: `create` 409s, `update` 400s ("soft
  deleted"), and there is **no undelete/restore API**.
- So a soft-deleted id is stuck. `create_or_update_data_agent` detects this and
  returns a clear, actionable error (use a different id, or don't hard-delete
  agents you intend to re-run).

**Lab guidance:** do NOT hard-delete agents between runs if you want re-runnable
cells. The notebook's Clean Up is opt-in (`DELETE_AGENT=False`) for this reason;
`create_or_update` + `get_or_create_conversation` make re-runs idempotent.

## ⚠️ v0.3.0 SDK vs docs — discrepancies found by introspection (historical)

Introspecting the installed SDK (v0.3.0) revealed the actual `Context` differs from
the public docs. The skill is built against the SDK (ground truth):

- **Glossaries ARE a structured field.** `Context.glossary_terms` is a repeated
  `GlossaryTerm{display_name, description, labels}`. The docs claim glossaries live
  only inside the `system_instruction` YAML — not true in v0.3.0. `ca-context-builder`
  uses the structured field (`build_glossary_terms`), and keeps `system_instruction`
  for free-text / relationships. **This simplifies the lab's glossary→CAI bridge.**
- **`ExampleQuery` has no `parameters`.** Only `natural_language_question` + `sql_query`.
  Parameterized golden queries (docs show `QueryParameter`) are NOT in this version.
- **UDFs unsupported.** No `UserFunctions` / `BigQueryRoutine` classes in v0.3.0. Omitted.
- **`Context` also has** `looker_golden_queries` and `schema_relationships` (structured
  `Context.SchemaRelationship`) — not currently wired by the skill; candidates later.
- **Options type is `ConversationOptions`** with `analysis.python.enabled`,
  `datasource.big_query_max_billed_bytes` (snake_case in SDK), and `chart`.
- **SDK is namespaced `geminidataanalytics_v1alpha`** under the hood (the public
  `google.cloud.geminidataanalytics` re-exports it).

Re-introspect on any SDK upgrade — these may converge toward the docs.

## DataAgent (agent identity)

| SDK (snake_case) | REST (camelCase) | Notes |
|---|---|---|
| `display_name` | `displayName` | user-friendly name — **agents can be named** |
| `description` | `description` | agent description |
| `labels` | `labels` | key/value tags for filtering (e.g. config A/B/C, domain) |
| `name` | `name` | full resource path; pass `data_agent_id` separately on create |
| — | `createTime`/`updateTime`/… | server-set timestamps |
| `kms_key` | `kmsKey` | optional CMEK |

Create with `create_data_agent_sync` (SDK) / `dataAgents:createSync` (REST, **v1beta**).
Always pass an explicit `data_agent_id` (no numeric-name retry loop needed).

## Context / published_context (structured context)

- `system_instruction` — **string, authored as YAML** (see below)
- `datasource_references` — the BigQuery tables
- `options` — `analysis.python.enabled`, `datasource.bigQueryMaxBilledBytes`
- `example_queries` — golden queries: `ExampleQuery(natural_language_question, sql_query, parameters=[QueryParameter(name, data_type, description)])`. Placeholders: `{state}` in NL, `@state` in SQL.
- `user_functions` — `UserFunctions.bq_routines` → `BigQueryRoutine(routine_reference, description)`

## Per-table / per-column context (on `BigQueryTableReference.schema`)

- Table: `schema.description`, `schema.synonyms`, `schema.tags`
- Column: `schema.fields = [Field(name, description, synonyms, tags)]`

## Delivered via the system_instruction YAML (NOT dedicated fields)

- `glossaries:` — **business term / jargon / abbreviation definitions.** This is the
  CAI home for the lab's Dataplex glossary artifacts. There is NO `Context.glossaries` field.
- `additional_descriptions:` — free-text context not covered by structured fields.
- table/relationship guidance (see "Write effective system instructions").

**Implication:** `ca-context-builder` needs a `system_instruction` YAML assembler
(glossary + free-text + persona → YAML string). This is the lab's glossary → CAI bridge.

## Endpoint version split (REST)

| Operation | Version |
|---|---|
| `dataAgents:createSync` | v1beta |
| `conversations` | v1 |
| `:chat` | v1 |
