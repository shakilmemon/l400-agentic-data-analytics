# CAI in the agent ecosystem — ADK, A2A, Gemini Enterprise, agents-cli

Researched 2026-07-18 against current Google docs. How this CAI skill relates to
the first-party agent tooling, and when to use what.

## The four integration patterns (from CA API "integration patterns" docs)

| Pattern | What | Use when |
|---|---|---|
| **Direct API** | Your app calls `geminidataanalytics` directly (this skill) | Full control, no framework; embed in any app/notebook; you own auth/state/parsing |
| **Vertical orchestration** | CA agent wrapped as a **tool inside ADK** | An ADK agent needs data answers among other tools |
| **Horizontal orchestration (A2A)** | CA agent published as an **A2A agent** (agent card) | Cross-system/standalone; register into Gemini Enterprise |
| — sub-patterns of Direct API — | single-agent (stateful/stateless) or custom-orchestrator (function-calling root) | prototypes vs. routing |

## ⚠️ ADK now ships FIRST-PARTY CAI tools (overlaps this skill)

Two built-ins exist as of **ADK Python v1.23.0** (experimental). **Confirmed these
are for the Conversational Analytics API** — the ADK docs state the Data Agent tools
provide integration with Data Agents "powered by Conversational Analytics API"
(they don't print the `geminidataanalytics` host string, but it's the same CA data
agent / `dataAgents` resource this skill creates):

