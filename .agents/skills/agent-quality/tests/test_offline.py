"""Offline tests for agent-quality — no network. Fast default suite.

Covers: row normalization, acceptance harness (via a fake CA), the manual-tier
grading SQL builder, the pass/fail summary, and native observability turn
collection. Vertex / bigquery-agent-analytics / real BigQuery are not exercised
here (they're live-only or injected).
"""

from conftest import FakeCA


# --- common -----------------------------------------------------------------

def test_normalize_rows_fills_and_coerces():
    import common
    rows = common.normalize_rows([
        {"question": "q1"},                              # missing keys
        {"question": "q2", "expectation_type": "bogus"},  # bad type -> answer
        {"question": "q3", "expectation_type": "refusal"},
    ])
    assert rows[0]["ground_truth"] is None
    assert rows[0]["expectation_type"] == "answer"
    assert rows[1]["expectation_type"] == "answer"
    assert rows[2]["expectation_type"] == "refusal"


def test_resolve_project_dataset_defaults(monkeypatch):
    import common
    monkeypatch.setattr(common, "load_env_config", lambda *a, **k: {})
    p, d = common.resolve_project_dataset("proj")
    assert p == "proj" and d == "agent_quality"


# --- acceptance -------------------------------------------------------------

def test_run_acceptance_builds_gradable_rows():
    import acceptance
    ca = FakeCA(answers={
        "What was Net Revenue?": {"text": "$1.2M", "followups": [],
                                  "generated_sql": "SELECT SUM(x) FROM sales",
                                  "thoughts": ["computing net revenue"],
                                  "data": [{"rev": 1200000}]},
        "What was profit?": {"text": None,
                             "followups": ["Gross or net profit?"]},
    })
    cases = [
        {"id": "rev", "question": "What was Net Revenue?", "category": "Baseline",
         "expectation_type": "answer", "ground_truth": "1200000"},
        {"id": "amb", "question": "What was profit?", "category": "Clarify",
         "expectation_type": "clarification", "ground_truth": "must ask"},
    ]
    r = acceptance.run_acceptance("p", "global", "agent-x", cases, ca=ca)
    assert r["status"] == "success"
    rows = r["results"]["rows"]
    assert rows[0]["agent_response"] == "$1.2M"
    assert rows[0]["expectation_type"] == "answer"
    # full trace captured so SQL-equivalence grading + diagnostics can fire
    assert rows[0]["generated_sql"] == "SELECT SUM(x) FROM sales"
    assert rows[0]["thoughts"] == ["computing net revenue"]
    assert rows[0]["data"] == [{"rev": 1200000}]
    assert rows[1]["followups"] == ["Gross or net profit?"]
    assert rows[1]["generated_sql"] is None   # clarification ran no SQL
    assert r["results"]["error_count"] == 0


def test_parse_acceptance_clarification_then_answer(tmp_path):
    """The -02 schema: clarification_then_answer carries must_ask +
    follow_up_user_response, and ground_truth is the resolved-answer SQL."""
    import acceptance
    f = tmp_path / "acc.md"
    f.write_text(
        "---\n"
        "dataAgentId: a\n"
        "testCases:\n"
        "  - id: profit\n"
        "    question: What was our profit?\n"
        "    expectationType: clarification_then_answer\n"
        "    groundTruth:\n"
        "      mustAsk: Gross or net?\n"
        "      followUpUserResponse: gross margin, B2B\n"
        "      sql: SELECT gross_margin FROM t\n"
        "---\n")
    r = acceptance.parse_acceptance_set(str(f))
    assert r["status"] == "success"
    c = r["results"]["cases"][0]
    assert c["expectation_type"] == "clarification_then_answer"
    assert c["ground_truth"] == "SELECT gross_margin FROM t"   # resolved-answer SQL
    assert c["must_ask"] == "Gross or net?"
    assert c["follow_up_user_response"] == "gross margin, B2B"


