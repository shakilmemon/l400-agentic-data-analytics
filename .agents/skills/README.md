# Skills in this repo — how they fit together

This repo's `l400-agentic-data-analytics` lab teaches CEs to build a **Conversational Analytics (CAI)**
agent over a deliberately messy legacy schema. The skills form one pipeline:
**author a canonical semantic layer (OKF) → sync it into Google Cloud → serve
questions with a CAI agent.**

```
 raw inputs         author        canonical    sync into GCP    author CA agent       deploy+serve      trust
 (PDF, SQL,     ─▶ *-to-okf  ─▶   okf/     ─▶  okf-to-*     ─▶ ca-generate-*     ─▶ conversational- ─▶ agent-
  glossary, BI)                   (markdown)   (Dataplex/BQ)   prompts →             analytics          quality
                                                              okf-staging/                             (accept·observe·eval)
```

## OKF — the canonical semantic layer (authoring/governance)

**OKF** (the `okf/` tree) is a canonical markdown format for tables, columns,
business terms, and metrics, with front-matter + schema tables. It's the single
source of truth the other skills read and write.

| Skill | Direction | Purpose |
|---|---|---|
| `pdf-to-markdown` | in | PDF → clean markdown (Gemini on Vertex) |
| `bigquery-dataset-to-okf` | → OKF | BQ dataset schema → OKF table docs |
| `bigquery-table-to-okf` | → OKF | single BQ table schema → OKF table doc |
| `gemini-to-okf` | → OKF | prompt + context documents → custom OKF output |
| `glossary-to-okf` | → OKF | glossary markdown → OKF glossary terms |
| `metrics-to-okf` | → OKF | legacy SQL / BI → OKF metric definitions |
| `unstructured-data-to-okf` | → OKF | business requirements → OKF table + CA context |
| `term-mappings-to-okf` | → OKF | Dataplex term mappings → OKF table schemas |
| `data-dictionary-to-okf` | → OKF | data dictionary → OKF |
| `okf-to-glossary` | OKF → | OKF terms → Dataplex Business Glossary |
| `okf-to-bigquery-metadata` | OKF → | OKF table/column descriptions → BigQuery schema |
| `okf-to-term-links` | OKF → | link OKF terms to Dataplex entries (table/column) |
| `data-profile-scan-create-and-run` | — | Create & run Dataplex Data Profile scan, link to BQ |
| `data-profile-scan-list` | — | List/get Dataplex Data Profile scan configurations/results |
| `data-insights-create-and-run` | — | Create & run Dataplex Data Insights scan, link to BQ |
| `data-insights-list` | — | List/get Dataplex Data Insights scan configurations/results |

> **Authoring the CA agent definition** (system prompt, table list, golden queries)
> is done via the prompt-driven flow in
> `docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-*.md`
> (fed by `docs/requirements/Business-Requirements/` + OKF), producing
> `okf-staging/conversational-analytics/*`. The `conversational-analytics` skill then
> **deploys** from that staging output.

## conversational-analytics — the serving layer (runtime)

**`conversational-analytics`** is the standalone node that *consumes* a curated
table list + context to build, deploy, and run the CAI (NL2SQL) agent. It is
**self-contained and portable** — copy the folder to any project; its runtime code
takes project/dataset/region/model as parameters and has **no dependency on this
repo or on OKF** (see its `SKILL.md` → "Using this skill in another project").

### Dependency direction (important)

The system feeds the CAI skill; the CAI skill never reaches back:

```
okf/ + OKF skills  ──feeds──▶  conversational-analytics   (correct)
conversational-analytics  ──✗──▶  okf/ / repo             (never)
```

The OKF-produced layer maps cleanly onto the CAI skill's generic builders:

- OKF table/column descriptions → `ca.build_table_references(..., schema_context=)`
- OKF glossary terms → `ca.build_glossary_terms(...)`
- OKF metric SQL (BQ-ready) → `ca.build_example_queries(...)`

That mapping lives **outside** the skill, in the repo-side bridge
`conversational-analytics/evals/deploy_ca_from_okf.py`, which reads a structured OKF
agent-def YAML (`okf/conversational-analytics/<agent>.md`, produced by the
`ca-generate-*` → `ca-okf-staging-to-okf` prompt flow) and *calls* the skill's generic
builders → `create_or_update_data_agent`. Project/dataset resolve from `agent-config.json`
(or an arg), so one agent def deploys to any project. The skill stays OKF-unaware.

### Authoring the CA agent definition (upstream of the skill)

