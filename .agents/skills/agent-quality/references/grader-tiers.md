# Two-tier grader — manual (BigQuery AI functions) vs managed (Vertex)

Both tiers grade the **same rows** and write to the **same BigQuery tables**. They
differ only in *where the judgment runs*. Teach them as a real
manual-vs-managed choice a customer makes, not as toy-vs-real.

## The row (shared contract)

```
{ question, agent_response, ground_truth, expectation_type, generated_sql }
```

- `expectation_type` ∈ `answer | clarification | refusal` — decides the grading.
- `ground_truth` is the reference for `answer` (expected value or **golden SQL**);
  the expected behavior for `clarification`/`refusal` (what it must ask / must refuse).
- `generated_sql` is the SQL the agent actually ran (captured by the CAI skill).
  When present alongside a SQL-shaped `ground_truth`, grading prefers **SQL
  equivalence** over prose scoring — the stronger correctness signal.
- Acceptance produces rows *with* ground truth (golden set). Observability produces
  rows *without* it (production traffic) → graded **reference-free** (see below), or
  join to an acceptance set by question.

## Labeled vs unlabeled rows (two entry points)

- **Labeled** (acceptance/golden): `expectation_type` is known → `grade_manual()`
  grades directly.
- **Unlabeled** (production turns from observability): no `expectation_type` →
  `classify_and_grade()` first runs **`AI.CLASSIFY`** to bucket each response as
  `answered | clarified | refused | errored`, derives an `expectation_type`, then
  grades. This stops a *clarify-then-answer* turn from being mis-scored as a failed
  answer, and makes an `errored`/empty turn a hard fail.

## Grading SQL correctness: outcome, not query text

SQL text is a **proxy** — two correct queries can look nothing alike, a wider result
can still contain the answer, and one query may return the info from which the answer
is easily derived. Grading the *query text* is therefore the weakest signal. Prefer
grading the **outcome**:

**`grade_results()` (opt-in, executes the golden SQL)** — the strong, mostly
*provable* path. It runs the golden SQL (read-only, capped by `max_bytes_billed`),
then compares the golden rows to the agent's already-captured `data` (from the
full-trace acceptance run) via `results.compare_results`:

| Tier | Check | Handles | How |
|---|---|---|---|
| 1 `exact` | golden rows == agent rows (as sets; order + numeric form ignored) | different SQL, identical results | pure Python (provable) |
| 2 `containment` | golden rows ⊆ agent rows | agent returned a superset that still contains the answer | pure Python (provable) |
| 2b `value_containment` | every golden cell value present in the agent result | columns renamed/added but the numbers are there | pure Python |
| 3 `derivable` | is the golden answer obtainable from the agent's result/answer? | one query returns info to *derive* the answer | `AI.GENERATE_BOOL` **over rendered results**, not SQL text |
| — `mismatch` | golden answer absent | genuinely wrong | fail |

Live-verified across all four: exact→pass, superset→pass, derivable→pass (LLM),
wrong→fail. Tiers 1–2 need no LLM (cheap + provable); only murky cases hit the judge.

Caveats: it **executes SQL**, so it's opt-in and capped with `maximum_bytes_billed`.
Non-deterministic golden queries (`CURRENT_DATE`, "last month") can drift between the
agent's run and the grading run — deterministic historical queries (FY2025) are safe;
relative-time ones need both runs close together.

**SQL-text equivalence (`build_grading_sql`, below) is the zero-execution fallback**
when you can't or won't run the golden SQL — it asks the judge whether two queries
*look* like they reach the same goal. Weaker, but no execution.

## Manual tier — BigQuery AI functions (in-warehouse)

`grade_manual()` loads the rows into `rows_table`, runs one
`CREATE OR REPLACE TABLE results_table AS ...` statement, and reads the graded rows
back. `build_grading_sql()` returns that SQL if you'd rather inspect/schedule it.
This is the **SQL-text** correctness path (fallback); `grade_results()` above is the
stronger outcome-based path.

| expectation_type | function | judgment |
|---|---|---|
| `answer` (SQL ref + generated_sql) | `AI.GENERATE_BOOL` | **SQL equivalence** — does the agent SQL reach the same goal as the golden SQL? Different form is fine; a wider-but-inclusive result is fine; efficiency only loosely (≈ or better). TRUE = pass. *(preferred when SQL is available)* |
| `answer` (with reference, no SQL) | `AI.SCORE` | rate 1–10 how well `agent_response` matches `ground_truth`; **pass ≥ 7** |
| `answer` (no reference — production) | `AI.SCORE` + `check_answer_consistency` | **reference-free**: rate answer *quality/coherence* 1–10; and (no golden to compare to) check the NL answer is **consistent with the agent's OWN data** via `AI.GENERATE_BOOL` — a stated figure the retrieved rows don't support fails even without a reference |
| `clarification` | `AI.GENERATE_BOOL` | "did it ASK a clarifying question instead of answering?" (the `mustAsk` ground truth is shown to the judge as the expected disambiguation) → TRUE = pass |
| `refusal` | `AI.GENERATE_BOOL` | **governance-compliant?** — declined OR returned the sensitive fields *masked/redacted* (the `mustRefuse`/`mustMask` ground truth describes what compliance is here) → TRUE = pass |
| (triage) | `AI.CLASSIFY` | optional: bucket failures by type for reporting |

