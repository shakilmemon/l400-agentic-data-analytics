# Closed loop: analyze & evaluate a CA agent with ADK → BigQuery → CA

An enhancement pattern, not part of the skill core. It **dogfoods this skill**: the
agent that *analyzes* agent behavior is itself a CA agent built by this skill,
pointed at an agent-events table. Three stages:

```
ADK agent  ──BigQuery Agent Analytics plugin──▶  agent_events table
                                                        │
                    this skill builds a CA agent ◀──────┘  (analysis)
                                                        │
                    BigQuery-Agent-Analytics-SDK ◀──────┘  (evaluation)
```

## 1. Capture — instrument the ADK agent (one plugin)

The **BigQuery Agent Analytics plugin** (ADK Python ≥ v1.21.0) streams every event
(user msgs, LLM calls, tool executions, A2A calls, transfers) to a BigQuery table via
the Storage Write API:

```python
from google.adk.plugins.bigquery_agent_analytics import BigQueryAgentAnalyticsPlugin
from google.adk.apps import App

plugin = BigQueryAgentAnalyticsPlugin(project_id=PROJECT, dataset_id="agent_obs")
app = App(name="my_agent", root_agent=root_agent, plugins=[plugin])
```

Writes `agent_obs.agent_events` (cols: `timestamp, event_type, agent, session_id,
invocation_id, user_id, trace_id/span_id/parent_span_id, content(JSON),
latency_ms(JSON), status, error_message, …`) and, with `create_views=True`, per-event
views: `v_llm_request`, `v_llm_response` (token/latency), `v_tool_completed`,
`v_tool_error`, `v_agent_transfer`, `v_tool_paused`.

## 2. Analyze — a CA agent over the events table (this skill)

The analysis agent is just another CA agent — build it with this skill, pointed at the
events table + views, with a glossary/golden queries about *agent operations*:

```python
import ca
tables = [f"{PROJECT}.agent_obs.agent_events",
          f"{PROJECT}.agent_obs.v_llm_response",
          f"{PROJECT}.agent_obs.v_tool_completed",
          f"{PROJECT}.agent_obs.v_tool_error"]
tr = ca.build_table_references(tables)
gt = ca.build_glossary_terms([
    {"display_name": "Turn",   "description": "One agent invocation (invocation_id)."},
    {"display_name": "Failure","description": "An event with status = 'ERROR'."},
])
eq = ca.build_example_queries([
    {"natural_language_question": "What is the p95 LLM latency by model this week?",
     "sql_query": ("SELECT model, APPROX_QUANTILES(total_ms,100)[OFFSET(95)] AS p95_ms "
                   f"FROM `{PROJECT}.agent_obs.v_llm_response` "
                   "WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) "
                   "GROUP BY model")},
])
ctx = ca.build_context(
    "You analyze AI-agent operational logs for reliability, latency, cost, and errors.",
    tr["results"]["datasource_references"],
    glossary_terms=gt["results"]["glossary_terms"],
    example_queries=eq["results"]["example_queries"])
ca.create_or_update_data_agent(PROJECT, "global", "agent-obs-analyst",
                               ctx["results"]["context"],
                               display_name="Agent Observability Analyst",
                               labels={"origin": "closed-loop"})
# then ask in NL: "Which tools error most often?", "Cost per session trend?"
```

`evals/observability_closed_loop.py` builds this context offline (no deploy) to prove
the wiring.

## 3. Evaluate — regularly, with the Agent Analytics SDK

`BigQuery-Agent-Analytics-SDK` (GoogleCloudPlatform/BigQuery-Agent-Analytics-SDK) is a
consumption-layer toolkit over the same events: **agent-run scoring** vs expected
outcomes, **golden-trajectory matching** (did execution follow the approved path),
**trace reconstruction**, LLM-as-judge, and `AI.GENERATE`/`AI.SCORE` for root-cause
(“explain the root cause of this failed conversation”). Schedule it (e.g. daily) to
watch quality/latency/cost drift over time.

## Why this is a good fit here

- **Dogfoods the skill** — the analysis agent is a CA agent; same `build_context` /
  `create_or_update_data_agent` flow, just pointed at `agent_events`.
- **Stays out of the skill core** — this is an *application* of the skill (in `evals/`),
  not new skill code. The heavier, reusable version lives in the sibling
  **`agent-quality`** skill (the trust trio: acceptance + observability + evaluation),
  so the CAI skill stays focused.
- Pairs with `agents-cli`'s observability skill and the "closed loop" community pattern.

## Sources
- BigQuery Agent Analytics plugin (ADK): https://adk.dev/integrations/bigquery-agent-analytics/
- Agent Analytics SDK: https://github.com/GoogleCloudPlatform/BigQuery-Agent-Analytics-SDK
- "Closed Loop" pattern: https://cloud.google.com/blog/products/data-analytics/introducing-bigquery-agent-analytics