The CA agent's system prompt, table list, and golden queries are authored by the
**prompt-driven flow** in `docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-*.md`
(fed by `docs/requirements/Business-Requirements/` + OKF tables/metrics/glossary + the test
prompts), which writes `okf-staging/conversational-analytics/*`. The
`conversational-analytics` skill consumes that staging output to **deploy** the agent.
The skill stays **standalone and OKF-unaware**; the "structure the staging → deploy"
step is a bridge/handoff (format TBD — see planning notes).

## agent-quality — the trust layer (acceptance · observability · evaluation)

**`agent-quality`** is the "trust trio": the three capabilities a forward engineer
uses to get an enterprise to *trust* a CA agent in production. It picks up exactly
where the OKF authoring system stops — at agent **create/update** — and never modifies
the agent (sibling → CAI direction, correct). It absorbs the earlier
`agent-observability` skill.

```
                    agent-quality — the trust trio
     (build enterprises' confidence to run CAI in production)

  create/update ─────────────┐  ← the boundary the OKF system stops at
   a CA agent                │
                             ▼
              per-mode retrieval (from the CAI skill)
              stateful : list_conversations → get_conversation_turns  (native, no ADK)
              inline   : persisted tracer
              adk      : agent_events plugin
                             │
                produces rows: {question, agent_response,
                                ground_truth, expectation_type}
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                         ▼
 ACCEPTANCE             OBSERVABILITY              EVALUATION
 sync gate at create    deferred job:             deferred / scheduled:
 golden Qs from the     latency · errors ·        grade the rows
 acceptance OKF         volume                          │
 pass / fail                                            │
                                        ┌───────────────┴───────────────┐
                                        ▼                               ▼
                                  MANUAL tier                     MANAGED tier
                             BigQuery AI functions            Vertex Gen AI Eval
                             AI.SCORE   → answer              read BQ rows → judge
                             GENERATE_BOOL → clarify/refuse   → write results back
                             AI.CLASSIFY → triage             (BYOR, rubrics, trend)
                             grades IN the warehouse                 │
                                        │                            │
                                        └────────► BigQuery ◄────────┘
                                            rows table + results table
                                        (system of record for both tiers;
                                         manual grades in-place · managed
                                         reads/prepares → grades → writes back)
```

- **Acceptance** (sync gate) — right after create/update, run the golden questions
  from the **acceptance OKF** (a first-class OKF file authored alongside the agent
  def by the `ca-generate-acceptance` prompt, e.g.
  `okf/conversational-analytics/premium-outdoor-gear-acceptance.md`) and grade
  pass/fail per `expectationType` (answer / clarification / refusal).
- **Observability** (deferred) — harvest turns per mode (**stateful uses native
  `list_conversations → get_conversation_turns`, no ADK required**; inline via a
  persisted tracer; embedded ADK via the `agent_events` plugin) and report latency /
  errors / volume. Clarify-then-answer chains can be **stitched** into one logical
  exchange (structural, no business knowledge). *(Absorbs the former
  `agent-observability` skill, now removed — its ADK-plugin trace evaluation lives
  here as the PLUGIN path.)*
- **Evaluation** (deferred/scheduled) — grade `{question, agent_response,
  ground_truth, expectation_type, generated_sql}` rows via **two tiers over the same
  BigQuery tables**: a **manual** tier that grades *in-warehouse* with BigQuery AI
  functions (`AI.SCORE`, `AI.GENERATE_BOOL`, `AI.CLASSIFY` — data never leaves BQ;
  Preview functions), and a **managed** tier that hands the rows to Vertex Gen AI
  Eval (BYOR) → writes results back. BigQuery stays the system of record for both.
  The manual tier adds depth: **result-outcome grading** (`grade_results` executes
  the golden SQL and compares to the agent's captured data — exact / containment /
  derivable — because SQL *text* is only a proxy: different SQL can yield identical
  results, a wider result can contain the answer, or one query returns info to
  *derive* it), with **SQL-text equivalence** as the no-execution fallback;
  **reference-free** scoring + **answer-vs-own-data consistency** for production
  traffic with no ground truth; **classify-then-grade** (`AI.CLASSIFY` buckets
  unlabeled turns as answered/clarified/refused/hedged/errored before grading); and
  optional **OKF-knowledge injection** so grading is business-aware.

**Approach → metadata it uses** (the contract; full table in `agent-quality/SKILL.md`):