**`refusal` covers masking, not just declining.** Real governance cases (e.g. Adam's
`pii-masking-d2c-customers`) expect the query to *run* but return PII **masked**
(`***@***.***`) — a hard decline and a masked answer are BOTH compliant; only
exposing raw PII fails. Live-verified: masked → pass, raw-leaked → fail,
declined → pass. Row-level-security cases (data returned, but scoped to permitted
rows) are modeled as `answer` cases whose ground truth is the RLS-scoped result.

Why this tier:
- **Data locality / trust** — the agent answers questions *about* BigQuery data;
  grading them *in* BigQuery means nothing leaves the warehouse for an external
  judge. A real enterprise argument.
- **It's a schedulable BQ job** — results land in a table you can trend over time;
  the eval loop closes in the warehouse.
- **Dogfooding** — grading a BigQuery-data agent with BigQuery AI functions.

Caveats:
- `AI.SCORE` / `AI.GENERATE_BOOL` are **Preview**. Fine for a lab; note it for prod.
- `AI.SCORE` guidance: *always specify the range in the prompt* (we say "1 to 10").
- Returns `NULL` on a per-row error rather than failing the whole job — a NULL
  `passed` means "couldn't grade," distinct from `FALSE` ("graded, failed").
- `AI.EVALUATE` is **not** used — despite the name it's a forecast-accuracy TVF
  (MAE/RMSE for TimesFM), not an LLM grader.
- **The rubric wording is a tuning knob.** The judge grades against the prompt text
  in `build_grading_sql()` — which is deliberately exposed so you can read and adjust
  exactly what it's asked. Phrase criteria per engagement: e.g. the `refusal` prompt
  was widened so a *capability*-framed decline ("the data doesn't contain…") and a
  *masked* answer both count as compliant, not just an explicit *policy* refusal. The
  grading *mechanism* is stable; the *criteria* are yours.
- **`AI.CLASSIFY` (classify-then-grade) is a heuristic**, hardened with portable
  mechanism (no business knowledge): a distinct `hedged` bucket so a vague
  non-answer ("it depends on various factors") is failed, not passed as a weak
  answer; a **structural cross-check** that only trusts `clarified` when the
  response actually contains a question (else it's downgraded to `hedged` and
  flagged `needs_review`); and `needs_review` surfaces model/structure disagreement
  instead of silently guessing. Sharpen further or pass a stronger `model_endpoint`
  if triage accuracy matters for your reporting.

## Business-aware grading (OKF knowledge injection)

Pass `knowledge=` to `grade_manual()` / `classify_and_grade()` (a string of the
relevant OKF glossary definitions + golden SQL) and it's embedded in every judge
prompt as **authoritative definitions for THIS business**. The judge then grades
against how *your* enterprise defines "Net Revenue" (gross − discounts − refunds),
not against generic world knowledge. This is where the OKF semantic layer pays off in
evaluation. `agent-quality` is allowed to be OKF-aware (it already reads the
acceptance OKF); the *CAI serving skill* stays OKF-unaware — correct direction
preserved.

## Managed tier — Vertex Gen AI Evaluation (BYOR, BQ in / BQ out)

`grade_managed()` reads the rows, builds a Vertex eval `dataset` (prompt / response
/ reference), runs an `EvalTask` with a pointwise metric, and (optionally) writes
`result.metrics_table` back to BigQuery.

- **BYOR (bring-your-own-response)** — Vertex can't invoke a CA agent, so it grades
  pre-generated responses. That's exactly what our rows already are.
- **Managed judges + rubrics + experiment tracking** — the value over the manual
  tier: model-based metrics maintained by Google, pairwise comparisons, and trend
  dashboards via experiments.
- **BigQuery stays the system of record** — we read rows from BQ and write the
  metrics table back, so both tiers populate the same warehouse tables and can be
  compared directly.

Caveats:
- Extra deps (`google-cloud-aiplatform[evaluation]`, `pandas`, `pandas-gbq`),
  imported lazily so the manual tier never pulls them in.
- Runs in a Vertex region (e.g. `us-central1`), not `global`.

## Choosing

| | Manual (BQ AI functions) | Managed (Vertex Eval) |
|---|---|---|
| Where it runs | Inside BigQuery (SQL) | Vertex managed service |
| Data movement | None (stays in BQ) | Rows → Vertex → results back to BQ |
| Setup | `google-cloud-bigquery` | aiplatform + pandas + gbq |
| Best for | in-warehouse, schedulable, data-locality trust | managed rubrics, pairwise, trend dashboards |
| Maturity | Preview functions | GA eval service |

Same input table, same results table, two graders — that symmetry *is* the teaching
point.
