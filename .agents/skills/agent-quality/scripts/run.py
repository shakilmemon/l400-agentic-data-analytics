"""agent-quality — the trust trio in one import.

Re-exports the three areas so callers can `import run` and reach everything:

    acceptance    : gate an agent at create/update on golden questions
    observability : harvest runtime turns (native stateful, or ADK plugin)
    grader        : score rows — MANUAL (BigQuery AI functions) or MANAGED (Vertex)

    import run
    # acceptance gate right after create:
    cases = run.parse_acceptance_set("okf/.../premium-outdoor-gear-acceptance.md")
    rows  = run.run_acceptance(P, "global", "premium-outdoor-gear-agent",
                               cases["results"]["cases"])
    graded = run.grade_manual(rows["results"]["rows"],
                              "proj.agent_quality.rows",
                              "proj.agent_quality.results")
    print(graded["results"]["summary"]["pass_rate"])

Every function returns the house-standard {status, tool_name, messages, results}.
All heavy deps (BigQuery, Vertex, the CAI skill, the ADK analytics SDK) are
imported lazily inside the functions that use them.
"""

from common import (  # noqa: F401
    load_env_config, resolve_project_dataset, normalize_rows, EXPECTATION_TYPES)

from acceptance import (  # noqa: F401
    parse_acceptance_set, run_acceptance, run_acceptance_suite, format_acceptance_report)

from observability import (  # noqa: F401
    collect_agent_turns, summarize_turns, stitch_exchanges,
    list_traces, evaluate_latency, judge_correctness, match_trajectory)

from grader import (  # noqa: F401
    build_grading_sql, grade_manual, grade_managed,
    classify_and_grade, load_rows_to_bq,
    grade_results, check_answer_consistency)

from results import compare_results  # noqa: F401
