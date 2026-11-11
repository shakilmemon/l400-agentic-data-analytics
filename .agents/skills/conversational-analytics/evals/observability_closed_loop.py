"""Closed-loop observability — build a CA agent that analyzes agent_events.

Dogfoods the skill: the observability analysis agent IS a CA agent built by this
skill, pointed at the BigQuery Agent Analytics events table + views. This helper
assembles the Context OFFLINE (no API calls) to prove the wiring; see
observability_closed_loop.md for the full ADK-plugin + evaluation-SDK pattern.

Run:  uv run python evals/observability_closed_loop.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "scripts")))

import ca  # noqa: E402


def build_observability_context(project, dataset="agent_obs"):
    """Assemble a CA Context over the ADK agent-events table + per-event views.

    Uses only the skill's generic builders — no observability-specific skill code.
    Returns the built Context (ready for create_or_update_data_agent).
    """
    tables = [
        f"{project}.{dataset}.agent_events",
        f"{project}.{dataset}.v_llm_response",
        f"{project}.{dataset}.v_tool_completed",
        f"{project}.{dataset}.v_tool_error",
    ]
    tr = ca.build_table_references(tables)

    glossary = ca.build_glossary_terms([
        {"display_name": "Turn",
         "description": "A single agent invocation, identified by invocation_id."},
        {"display_name": "Session",
         "description": "A conversation thread, identified by session_id."},
        {"display_name": "Failure",
         "description": "Any event with status = 'ERROR'."},
        {"display_name": "Tool Provenance",
         "description": "Origin of a tool call: local function, MCP, sub-agent, "
                        "A2A remote, or transfer."},
    ])

    golden = ca.build_example_queries([
        {"natural_language_question": "What is the p95 LLM latency by model this week?",
         "sql_query": (
             "SELECT model, APPROX_QUANTILES(total_ms, 100)[OFFSET(95)] AS p95_ms "
             f"FROM `{project}.{dataset}.v_llm_response` "
             "WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) "
             "GROUP BY model ORDER BY p95_ms DESC")},
        {"natural_language_question": "Which tools error most often?",
         "sql_query": (
             "SELECT tool_name, COUNT(*) AS errors "
             f"FROM `{project}.{dataset}.v_tool_error` "
             "GROUP BY tool_name ORDER BY errors DESC")},
    ])

    ctx = ca.build_context(
        "You analyze AI-agent operational logs for reliability, latency, cost, and "
        "errors. Prefer the verified queries for common operational metrics.",
        tr["results"]["datasource_references"],
        glossary_terms=glossary["results"]["glossary_terms"],
        example_queries=golden["results"]["example_queries"])
    return ctx, len(tables), glossary["results"]["count"], golden["results"]["count"]


def main():
    import google.auth
    project = os.environ.get("CA_PROJECT") or google.auth.default()[1]
    ctx, n_tables, n_terms, n_queries = build_observability_context(project)
    print("Built observability CA Context (dogfooding the skill):")
    print(f"  status         : {ctx['status']}")
    print(f"  events tables  : {n_tables}")
    print(f"  glossary terms : {n_terms}")
    print(f"  golden queries : {n_queries}")
    print("\nTo deploy the analysis agent:")
    print("  ca.create_or_update_data_agent(project, 'global', 'agent-obs-analyst',")
    print("      ctx['results']['context'], display_name='Agent Observability Analyst')")
    print("\nThen instrument your ADK agent with BigQueryAgentAnalyticsPlugin and ask")
    print("this agent NL questions over agent_events. See observability_closed_loop.md.")
    return ctx


if __name__ == "__main__":
    main()
