---
name: conversational-analytics
description: Build and interact with BigQuery Conversational Analytics (the geminidataanalytics / CAI NL2SQL API) in every mode — stateful conversations, stateless chat with a stored agent, and stateless inline chat with no stored agent. Use this skill when the user asks to create, update, or deploy a CA data agent, chat with their BigQuery data in natural language, or build a Conversational Analytics context (system instruction, glossary, golden/example queries) from a curated table list.
---

# Skill: Conversational Analytics (CAI)

Build, deploy, and interact with the BigQuery Conversational Analytics API (`geminidataanalytics`, NL2SQL) in all three interaction modes. It consumes a curated table list + context (authored upstream — see below) and turns it into a deployed or inline CA agent.

Two mirrored implementations are provided so you can see the same operation both ways:
- **`scripts/ca_sdk.py`** — Python SDK (`google-cloud-geminidataanalytics>=0.11.0` — older 0.3.0 lacks `text_type` and breaks answer parsing). Primary/reference.
- **`scripts/ca_rest.py`** — REST from Python (`google-auth` + `requests`). Same function names/signatures/order — diff the two files to see exactly what the SDK does under the hood.

Both return the house-standard dict: `{"status", "tool_name", "messages", "results"}`.

## Using this skill in another project

This folder is self-contained and portable — the runtime code (`scripts/`) has **no
dependency on this repo**; it takes project/dataset/region/model as parameters. To
reuse it anywhere:

1. **Copy** `.agents/skills/conversational-analytics/` into the target repo.
2. **Prerequisites** in the target GCP project: enable the `geminidataanalytics`,
   and `bigquery` APIs; authenticate with ADC (`gcloud auth application-default
   login`). The agent runs under the caller's identity (OAuth pass-through) — do not
   use a privileged SA.
3. **Install deps** — `scripts/requirements.txt` (full) or `scripts/requirements-rest.txt`
   (REST-only, no SDK).
4. **Import** via the path pattern below and call with your own ids:
   ```python
   import sys, os
   sys.path.append(os.path.abspath('.agents/skills/conversational-analytics/scripts'))
   import ca
   tr  = ca.build_table_references(["my-project.my_dataset.MY_TABLE"])
   ctx = ca.build_context("You are a data analyst for <domain>.",
                          tr["results"]["datasource_references"])
   ans = ca.chat("my-project", "global", "How many orders last month?",
                 "inline", inline_context=ctx["results"]["context"])
   print(ans["results"]["answer"]["text"])
   ```

Nothing about the skill knows about `l400-agentic-data-analytics`; examples below that reference it are
illustrative of *this* repo. See `evals/` for full worked examples and `DESIGN.md`
for the architecture.

> **Optional richer input (OKF).** In this repo, the CA agent definition (system
> prompt, table list, golden queries) is authored upstream by a prompt-driven flow
> (`docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-*.md` →
> `okf-staging/conversational-analytics/*`) and fed to this skill via a bridge in
> `evals/`. This skill stays **standalone and OKF-unaware** — it consumes a curated
> table list + context regardless of where that curation came from. The "structure
> the staging → deploy" step lives in the bridge, not here.

## Integrating with ADK, A2A & Gemini Enterprise

This skill's job is to **build, deploy, and interact with** CA data agents (context
from a curated table list + glossary + golden queries, idempotent create). For
*consuming* a stored agent inside a larger agentic system, use the first-party paths
below — don't rebuild them here.
Full detail + sources: [references/ecosystem-integration.md](references/ecosystem-integration.md).

### Call a stored agent from ADK (vertical orchestration)

ADK ships a first-party **`DataAgentToolset`** (ADK Python ≥ v1.23.0, experimental)
for the Conversational Analytics API. Build the agent with this skill, then let an
ADK agent call it:

```python
# build/curate once with this skill (governed, consistent behavior):
ca.create_or_update_data_agent(PROJECT, "global", "cfo-agent",
    ctx["results"]["context"], display_name="CFO Agent")

# consume from ADK — first-party, no custom glue:
from google.adk.tools.data_agent.data_agent_toolset import DataAgentToolset
from google.adk.tools.data_agent.config import DataAgentToolConfig
from google.adk.tools.data_agent.credentials import DataAgentCredentialsConfig
import google.auth
creds, _ = google.auth.default()
da_toolset = DataAgentToolset(
    credentials_config=DataAgentCredentialsConfig(credentials=creds),
    data_agent_tool_config=DataAgentToolConfig(max_query_result_rows=100),
    tool_filter=["list_accessible_data_agents", "get_data_agent_info", "ask_data_agent"],
)
# add da_toolset to your ADK Agent(...). ask_data_agent chats with the stored agent.
```

