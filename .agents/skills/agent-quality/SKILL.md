---
name: agent-quality
description: Build enterprise trust in a Conversational Analytics (or ADK) agent through three capabilities — acceptance testing (gate an agent on golden questions right after create/update), observability (harvest and summarize real runtime turns), and evaluation (grade responses against ground truth with a two-tier grader). Use this skill when the user wants to test, gate, monitor, evaluate, or measure the quality/latency/correctness of a CA data agent; run acceptance/golden-question suites; collect what a deployed agent actually answered; or grade agent responses in BigQuery (AI functions) or Vertex Gen AI Evaluation. Absorbs the former agent-observability skill.
---

# Skill: Agent Quality (the trust trio)

The three capabilities a forward engineer uses to get an enterprise to **trust** a
Conversational Analytics agent in production. It picks up exactly where the OKF
authoring system stops — at agent **create/update** — and never modifies the agent
(it points at agents built by the `conversational-analytics` skill).

- **Acceptance** — *is it correct on the questions we care about?* A synchronous
  gate run right after create/update, on a golden set.
- **Observability** — *what is it doing in production?* Harvest real turns and
  summarize volume / errors / SQL execution.
- **Evaluation** — *is it measurably good, and staying good?* Grade rows with a
  two-tier grader; schedule it to watch drift.

> **Not to be confused with `lab-evaluation-verifier/`.** That repo microservice
> grades the *student's lab submission* (did the learner build the OKF, deploy the
> agent, etc.); this skill grades the *deployed agent's answers*. Orthogonal axes —
> learner vs. agent. See the skills README for the side-by-side.

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

The trust trio's currency is a **row**:
`{question, agent_response, ground_truth, expectation_type}`. Acceptance and
observability *produce* rows; the graders *consume* them — so the same grader scores
a golden acceptance set and live production traffic.

## Dependencies (direction matters)

This skill **depends on** the `conversational-analytics` skill to talk to agents
(acceptance sends questions; native observability reconstructs turns). That's the
correct direction — quality points at agents the CAI skill builds and never the
reverse. All heavy deps (BigQuery, Vertex, the CAI skill, the ADK analytics SDK) are
imported **lazily**, so importing this skill is cheap and each path pulls only what
it needs.

## Usage

```python
import sys, os
sys.path.append(os.path.abspath('.agents/skills/agent-quality/scripts'))
import run

P, LOC, AGENT = "my-project", "global", "premium-outdoor-gear-agent"

# 1) ACCEPTANCE — gate right after create/update
cases  = run.parse_acceptance_set("okf/conversational-analytics/premium-outdoor-gear-acceptance.md")
ran    = run.run_acceptance(P, LOC, AGENT, cases["results"]["cases"])

# 2) EVALUATION (manual tier) — grade in BigQuery, results stay in-warehouse
graded = run.grade_manual(ran["results"]["rows"],
                          rows_table=f"{P}.agent_quality.rows",
                          results_table=f"{P}.agent_quality.results")
print("pass rate:", graded["results"]["summary"]["pass_rate"])

# 2b) EVALUATION (managed tier) — same rows via Vertex, BQ in / BQ out
# graded = run.grade_managed(ran["results"]["rows"],
#                            results_table=f"{P}.agent_quality.vertex_results")

# 3) OBSERVABILITY — what did the deployed agent actually answer? (native, no ADK)
turns = run.collect_agent_turns(P, LOC, AGENT)
print(run.summarize_turns(turns["results"]["rows"])["results"]["summary"])
```

Every function returns the house-standard dict:
`{"status", "tool_name", "messages", "results"}` (`status` is `"success"` /
`"failed"`).

## Approaches & the metadata each uses

The trust trio has three *approaches* (when/how it engages the agent) and the
evaluation approach has several *grading paths*. Each consumes specific metadata —
some from the agent's live response, some from the acceptance OKF, some from an ADK
events table. This table is the contract:

| Approach | When | Metadata IN (source) | Metadata OUT |
|---|---|---|---|
| **Acceptance** (`run_acceptance`) | agent create/change (sync gate) | `question`, `expectation_type`, `ground_truth` ← acceptance OKF; **live from the agent**: `agent_response`, `generated_sql`, `followups`, `thoughts`, `data` | gradable rows (full trace) |
| **Observability — native** (`collect_agent_turns`) | deferred (real traffic) | `question`, `agent_response`, `generated_sql`, `timestamp`, `conversation` ← stateful history (`list_conversations`→`get_conversation_turns`); optional `stitched`, `clarifications` | rows (no `ground_truth` — production) |
| **Observability — ADK plugin** (`list_traces`/`evaluate_latency`/`judge_correctness`/`match_trajectory`) | deferred (embedded ADK) | `agent_events` BigQuery table (latency, errors, per-tool trajectory, tokens) ← ADK BigQuery Agent Analytics plugin | trace lists, SLO/judge/trajectory reports |
| **Evaluation** (`grade_manual`/`classify_and_grade`/`grade_managed`) | deferred/scheduled | the rows above + optional `knowledge` (OKF glossary + golden SQL) | graded rows + pass/fail summary |

### Grading paths (evaluation), and the metadata each keys on

The grader picks a path **per row** from the metadata present:

| Grading path | Fires when | Metadata used | Signal |
|---|---|---|---|
| **Result outcome** (`grade_results`, opt-in — executes golden SQL) | `answer` with a SQL `ground_truth` AND captured `data` | `ground_truth` (golden SQL, executed) + agent `data`; `question`+`agent_response` for the tier-3 judge; `knowledge` | **strongest — grades the RESULT, not the query.** exact / containment / value-containment (provable) → `derivable` (LLM over results) → mismatch |
| **SQL-equivalence** (`AI.GENERATE_BOOL`) — *fallback, no execution* | `answer` AND `generated_sql` present AND `ground_truth` looks like SQL | `question`, `generated_sql`, `ground_truth` (golden SQL), `knowledge` | grades whether two queries *look* like the same goal (weaker than result outcome) |
| **Reference-based score** (`AI.SCORE`) | `answer` with a `ground_truth`, no SQL | `question`, `agent_response`, `ground_truth`, `knowledge` | correctness vs reference (pass ≥ 7/10) |
| **Reference-free score** (`AI.SCORE`) | `answer`, **no** `ground_truth` (production) | `question`, `agent_response`, `knowledge` | quality/coherence (can't check correctness) |
| **Answer-vs-own-data** (`check_answer_consistency`, `AI.GENERATE_BOOL`) | production turns, no reference, with `data` | `question`, `agent_response`, agent `data` | is the stated answer supported by the rows the agent itself got? (the honest no-reference correctness check) |
| **Clarification** (`AI.GENERATE_BOOL`) | `expectation_type=clarification` | `question`, `agent_response`, `followups`, `ground_truth` (the `mustAsk`) | did it ask the right disambiguation? |
| **Refusal / governance** (`AI.GENERATE_BOOL`) | `expectation_type=refusal` | `question`, `agent_response`, `ground_truth` (the `mustRefuse`/mask rule) | declined OR masked = pass; raw PII = fail |
| **Clarification-then-answer** (multi-turn) | `expectation_type=clarification_then_answer` | turn-1 `clarification_response` + `must_ask`; resolved `agent_response`/`generated_sql`/`data` + `ground_truth` | ask AND resolved-answer both correct |
| **Response-shape triage** (`AI.CLASSIFY`) | unlabeled rows (`classify_and_grade`) | `question`, `agent_response` (+ structural: is a `?` present) | answered/clarified/refused/hedged/errored → derives `expectation_type` |

**Correctness signal hierarchy (strongest first):** result-outcome comparison
(`grade_results`) → SQL-text equivalence (fallback) → prose score. Grade the outcome
when you can; SQL text is only a proxy — different SQL can yield identical results, a
wider result can still contain the answer, and one query may return the info to
*derive* the answer. `grade_results` handles all three (exact / containment /
derivable); it executes the golden SQL so it's opt-in and capped with
`maximum_bytes_billed`.

Notes: `thoughts`/`data` are captured for **diagnostics**; `data` is also the input
to `grade_results` and `check_answer_consistency` but is *not* loaded into the
`build_grading_sql` BQ table (that path keys only on its columns). Per-tool
**trajectory** and **token cost** are ADK-plugin-only — a stateless acceptance or
native-observability run cannot see them. `knowledge` is optional everywhere; when
supplied it makes every judge prompt business-aware.

## Areas & functions

### Acceptance (`acceptance.py`)
| Function | Purpose |
|---|---|
| `parse_acceptance_set(path)` | Parse an acceptance OKF file → test cases `[{id, question, category, expectation_type, ground_truth, notes}]` |
| `run_acceptance(project, location, agent_id, cases)` | Run each case against a stored agent (stateless `agent` mode) → gradable rows capturing the **full trace** |

**Run acceptance when a CA agent is created or changed** — it's the synchronous
gate. Each case captures the full trace of the turn, not just the answer text:
`agent_response`, `generated_sql`, `followups`, `thoughts`, `data`. Capturing
`generated_sql` is what lets the grader use **SQL-equivalence** on `answer` cases
that carry golden SQL (the strong correctness signal) — e.g. it will *fail* an
answer whose prose looks right but whose SQL computed the wrong thing
(list-the-islands vs count-the-islands). `thoughts`/`data` are kept for failure
diagnostics. (The only trace signal a stateless run can't capture is the per-tool
ADK trajectory, which needs the ADK plugin and acceptance doesn't require.)

The acceptance set is a **first-class OKF file authored alongside the agent def**
by the `ca-generate-acceptance` prompt
(`docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-acceptance-prompt.md`),
e.g. `okf/conversational-analytics/premium-outdoor-gear-acceptance.md`. Its schema:
`testCases[{id, question, category, expectationType, groundTruth{sql|mustAsk|
mustRefuse|followUpUserResponse}, notes}]`.

The four `expectation_type`s decide how a case is graded:
- `answer` — correct data answer (SQL-equivalence when golden SQL is present, else
  prose score).
- `clarification` — agent must *ask*, not answer.
- `refusal` — agent must *decline* or mask (out-of-bounds/PII).
- `clarification_then_answer` — **multi-turn**: the agent must ask (`mustAsk`),
  then given the simulated user reply (`followUpUserResponse`) produce the correct
  answer (golden `sql`). `run_acceptance` drives both turns; grading requires the
  ask AND the resolved answer to be correct.

### Observability (`observability.py`)
| Function | Purpose |
|---|---|
| `collect_agent_turns(project, location, agent_id)` | **NATIVE** (stateful, no ADK): `list_conversations` → `get_conversation_turns` → gradable rows |
| `summarize_turns(rows)` | Cheap no-LLM operational view: volume, error rate, SQL-execution rate |
| `list_traces / evaluate_latency / judge_correctness / match_trajectory` | **PLUGIN** (embedded ADK): over a BigQuery `agent_events` table (absorbed from agent-observability) |

Two retrieval paths because not every CA agent runs in ADK. A plain deployed CA
data agent stores its own history, so `collect_agent_turns` gets real Q&A with **no
extra capture infra**. Embedded ADK agents use the BigQuery Agent Analytics plugin
(one line in the ADK app) and the `*_traces` / evaluators.

> **What each path can see.** Native (stateful) turns carry: question, final
> answer, generated SQL, reasoning/thoughts, timestamps, data rows. They do **not**
> carry per-tool trajectory or token cost — those are ADK-plugin only. Multi-turn
> conversations are split per user message (N exchanges → N turns).
>
> **Clarify-then-answer.** In production, a turn may be a clarifying question rather
> than an answer. Two portable, no-business-knowledge mechanisms handle it:
> - `collect_agent_turns(..., stitch=True)` (or `stitch_exchanges`) folds a
>   clarify-then-answer chain into one logical exchange — original question, final
>   resolved answer, with the intermediate clarification(s) recorded. Capped by
>   `max_span` so a long clarify loop can't swallow a conversation; applied
>   per-conversation so it never spans conversations.
> - `classify_and_grade` labels each turn's *shape* (`AI.CLASSIFY`) so a genuine
>   clarify-turn is judged as a clarification, not a failed answer.
>
> Acceptance sidesteps this entirely by sending clarification cases stateless (one
> turn to judge).

### Evaluation — the two-tier grader (`grader.py`)
| Function | Tier | Purpose |
|---|---|---|
| `grade_results(rows, ...)` | manual (opt-in) | **Outcome grading** — execute the golden SQL (capped), compare to the agent's captured `data`: exact/containment/value-containment (provable) → derivable (LLM over results). The strongest correctness path. |
| `check_answer_consistency(rows, ...)` | manual | **No-reference** — is the production answer consistent with the agent's OWN `data`? |
| `build_grading_sql(rows_table, results_table, knowledge=, grade_sql=)` | manual | The BigQuery AI-functions grading SQL (SQL-text/prose paths; inspect or schedule it) |
| `grade_manual(rows, rows_table, results_table, knowledge=)` | manual | Load rows → run the SQL → graded results (all in BigQuery). For **labeled** rows. |
| `classify_and_grade(rows, rows_table, classified_table, results_table)` | manual | For **unlabeled** production turns: `AI.CLASSIFY` the response shape → derive expectation_type → grade. |
| `grade_managed(rows, results_table=...)` | managed | Vertex Gen AI Eval (BYOR); reads rows, judges, writes metrics back to BQ |

**Both tiers consume the same rows and write to BigQuery**, so they're comparable.

- **Manual** grades *in the warehouse*:
  - `answer` correctness — **prefer `grade_results`** (grade the RESULT: execute the
    golden SQL, compare to the agent's captured data — exact/containment/derivable);
    fall back to **SQL-text equivalence** in `build_grading_sql` (`AI.GENERATE_BOOL`,
    no execution) or `AI.SCORE` on the prose when there's no SQL;
  - `answer` with **no** reference (production) → `AI.SCORE` **reference-free** +
    `check_answer_consistency` (answer vs its own data);
  - `clarification`/`refusal` → `AI.GENERATE_BOOL` (“did it ask?” / governance:
    “declined or masked?”); `clarification_then_answer` → both halves.
  - Pass `knowledge=` (OKF glossary + golden SQL) to make grading **business-aware**.
  Data never leaves BigQuery, and it's a schedulable BQ job. `grade_results`
  *executes* the golden SQL (read-only, `maximum_bytes_billed` cap) so it's opt-in.
  *(AI.SCORE / AI.GENERATE_BOOL / AI.CLASSIFY are Preview — fine for a lab; note for
  prod.)*
- **Managed** uses Vertex's managed judges/rubrics and experiment tracking; Vertex
  can't invoke a CA agent, so it grades pre-generated responses (BYOR). We read the
  rows from BigQuery, hand them to Vertex, and write the metrics table back.

## When to run what (the lifecycle)

- **Acceptance** — synchronously, the moment an agent is created/updated. It needs
  only the golden set, which exists before any traffic. This is the gate.
- **Observability & Evaluation** — deferred: traffic accrues over time, so run
  these later / on a schedule (a BQ scheduled query for the manual tier; a
  scheduled job for Vertex). In the lab a CE runs them by hand; in production
  they're a scheduled cloud job.

## Install

`scripts/requirements.txt` lists deps per path — install only what you use:
- Core + acceptance/native-observability: `pyyaml` + the CAI skill's requirements.
- Manual grader tier: `google-cloud-bigquery`.
- Managed grader tier: `google-cloud-aiplatform[evaluation]`, `pandas`, `pandas-gbq`.
- Plugin observability: `bigquery-agent-analytics[llm]`.

Auth is ADC (current user), matching the CAI skill's OAuth pass-through rule.

## Project layout

```
agent-quality/
├── SKILL.md
├── pyproject.toml          # uv dev/test environment
├── scripts/
│   ├── run.py              # one import → all three areas
│   ├── acceptance.py       # gate on golden questions
│   ├── observability.py    # native turns + ADK-plugin traces
│   ├── grader.py           # two-tier grader (BQ AI funcs / Vertex)
│   ├── common.py           # row shape + house-standard helpers
│   └── requirements.txt
├── references/             # grader-tiers deep dive, acceptance-set format
└── tests/                  # offline suite (fakes) + opt-in live
```

## References

- Two-tier grader deep dive: [references/grader-tiers.md](references/grader-tiers.md)
- Acceptance-set OKF: the `ca-generate-acceptance` prompt
  (`docs/requirements/Conversational-Analytics-Best-Practices/ca-generate-acceptance-prompt.md`)
  + example `okf/conversational-analytics/premium-outdoor-gear-acceptance.md`
- BigQuery AI functions: [AI.SCORE](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-score),
  [AI.GENERATE_BOOL](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-bool),
  [AI.CLASSIFY](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-classify)
- Vertex Gen AI Evaluation: https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview
- BigQuery Agent Analytics plugin (ADK): https://adk.dev/integrations/bigquery-agent-analytics/
- Sibling skill it points at: `.agents/skills/conversational-analytics/`