def test_run_acceptance_drives_two_turn_flow():
    """clarification_then_answer runs turn 1 (ask) then turn 2 (the follow-up
    reply), grading the resolved answer; both turns are captured."""
    import acceptance
    ca = FakeCA(answers={
        "What was our profit?": {"text": "Do you mean gross or net?",
                                 "followups": ["Gross or net?"]},
        "gross margin, B2B": {"text": "Gross margin was $2M",
                              "generated_sql": "SELECT gross_margin FROM t"},
    })
    cases = [{"id": "profit", "question": "What was our profit?",
              "expectation_type": "clarification_then_answer",
              "ground_truth": "SELECT gross_margin FROM t",
              "must_ask": "Gross or net?",
              "follow_up_user_response": "gross margin, B2B"}]
    r = acceptance.run_acceptance("p", "global", "agent-x", cases, ca=ca)
    row = r["results"]["rows"][0]
    # turn 1 captured as the clarification
    assert row["clarification_response"] == "Do you mean gross or net?"
    assert row["must_ask"] == "Gross or net?"
    # turn 2 (resolved) is the primary graded response + SQL
    assert row["agent_response"] == "Gross margin was $2M"
    assert row["generated_sql"] == "SELECT gross_margin FROM t"


def test_compare_results_exact_ignores_order_and_numeric_form():
    """Tier 1: different SQL, identical results → exact (order + 3 vs 3.0 ignored)."""
    import results
    golden = [{"island": "Biscoe", "n": 168}, {"island": "Dream", "n": 124}]
    agent = [{"n": 124.0, "island": "Dream"}, {"island": "Biscoe", "n": 168}]
    c = results.compare_results(golden, agent)
    assert c["tier"] == "exact" and c["passed"] is True


def test_compare_results_containment_superset():
    """Tier 2: agent returned a superset that still contains the golden answer."""
    import results
    golden = [{"island": "Biscoe", "n": 168}]
    agent = [{"island": "Biscoe", "n": 168}, {"island": "Dream", "n": 124},
             {"island": "Torgersen", "n": 52}]
    c = results.compare_results(golden, agent)
    assert c["tier"] == "containment" and c["passed"] is True


def test_compare_results_value_containment_diff_columns():
    """One SQL gives a direct scalar, another a wider result that includes it —
    columns differ but the golden value is present."""
    import results
    golden = [{"total_net_revenue": 1200000}]
    agent = [{"revenue": 1200000, "region": "NorthAm"},
             {"revenue": 800000, "region": "EMEA"}]
    c = results.compare_results(golden, agent)
    assert c["tier"] == "value_containment" and c["passed"] is True


def test_compare_results_currency_and_formatting():
    """Formatted currency, percentages, and commas normalize to compare correctly."""
    import results
    golden = [{"aov": 2813.38}]
    agent = [{"aov": "$2,813.38"}]
    c = results.compare_results(golden, agent)
    assert c["tier"] == "exact" and c["passed"] is True

    golden_pct = [{"defect_rate": 2.7}]
    agent_pct = [{"defect_rate": "2.7%"}]
    c2 = results.compare_results(golden_pct, agent_pct)
    assert c2["tier"] == "exact" and c2["passed"] is True


def test_compare_results_aggregation_derivability():
    """A scalar total matches the sum of detailed rows."""
    import results
    # golden is scalar total, agent is yearly breakdown
    golden = [{"total_cogs": 3000.0}]
    agent = [{"fy": 2024, "cogs": 1000.0}, {"fy": 2025, "cogs": 2000.0}]
    c = results.compare_results(golden, agent)
    assert c["tier"] == "derivable_aggregation" and c["passed"] is True

    # agent is scalar total, golden is breakdown
    c2 = results.compare_results(agent, golden)
    assert c2["tier"] == "derivable_aggregation" and c2["passed"] is True


def test_compare_results_mismatch_and_edge_cases():
    import results
    # genuinely wrong: golden value absent
    m = results.compare_results([{"n": 3}], [{"n": 5}])
    assert m["passed"] is False and m["tier"] == "mismatch"
    # agent returned nothing
    nd = results.compare_results([{"n": 3}], None)
    assert nd["passed"] is False and nd["tier"] == "no_agent_data"
    # empty golden
    eg = results.compare_results([], [{"n": 3}])
    assert eg["passed"] is False and eg["tier"] == "empty_golden"


def test_grading_sql_multi_turn_grades_both_halves():
    """clarification_then_answer requires BOTH ask_pass AND answer_pass."""
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "AS ask_pass" in sql
    assert "EXPECTED CLARIFICATION" in sql and "TURN 1 RESPONSE" in sql
    # the type is graded on both halves
    assert "COALESCE(ask_pass, FALSE) AND COALESCE(answer_pass, FALSE)" in sql
    # and it participates in SQL-equivalence / score answer grading
    assert "clarification_then_answer" in sql