For **inline chat inside ADK over a curated table set** (which `DataAgentToolset`
doesn't do — it targets a stored agent), use this skill's `ca_adk.py` tool
`tool_ask_cai` (build context → `chat('inline')`). See `references/adk-integration.md`.

### Publish to Gemini Enterprise (A2A) — MANAGED, no hosting

A CA data agent is **already a Google-managed resource** — there is **no Cloud Run /
self-hosting step**. To surface it in Gemini Enterprise:

1. Build it with this skill, then in **BigQuery → publish** the agent, selecting
   **Gemini Enterprise**.
2. **Copy the generated A2A endpoint JSON**; give it + the user list to your GE admin.
3. Admin registers it as **"Custom agent via A2A"** (paste the agent-card JSON,
   configure OAuth, scope `https://www.googleapis.com/auth/cloud-platform`).

That's it — GE (and other A2A clients) then call the managed agent directly.

### Hosting policy

CA agents need **no hosting** (managed, per above). Only *custom* ADK agents need
hosting; when they do, use **Agent Engine / Agent Runtime** on the **Gemini
Enterprise Agent Platform** (2026 rename of Vertex AI; API `aiplatform.googleapis.com`;
`--a2a-enabled` auto-exposes endpoints). **We do not use Cloud Run.**

## Choosing a backend: the `ca.py` facade

Prefer **`ca.py`** — a facade that unifies both behind one import. **SDK is the default**; REST is a per-call or per-session override:

```python
import ca
ca.chat(project_id, location, q, "agent", agent_name=...)   # SDK (default)
ca.chat(..., backend="rest")                                # REST for one call
ca.set_backend("rest")                                      # REST for the session
# or set env CA_BACKEND=rest
```

**REST-only environments:** the facade loads a backend *lazily* — selecting REST
(`set_backend("rest")` or `CA_BACKEND=rest`) **never imports the SDK**. Customers who
avoid the SDK (fewer dependencies to manage, security review) can install only
`requirements-rest.txt` (`google-auth` + `requests`) and run the whole skill over REST.

You can still `import ca_sdk` / `import ca_rest` directly for hands-on side-by-side comparison.

## Auth

Both use Application Default Credentials (current user) via `google.auth.default()`. This aligns with the lab's governance rule: CA agents must use OAuth pass-through, **never** a privileged service account.

## Import pattern

```python
import sys, os
sys.path.append(os.path.abspath('.agents/skills/conversational-analytics/scripts'))
import ca_sdk        # or: import ca_rest  (identical API)
```

## Functional areas

| Area | Status | Purpose |
|---|---|---|
| **ca-chat** | ✅ built | `chat()` — unified dispatcher over all 3 modes |
| **ca-agent-manage** | ✅ built | `create_data_agent` / `create_or_update_data_agent` / `update` / `get` / `list` / `delete` stored agents |
| **ca-conversation** | ✅ built | `create_conversation` / `get_or_create_conversation` / `get_conversation` / `list_conversations` / `delete_conversation` / `list_messages` (all with server-side `filter_str` + paging) |
| **ca-trace** | ✅ built | `get_conversation_turns` — reconstruct a stateful conversation's stored history into `{prompt, response, timestamp, thoughts, followups, data, generated_sql}` turns (native audit, no ADK) |
| **ca-context-builder** | ✅ built | `build_table_references` / `build_glossary_terms` / `build_example_queries` / `build_context` |
| **ca-adk** (optional) | ✅ built | Optional ADK tools + `ca.to_tool_json`; ADK owns memory→stateless inline. See [references/adk-integration.md](references/adk-integration.md) |

> **Building a Context** (feeds both `create_data_agent` and inline `chat`):
> ```python
> import ca
> tr  = ca.build_table_references(["proj.l400_agentic_da.SLS_ORD_HDR", "proj.l400_agentic_da.SLS_ORD_DTL_LN"])
> eq  = ca.build_example_queries([{"natural_language_question": "...", "sql_query": "..."}])  # golden queries
> gt  = ca.build_glossary_terms([{"display_name": "Net Revenue", "description": "Gross minus discounts & refunds"}])
> ctx = ca.build_context("You are the CFO assistant...", tr["results"]["datasource_references"],
>                        example_queries=eq["results"]["example_queries"],
>                        glossary_terms=gt["results"]["glossary_terms"],
>                        max_billed_bytes=104857600)
> # stateful: ca.create_data_agent(..., context=ctx["results"]["context"]) → create_conversation → chat('conversation')
> # stateless inline: ca.chat(..., context_mode="inline", inline_context=ctx["results"]["context"])
> ```
> **SDK notes:** glossaries are a *structured* field (`glossary_terms`), not YAML;
> example queries have no `parameters`; UDFs unsupported. See references/api-surface.md.

## Where table curation happens

This skill **consumes** a curated table list (and system prompt + golden queries) —
it does not discover them. In this repo, that curation is authored upstream by the
`ca-generate-*` prompt flow into `okf-staging/conversational-analytics/*` (see the
skills README). The skill's job is to turn those into a Context and deploy.
## Robustness & debugging

- **Retry/backoff** on transient errors (RESOURCE_EXHAUSTED/429/503) is automatic
  on every network call (`ca_common.retry`); non-retryable errors raise at once.
- **Pagination**: list operations fetch all pages (no silent truncation).
- **Idempotency**: `create_or_update_data_agent` survives lab-cell re-runs.
- **Debug tracer** (opt-in): set `CA_DEBUG=1` or `ca.set_debug(True)`, then
  `ca.get_trace()` returns per-call records (op, backend, ms, status). Use
  `ca.new_trace_id()` + pass `trace_id=` to correlate a context→chat run.

## The three chat modes

`chat(project_id, location, question, context_mode, ...)`:

- **`'conversation'`** — STATEFUL. Server retains history. Requires `conversation_name` + `agent_name`.
- **`'agent'`** — STATELESS with a stored agent. You pass `history` each call. Requires `agent_name`.
- **`'inline'`** — STATELESS, no stored agent. You pass `inline_context` (SDK: a `Context`; REST: a dict) and `history`. This is the target for dynamic per-question routing.

See [references/chat-modes.md](references/chat-modes.md) for details and the request shapes.

## Example

```python
import sys, os
sys.path.append(os.path.abspath('.agents/skills/conversational-analytics/scripts'))
import ca_sdk

# Stateless chat against an existing stored agent
resp = ca_sdk.chat(
    project_id="l400-agentic-da-xxxx",
    location="global",
    question="What was our total Net Revenue for Fiscal Year 2025?",
    context_mode="agent",
    agent_name="projects/l400-agentic-da-xxxx/locations/global/dataAgents/cfo-finance-agent",
    history=[],
)
print(resp["status"], resp["results"]["answer"]["text"])
# Continue the (stateless) conversation by passing back the history:
follow = ca_sdk.chat(..., context_mode="agent", agent_name=..., history=resp["results"]["history"])
```

## Notes

- The response list mixes message kinds (text/schema/data/chart) in non-deterministic order, and text messages are bucketed by `textType` (FINAL_RESPONSE = answer, THOUGHT/PROGRESS = reasoning, FOLLOWUP_QUESTIONS = suggested next). Use `ca.parse_stream(raw)` for `{text, thoughts, followups, data, generated_sql, has_chart, all_text}`, or `ca.find_messages(raw, kind, text_type=...)` to locate raw messages. Full map: [references/chat-modes.md](references/chat-modes.md).
- Chart PNG rendering is left to the caller (needs `vl_convert`); the skill flags `has_chart` and returns the raw responses (`results["raw"]`) so a notebook can render via `find_messages(raw, "chart")`.
- `results["history"]` is returned for stateless modes so you can continue a conversation.
- `results["raw"]` holds the unparsed responses for advanced inspection.
- **Auditing a deployed stateful agent (native, no ADK):** enumerate an agent's
  conversations, then reconstruct each into Q&A turns —
  ```python
  convs = ca.list_conversations(project, "global", filter_str=f'agents:"{agent_name}"')
  for c in convs["results"]["conversations"]:
      turns = ca.get_conversation_turns(c["name"])   # [{prompt, response, timestamp, ...}]
  ```
  This is the stateful trace-retrieval path the `agent-quality` trust layer builds on
  (inline mode uses the persisted tracer; embedded ADK uses the `agent_events` plugin).

## Project layout

This skill folder is self-contained and portable — copy it to any repo:

```
conversational-analytics/
├── SKILL.md            # this file
├── DESIGN.md           # architecture + decisions + change log
├── pyproject.toml      # uv dev/test/eval environment
├── scripts/            # runtime code (ca*.py) + requirements(.rest).txt
├── references/         # deep-dive docs (chat-modes, api-surface, adk-integration, ecosystem-integration)
├── tests/              # PORTABLE verification (offline + opt-in live); run: uv run pytest tests/
└── evals/              # worked examples + measurement (some repo-specific); see evals/README.md
```

The learner tutorial notebook lives in the repo's `colab-enterprise/` (it *uses*
the skill; it isn't part of it).

## References

- [Build a data agent using the Python SDK](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/build-agent-sdk)
- [Build a data agent using HTTP and Python](https://docs.cloud.google.com/gemini/data-agents/conversational-analytics-api/build-agent-http)
- [Define data agent context for BigQuery](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/data-agent-authored-context-bq)
- [Known limitations](https://docs.cloud.google.com/gemini/docs/conversational-analytics-api/known-limitations)
- [DataAgent REST resource](https://docs.cloud.google.com/gemini/data-agents/reference/rest/v1beta/projects.locations.dataAgents)
- Full verified API surface: [references/api-surface.md](references/api-surface.md)
- Foundational reference notebook: `vertex-ai-mlops/Applied ML/AI Agents/conversational-analytics-api/`
- CAI setup best practices (design rationale — independently validates this skill's
  approach: keep agents focused (<20 core tables), structured context > prose, and
  the priority verified-queries → glossaries → instructions): in this repo,
  `docs/requirements/Conversational-Analytics-Best-Practices/ca-best-practices.md`. These
  map to `build_example_queries` / `build_glossary_terms` / `build_context`.