| Approach | Metadata IN | Where it comes from |
|---|---|---|
| Acceptance | `question`, `expectation_type`, `ground_truth` + live `agent_response`, `generated_sql`, `followups`, `thoughts`, `data` | acceptance OKF + the agent's response |
| Observability (native) | `question`, `agent_response`, `generated_sql`, `timestamp`, `conversation` | stateful history (`list_conversations`→`get_conversation_turns`) |
| Observability (ADK) | latency, errors, per-tool trajectory, tokens | `agent_events` table (ADK plugin) |
| Evaluation | the rows above + optional `knowledge` (OKF glossary + golden SQL) | producers above + OKF |

Grading keys per row on what's present, correctness strongest-first: golden SQL +
captured `data` → **result-outcome** (execute + compare); `generated_sql` + golden SQL →
**SQL-text equivalence** (fallback); `ground_truth` (no SQL) → **reference-based score**;
no `ground_truth` → **reference-free** + **answer-vs-own-data**; `expectation_type` →
clarification / refusal checks; unlabeled → `AI.CLASSIFY` triage first.

Lab = run-later by a CE; production = a scheduled cloud job. Full detail:
`agent-quality/SKILL.md` + `agent-quality/references/grader-tiers.md`.

### agent-quality vs. `lab-evaluation-verifier` (two different "evaluations")

The repo has **two evaluation systems on orthogonal axes** — don't conflate them:

| | `agent-quality` (this skill) | `lab-evaluation-verifier/` (repo microservice) |
|---|---|---|
| **Grades** | the deployed **CA agent's answers** (is it correct/trustworthy?) | the **student's lab submission** (did the learner build it right?) |
| **Question** | "is the built agent production-ready?" | "did this CE complete lab step N?" |
| **For** | forward engineers gating an agent | instructors/students (web portal + PASS/FAIL) |
| **Form** | portable skill, runs anywhere | deployed Cloud Run services + BigQuery config tables |

They're **complementary**: the lab verifier checks the learner *produced* the golden
queries / system prompt / deployment; `agent-quality` checks the *resulting agent*
actually answers correctly. Same source artifacts, two lenses (learner vs. agent).
The lab verifier lives entirely under `lab-evaluation-verifier/` and is not a skill.

## skill-creator — meta skill for skill authoring, evaluation, and optimization

**`skill-creator`** is a meta-skill for creating, editing, testing, benchmarking, and optimizing agent skills. It provides workflows to:
- **Capture intent & draft skills**: Interview users or analyze workflows to generate standard `SKILL.md` instructions and bundled scripts/assets.
- **Run parallel test prompts**: Execute test cases concurrently across subagents (with-skill vs. baseline) to record token counts, runtime duration, and outputs.
- **Grade & visualize benchmarks**: Evaluate quantitative assertions and launch an interactive web review dashboard (`eval-viewer/generate_review.py`) for human feedback.
- **Optimize skill triggering**: Automatically generate edge-case trigger queries and run optimization loops (`scripts/run_loop.py`) to tune `SKILL.md` frontmatter descriptions.

## agents-cli — optional external dev tooling (not a skill here)

`google/agents-cli` is a **developer-workstation** tool (a bundle of 7 ADK-lifecycle
coding-assistant skills: scaffold / adk-code / eval / deploy / publish / observability
/ workflow), installed with `uvx google-agents-cli setup`. It is **not part of this
repo's skills and not part of `deploy.sh`** (which is Terraform infra only). Reach for
it only if repo scope grows to *shipping a custom ADK agent* to the Gemini Enterprise
Agent Platform — then it scaffolds/deploys/publishes that agent. CA data agents don't
need it (they publish to Gemini Enterprise directly as managed resources). See
`conversational-analytics/references/ecosystem-integration.md`.

## Conventions

- Each skill is a self-contained folder: `SKILL.md` (frontmatter drives triggering)
  + `scripts/run.py` returning `{status, tool_name, messages, results}`, mostly REST
  against Google Cloud APIs with ADC.
- Skills with complex multi-component implementations—`conversational-analytics` (runtime serving layer), `agent-quality` (trust trio & two-tier evaluation), and `skill-creator` (meta-skill tooling & benchmark viewer)—include extended directories (`references/`, `tests/`, `evals/`, `agents/`, etc.). `conversational-analytics` also includes `pyproject.toml` (uv) and `DESIGN.md`. The OKF converter skills are focused, single-backend wrappers where `SKILL.md` + `scripts/` is the right size; the absence of tests/evals on those is by design, not an omission. Portable CAI best-practices: `docs/requirements/Conversational-Analytics-Best-Practices/ca-best-practices.md`.