def test_run_acceptance_counts_chat_errors():
    import acceptance

    class BadCA(FakeCA):
        def chat(self, *a, **k):
            return {"status": "error", "tool_name": "chat",
                    "messages": ["boom"], "results": {}}

    r = acceptance.run_acceptance(
        "p", "global", "agent-x",
        [{"question": "q", "expectation_type": "answer"}], ca=BadCA())
    assert r["results"]["error_count"] == 1
    assert r["results"]["rows"][0]["agent_response"] is None


def test_parse_acceptance_set(tmp_path):
    import acceptance
    f = tmp_path / "acc.md"
    f.write_text(
        "---\n"
        "dataAgentId: my-agent\n"
        "testCases:\n"
        "  - id: c1\n"
        "    question: What was Net Revenue?\n"
        "    category: Baseline\n"
        "    expectationType: answer\n"
        "    groundTruth:\n"
        "      sql: SELECT 1\n"
        "  - id: c2\n"
        "    question: What was profit?\n"
        "    expectationType: clarification\n"
        "    groundTruth:\n"
        "      mustAsk: gross or net?\n"
        "---\n")
    r = acceptance.parse_acceptance_set(str(f))
    assert r["status"] == "success"
    cases = r["results"]["cases"]
    assert cases[0]["ground_truth"] == "SELECT 1"
    assert cases[1]["expectation_type"] == "clarification"
    assert cases[1]["ground_truth"] == "gross or net?"
    assert r["results"]["meta"]["data_agent_id"] == "my-agent"


# --- grader: manual-tier SQL builder (no BigQuery) --------------------------

def test_build_grading_sql_uses_ai_functions():
    import grader
    sql = grader.build_grading_sql("proj.ds.rows", "proj.ds.results")
    assert "CREATE OR REPLACE TABLE `proj.ds.results`" in sql
    assert "FROM `proj.ds.rows`" in sql
    assert "AI.SCORE(" in sql               # answer grading
    assert "AI.GENERATE_BOOL(" in sql       # clarification/refusal grading
    assert "expectation_type = 'answer'" in sql
    assert "AS passed" in sql


def test_grading_sql_refusal_accepts_masking():
    """A governance case passes if the agent declines OR masks the PII — not only
    a hard refusal (Adam's pii-masking case expects masked output)."""
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "MASKED" in sql or "masked" in sql
    assert "EXPECTED BEHAVIOR" in sql       # refusal prompt uses ground_truth


def test_grading_sql_clarification_uses_expected_text():
    """Clarification grading feeds the mustAsk ground truth to the judge."""
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "EXPECTED CLARIFICATION" in sql


def test_grading_sql_grades_sql_when_present():
    """Answer rows with a generated_sql + SQL reference are graded by SQL
    equivalence (AI.GENERATE_BOOL on the SQL), not just AI.SCORE on the text."""
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "AS sql_pass" in sql
    assert "AGENT SQL" in sql and "REFERENCE SQL" in sql
    # the rubric must allow equivalent forms + wider-but-inclusive results
    assert "same" in sql.lower() and "WIDER" in sql
    # SQL path gated on having generated_sql + a SELECT-shaped reference
    assert "generated_sql IS NOT NULL" in sql
    assert "LIKE '%SELECT%'" in sql
    # passed prefers sql_pass over the numeric score
    assert "sql_pass IS NOT NULL\n           THEN sql_pass" in sql


def test_grading_sql_can_disable_sql_grading():
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o", grade_sql=False)
    # with SQL grading off the sql_cond collapses to FALSE
    assert "WHEN FALSE THEN" in sql


def test_knowledge_injected_into_prompts():
    """OKF knowledge is embedded in the judge prompts when provided."""
    import grader
    sql = grader.build_grading_sql(
        "p.d.r", "p.d.o",
        knowledge="Net Revenue = gross minus discounts and refunds.")
    assert "BUSINESS KNOWLEDGE" in sql
    assert "Net Revenue = gross minus discounts" in sql


def test_knowledge_sql_literal_escapes_quotes():
    import grader
    # a single quote in the knowledge must not break the SQL literal
    frag = grader._knowledge_clause("Tier 1's threshold is $250k")
    assert "\\'" in frag  # escaped for embedding in a single-quoted SQL literal