1. **`DataAgentToolset`** (`google.adk.tools.data_agent`) — wraps a **pre-created, stored** CA data agent. Tools: `list_accessible_data_agents`, `get_data_agent_info`, `ask_data_agent`. Config via `DataAgentToolConfig(max_query_result_rows=…)` + `DataAgentCredentialsConfig(credentials=ADC)`. Governed agent → consistent behavior across consumers. **Requires you to create the agent first** (that's what this skill does).
2. **`BigQueryToolset` → `ask_data_insights`** — schema-driven, no stored agent; generates SQL from schema inference, text-only answers. Also in the **MCP Toolbox**. Fast/simple, less governed.

### How this skill relates (not replaced — complementary)

- **Use ADK `DataAgentToolset` for the *consume* side** when you're inside ADK and just need to call an already-built agent. Prefer it over hand-rolling `ca_adk.tool_ask_cai` for that case.
- **This skill owns the *build* side**: creating/curating the agent (context, glossary, golden queries, **dynamic table routing**, idempotent create-or-update, soft-delete handling). `DataAgentToolset` has none of that — it assumes the agent exists.
- **This skill's differentiators the built-ins lack:** REST-only/no-SDK path, the SDK/REST backend facade, the context builders (system prompt + glossary + golden queries), idempotent create-or-update + soft-delete handling, and response parsing/hardening.
- **`ca_adk.py` positioning:** keep it as the thin bridge for *inline/stateless + routing* inside ADK (which `DataAgentToolset` doesn't do), and in docs point users to `DataAgentToolset` for the plain "call my stored agent" case.

## A2A + Gemini Enterprise — CA agents are MANAGED (no self-hosting)

**Verified 2026-07-19 (bigquery/docs/create-data-agents).** A CA data agent is
already a Google-managed resource. You do **NOT** stand up a Cloud Run / self-hosted
A2A server for it. To surface it in Gemini Enterprise:

1. Create the agent (this skill: `create_or_update_data_agent`), then in BigQuery
   **publish** it, selecting **Gemini Enterprise** as a publishing option.
2. **Copy the A2A endpoint JSON** the platform generates; share it + the user list
   with your GE admin.
3. Admin registers it as **"Custom agent via A2A"**, pasting the agent-card JSON and
   configuring OAuth (client id/secret, auth + token URIs, scope
   `https://www.googleapis.com/auth/cloud-platform`).

So the chain is simply: **this skill builds/curates the agent → publish to GE → admin
registers the generated A2A endpoint.** No hosting step. The `to_a2a()` + Cloud Run
route is only for *custom* ADK agents, NOT for CA data agents — do not conflate them.

**Hosting policy (when hosting IS needed — i.e. custom ADK agents, not CA agents):**
use **Agent Engine / Agent Runtime** on the **Gemini Enterprise Agent Platform**
(the 2026 rename of Vertex AI; API still `aiplatform.googleapis.com`). Deploying there
with `--a2a-enabled` registers the agent in the Agent Registry and exposes A2A
endpoints automatically (agent-card serving, auth, autoscale-from-zero, built-in
tracing). Prefer this managed runtime over Cloud Run/GKE for our purposes. We do NOT
use Cloud Run.

- GE supports A2A **v0.3 streaming**; A2A now Linux-Foundation governed (v1.2, signed
  agent cards).
- **Auth:** Agent Identity (SPIFFE IDs) for granular IAM — aligns with this skill's
  OAuth-passthrough stance.

## agents-cli (`google/agents-cli`) — really a SKILL BUNDLE, not just a CLI

> Repo-level home for this: `.agents/skills/README.md`. It is a **developer-workstation
> tool**, NOT part of `deploy.sh` (Terraform infra only) and not installed by default.
> Reach for it only if repo scope grows to shipping a *custom ADK agent*; CA data
> agents publish to Gemini Enterprise directly (managed, no agents-cli needed).

Clarification: `agents-cli` is primarily a **bundle of 7 coding-assistant skills**
(context files) installed into Claude Code / Antigravity / Copilot via
`uvx google-agents-cli setup` — plus standalone CLI commands that mirror them. The
value here is the *skills*: they give a coding agent expertise across the ADK agent
lifecycle. Complementary to this repo's *data-layer* skills:

| Skill | Covers |
|---|---|
| `…-scaffold` | `scaffold create/enhance/upgrade`, templates, prototype-first |
| `…-adk-code` | agent types, tools, orchestration, callbacks, state |
| `…-eval` | eval metrics, dataset schema, LLM-as-judge |
| `…-deploy` | deploy workflows, service accounts, rollback |
| `…-publish` | ADK vs A2A registration, Agent Registry, Gemini Enterprise surfacing |
| `…-observability` | Cloud Trace, prompt/response logging, BigQuery Agent Analytics |
| `…-workflow` | always-on lifecycle overview |

`scaffold enhance` adds deploy/CI to an existing agent project. `publish` is the
route to A2A-register + surface in Gemini Enterprise.

### How agents-cli helps THIS skill

- **Don't rebuild lifecycle**: to ship a CAI agent into GE, scaffold an ADK agent
  that uses this skill (or `DataAgentToolset`) as its tool, then `agents-cli`
  handles eval/deploy/publish/observability.
- **Division of labor:** *this repo's skills* = build the data/semantic layer + the
  CA agent; *agents-cli skills* = wrap, evaluate, deploy, and register the agent.
- **Observability / the CLOSED LOOP (high-value for us):** The **BigQuery Agent
  Analytics plugin** for ADK streams every agent event (user msgs, LLM calls, tool
  executions, A2A calls) to a BigQuery table with one line of code (OpenTelemetry
  trace_id/span_id, tool provenance, auto per-event views). Then you point a **CA
  data agent at that events table** and analyze agent behavior in natural language —
  ADK → BigQuery → CA, analyzing CA with CA. Add the **BigQuery-Agent-Analytics-SDK**
  for programmatic **evaluation**: agent-run scoring, golden-trajectory matching,
  trace reconstruction, LLM-as-judge, plus `AI.GENERATE`/`AI.SCORE` root-cause. This
  is the enhancement to pursue: instrument our CA agent, then evaluate it regularly.

## Recommended stances

1. Keep the skill's **build/curate/route** role as the crown jewel — the built-ins
   don't do it.
2. In `ca_adk.py` / `adk-integration.md`, **point to `DataAgentToolset`** for the
   plain "call my stored agent in ADK" case; keep our tools for inline+routing.
3. For Gemini Enterprise, document the **`to_a2a()` → Cloud Run → register** chain
   rather than building A2A plumbing into this skill (stays a standalone node).
4. Treat **agents-cli** as the deploy/publish layer around this skill, not a
   competitor — they compose.