def test_score_prompt_has_reference_free_mode():
    """Answer grading uses reference-based scoring when ground_truth exists and
    reference-free quality scoring when it doesn't (production traffic)."""
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "no reference answer is available" in sql   # reference-free branch
    assert "how well the AGENT ANSWER matches the REFERENCE" in sql  # ref-based
    assert "ground_truth IS NOT NULL AND ground_truth != ''" in sql  # the switch


def test_grading_sql_errored_shape_always_fails():
    """When grading a classified table, an errored/empty turn is a hard fail
    regardless of its derived expectation_type."""
    import grader
    # without shape column: no errored short-circuit
    plain = grader.build_grading_sql("p.d.r", "p.d.o")
    assert "response_shape = 'errored'" not in plain
    # with shape column: errored (and hedged) -> FALSE
    classified = grader.build_grading_sql("p.d.r", "p.d.o",
                                          has_response_shape=True)
    assert "response_shape IN ('errored', 'hedged') THEN FALSE" in classified


def test_classify_sql_uses_ai_classify_and_maps_types():
    import grader
    sql = grader._classify_shape_sql("p.d.rows", "p.d.classified")
    assert "AI.CLASSIFY(" in sql
    for shape in ("answered", "clarified", "refused", "hedged", "errored"):
        assert f"'{shape}'" in sql
    assert "AS response_shape" in sql
    # shape -> expectation_type mapping
    assert "WHEN 'clarified' THEN 'clarification'" in sql
    assert "WHEN 'refused'   THEN 'refusal'" in sql


def test_classify_sql_hardening_structural_check_and_review_flag():
    """A 'clarified' with no actual question is downgraded to 'hedged' and flagged
    needs_review — portable structural corroboration, no business knowledge."""
    import grader
    sql = grader._classify_shape_sql("p.d.rows", "p.d.classified")
    # structural signal: is there a question mark?
    assert "STRPOS(COALESCE(agent_response, ''), '?')" in sql
    # downgrade clarified-without-question to hedged
    assert "model_shape = 'clarified' AND NOT has_question" in sql
    assert "THEN 'hedged'" in sql
    # surfaces disagreement instead of silently guessing
    assert "AS needs_review" in sql
    # classify runs once (in a CTE), not duplicated inline
    assert sql.count("AI.CLASSIFY(") == 1


def test_grading_sql_hedged_shape_also_fails():
    """Both errored and hedged are hard fails when a response_shape is present."""
    import grader
    classified = grader.build_grading_sql("p.d.r", "p.d.o",
                                          has_response_shape=True)
    assert "'errored'" in classified and "'hedged'" in classified
    assert "THEN FALSE" in classified


def test_build_grading_sql_with_endpoint():
    import grader
    sql = grader.build_grading_sql("p.d.r", "p.d.o",
                                   model_endpoint="gemini-2.5-flash")
    assert "endpoint => 'gemini-2.5-flash'" in sql


def test_summarize_computes_pass_rate_and_by_category():
    import grader
    graded = [
        {"category": "A", "passed": True},
        {"category": "A", "passed": False},
        {"category": "B", "passed": True},
    ]
    s = grader._summarize(graded)
    assert s["total"] == 3 and s["passed"] == 2
    assert abs(s["pass_rate"] - 2 / 3) < 1e-9
    assert s["by_category"]["A"] == {"total": 2, "passed": 1}


# --- observability: native path (fake CA) -----------------------------------

def test_collect_agent_turns_flattens_to_rows():
    import observability
    convs = [{"name": "projects/p/locations/global/conversations/c1",
              "conversation_id": "c1", "agents": []}]
    turns = {"projects/p/locations/global/conversations/c1": [
        {"prompt": "How many islands?", "response": "3",
         "timestamp": "2026-07-24T00:00:00Z", "generated_sql": "SELECT 1"},
        {"prompt": "Heaviest?", "response": "Biscoe",
         "timestamp": "2026-07-24T00:01:00Z", "generated_sql": None},
    ]}
    ca = FakeCA(conversations=convs, turns=turns)
    r = observability.collect_agent_turns("p", "global", "agent-x", ca=ca)
    assert r["status"] == "success"
    rows = r["results"]["rows"]
    assert len(rows) == 2
    assert rows[0]["question"] == "How many islands?"
    assert rows[0]["agent_response"] == "3"
    assert rows[0]["category"] == "production"
    assert r["results"]["conversation_count"] == 1


def test_stitch_exchanges_merges_clarify_then_answer():
    """A clarify turn folds into the following answer: original question kept, the
    resolution becomes the response, the clarifying question is recorded."""
    import observability
    turns = [
        {"prompt": "What was profit?", "response": None,
         "followups": ["Gross or net?"], "generated_sql": None, "data": None},
        {"prompt": "Net", "response": "Net profit was $1.2M",
         "followups": [], "generated_sql": "SELECT ...", "data": [{"x": 1}]},
    ]
    out = observability.stitch_exchanges(turns)
    assert len(out) == 1
    assert out[0]["prompt"] == "What was profit?"
    assert out[0]["response"] == "Net profit was $1.2M"
    assert out[0]["stitched"] is True
    assert out[0]["clarifications"] == ["Gross or net?"]
    assert out[0]["generated_sql"] == "SELECT ..."


def test_stitch_exchanges_passes_through_plain_answers():
    import observability
    turns = [
        {"prompt": "How many islands?", "response": "3 islands",
         "followups": [], "generated_sql": "SELECT 1", "data": [{"n": 3}]},
        {"prompt": "Heaviest?", "response": "Biscoe",
         "followups": [], "generated_sql": "SELECT 2", "data": None},
    ]
    out = observability.stitch_exchanges(turns)
    assert len(out) == 2
    assert all(t["stitched"] is False for t in out)


def test_stitch_exchanges_unresolved_clarification():
    """A trailing clarification with no resolution stays a single (unstitched)
    exchange rather than swallowing nonexistent turns."""
    import observability
    turns = [
        {"prompt": "What was profit?", "response": "Gross or net?",
         "followups": ["Gross or net?"], "generated_sql": None, "data": None},
    ]
    out = observability.stitch_exchanges(turns)
    assert len(out) == 1
    assert out[0]["prompt"] == "What was profit?"
    assert out[0]["response"] is None       # never resolved
    assert out[0]["stitched"] is False


def test_stitch_exchanges_respects_max_span():
    """A long clarify loop can't absorb more than max_span turns."""
    import observability
    turns = [
        {"prompt": "q0", "response": "clarify 1?", "followups": ["a?"],
         "generated_sql": None, "data": None},
        {"prompt": "reply1", "response": "clarify 2?", "followups": ["b?"],
         "generated_sql": None, "data": None},
        {"prompt": "reply2", "response": "clarify 3?", "followups": ["c?"],
         "generated_sql": None, "data": None},
        {"prompt": "reply3", "response": "finally the answer",
         "followups": [], "generated_sql": "SELECT 1", "data": [{"n": 1}]},
    ]
    out = observability.stitch_exchanges(turns, max_span=3)
    # first exchange caps at 3 turns and does NOT reach the answer at index 3
    assert out[0]["prompt"] == "q0"
    assert out[0]["response"] != "finally the answer"


def test_summarize_turns_operational_metrics():
    import observability
    rows = [
        {"agent_response": "ok", "generated_sql": "SELECT 1", "conversation": "c1"},
        {"agent_response": "", "generated_sql": None, "conversation": "c1"},
        {"agent_response": "ok2", "generated_sql": "SELECT 2", "conversation": "c2"},
    ]
    s = observability.summarize_turns(rows)["results"]["summary"]
    assert s["turn_count"] == 3
    assert s["conversation_count"] == 2
    assert s["empty_response_count"] == 1
    assert abs(s["error_rate"] - 1 / 3) < 1e-9
    assert abs(s["sql_execution_rate"] - 2 / 3) < 1e-9


# --- run.py aggregates everything -------------------------------------------

def test_run_reexports_all_areas():
    import run
    for fn in ("parse_acceptance_set", "run_acceptance", "collect_agent_turns",
               "summarize_turns", "stitch_exchanges", "list_traces",
               "evaluate_latency", "judge_correctness", "match_trajectory",
               "build_grading_sql", "grade_manual", "grade_managed",
               "classify_and_grade", "load_rows_to_bq", "normalize_rows",
               "grade_results", "check_answer_consistency", "compare_results"):
        assert hasattr(run, fn), f"run.py missing {fn}"
