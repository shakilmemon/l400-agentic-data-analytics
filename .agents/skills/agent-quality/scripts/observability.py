"""Observability — runtime behavior of a deployed agent (the deferred capability).

Two retrieval paths, because not every CA agent runs inside ADK:

  NATIVE (stateful CA agents, no ADK) — enumerate an agent's conversations and
      reconstruct each into turns via the conversational-analytics skill
      (list_conversations -> get_conversation_turns). This is the primary path for
      a plain deployed CA data agent: the API stores the history, so real Q&A is
      retrievable with no extra capture infra. Turns come back as gradable rows.

  PLUGIN (embedded ADK agents) — read the BigQuery `agent_events` table populated
      by the ADK BigQuery Agent Analytics plugin, and evaluate latency / errors /
      LLM-judge correctness / golden-trajectory. Absorbed from the former
      agent-observability skill (bigquery-agent-analytics SDK, imported lazily).

Observability produces the same {question, agent_response, ...} rows acceptance
does, so the SAME grader (grader.py) scores production traffic and golden sets.
"""

import os
import sys

from common import _ok, _fail


def _load_ca():
    """Import the conversational-analytics `ca` facade (native path)."""
    candidates = [
        os.environ.get("CA_SKILL_SCRIPTS"),
        os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", "conversational-analytics",
                                     "scripts")),
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            if path not in sys.path:
                sys.path.insert(0, path)
            import ca  # noqa: E402
            return ca
    raise ImportError("Could not find conversational-analytics scripts/; set "
                      "CA_SKILL_SCRIPTS.")


# ---------------------------------------------------------------------------
# NATIVE path — stateful CA agents (no ADK, no plugin, no extra tables)
# ---------------------------------------------------------------------------

def _looks_like_clarification(turn):
    """Structural (no-LLM) test: did this turn ask instead of answer? True when it
    produced no final answer text but offered followups, or its text is itself a
    question. Pure conversation shape — no business knowledge, so it's portable."""
    text = (turn.get("response") or "").strip()
    if turn.get("followups") and not text:
        return True
    if not text:
        return False
    # a short response that is only a question (ends with '?', no data/SQL)
    return (text.endswith("?") and not turn.get("data")
            and not turn.get("generated_sql"))


def stitch_exchanges(turns, max_span=3):
    """Collapse clarify-then-answer chains in ONE conversation's turns into logical
    exchanges, for grading. Structural rule only (see _looks_like_clarification):
    when a turn is a clarification, fold the following turn(s) into it — keep the
    ORIGINAL question, take the first real answer as the response, and record the
    intermediate clarification(s). `max_span` caps how many turns one exchange may
    absorb (clarify + user reply + answer = 3), so a long clarify loop can't eat
    the whole conversation. Turns must be in ask order.

    Returns new turn dicts with added: `stitched` (bool), `clarifications` (list of
    the intermediate clarifying questions). Non-clarify turns pass through as-is.
    """
    out, i, n = [], 0, len(turns)
    while i < n:
        t = turns[i]
        if not _looks_like_clarification(t):
            out.append({**t, "stitched": False, "clarifications": []})
            i += 1
            continue
        # start an exchange at the original question; absorb up to max_span turns
        clarifs = [t.get("response") or " | ".join(t.get("followups") or [])]
        j = i + 1
        resolved = None
        while j < n and (j - i) < max_span:
            nxt = turns[j]
            if _looks_like_clarification(nxt):
                clarifs.append(nxt.get("response")
                               or " | ".join(nxt.get("followups") or []))
                j += 1
                continue
            resolved = nxt
            break
        merged = {
            "prompt": t.get("prompt"),
            "response": (resolved or {}).get("response"),
            "timestamp": t.get("timestamp"),
            "thoughts": (resolved or {}).get("thoughts", []),
            "followups": (resolved or {}).get("followups", []),
            "data": (resolved or {}).get("data"),
            "generated_sql": (resolved or {}).get("generated_sql"),
            "stitched": resolved is not None,
            "clarifications": clarifs,
        }
        out.append(merged)
        # advance past the resolution (or past what we scanned if unresolved)
        i = (j + 1) if resolved is not None else j
    return out


def collect_agent_turns(project_id, location, agent_id, ca=None,
                        max_conversations=None, stitch=False):
    """Harvest real production turns from a deployed STATEFUL agent.

    Lists the agent's conversations (server-side filtered to THIS agent) and
    reconstructs each into {prompt, response, timestamp, ...} turns, flattened
    into gradable rows (question=prompt, agent_response=response). No ground_truth
    (production traffic) — the grader judges these reference-free, or you join to
    an acceptance set by question. `ca` may be injected for tests.

    `stitch=True` collapses clarify-then-answer chains WITHIN each conversation
    into logical exchanges (see stitch_exchanges), so grading judges the resolved
    {original question -> final answer} pair instead of a bare clarifying turn.
    Stitching is applied per-conversation, so it never spans conversations.
    """
    tool = "collect_agent_turns"
    try:
        ca = ca or _load_ca()
        agent_name = (f"projects/{project_id}/locations/{location}"
                      f"/dataAgents/{agent_id}")
        listed = ca.list_conversations(project_id, location,
                                       filter_str=f'agents:"{agent_name}"')
        if listed["status"] != "success":
            return _fail(tool, listed["messages"][0])
        convs = listed["results"]["conversations"]
        if max_conversations:
            convs = convs[:max_conversations]

        rows, conv_count = [], 0
        for c in convs:
            turns = ca.get_conversation_turns(c["name"])
            if turns["status"] != "success":
                continue
            conv_count += 1
            conv_turns = turns["results"]["turns"]
            if stitch:
                conv_turns = stitch_exchanges(conv_turns)
            for t in conv_turns:
                rows.append({
                    "id": None,
                    "question": t.get("prompt"),
                    "category": "production",
                    "expectation_type": "answer",
                    "ground_truth": None,
                    "agent_response": t.get("response"),
                    "timestamp": t.get("timestamp"),
                    "conversation": c["name"],
                    "generated_sql": t.get("generated_sql"),
                    "stitched": t.get("stitched", False),
                    "clarifications": t.get("clarifications", []),
                })
        return _ok(tool, {"rows": rows, "conversation_count": conv_count,
                          "turn_count": len(rows)},
                   [f"Collected {len(rows)} turn(s) from {conv_count} "
                    f"conversation(s) for '{agent_id}'."])
    except Exception as e:
        return _fail(tool, f"collect_agent_turns failed: {e}")


def summarize_turns(rows):
    """Lightweight, no-LLM operational summary of collected turns: volume, error
    rate (responses that came back empty), and SQL-execution rate. The cheap
    'what is it doing?' view before you spend judge tokens."""
    tool = "summarize_turns"
    try:
        total = len(rows)
        empty = sum(1 for r in rows if not (r.get("agent_response") or "").strip())
        with_sql = sum(1 for r in rows if r.get("generated_sql"))
        convs = len({r.get("conversation") for r in rows if r.get("conversation")})
        summary = {
            "turn_count": total,
            "conversation_count": convs,
            "empty_response_count": empty,
            "error_rate": (empty / total) if total else 0.0,
            "sql_execution_rate": (with_sql / total) if total else 0.0,
        }
        return _ok(tool, {"summary": summary},
                   [f"{total} turn(s), {empty} empty, "
                    f"{with_sql} ran SQL."])
    except Exception as e:
        return _fail(tool, f"summarize_turns failed: {e}")


# ---------------------------------------------------------------------------
# PLUGIN path — embedded ADK agents via bigquery-agent-analytics
# (absorbed from the former agent-observability skill; SDK imported lazily)
#
# Capture step (in the ADK agent, one line):
#   from google.adk.plugins.bigquery_agent_analytics import BigQueryAgentAnalyticsPlugin
#   App(..., plugins=[BigQueryAgentAnalyticsPlugin(project_id=P, dataset_id=D)])
# ---------------------------------------------------------------------------

def _events_client(project_id, dataset_id, events_table="agent_events"):
    from bigquery_agent_analytics import Client  # lazy
    return Client(project_id=project_id, dataset_id=dataset_id,
                  table_id=events_table)


def list_traces(project_id, dataset_id, events_table="agent_events",
                agent_id=None, days=7, has_error=None, min_latency_ms=None):
    """List/filter agent traces from an ADK agent_events table (recent window)."""
    tool = "list_traces"
    try:
        from datetime import datetime, timedelta
        from bigquery_agent_analytics import TraceFilter
        client = _events_client(project_id, dataset_id, events_table)
        kwargs = {"start_time": datetime.now() - timedelta(days=days),
                  "end_time": datetime.now()}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if has_error is not None:
            kwargs["has_error"] = has_error
        if min_latency_ms is not None:
            kwargs["min_latency_ms"] = min_latency_ms
        traces = list(client.list_traces(filter_criteria=TraceFilter(**kwargs)))
        return _ok(tool, {"count": len(traces), "traces": traces},
                   [f"Found {len(traces)} trace(s) over {days} day(s)."])
    except Exception as e:
        return _fail(tool, f"list_traces failed: {e}")


def evaluate_latency(project_id, dataset_id, events_table="agent_events",
                     agent_id=None, threshold_ms=5000):
    """Batch latency-SLO scoring over ADK traces. Returns a report summary."""
    tool = "evaluate_latency"
    try:
        from bigquery_agent_analytics import SystemEvaluator, TraceFilter
        client = _events_client(project_id, dataset_id, events_table)
        filters = TraceFilter(agent_id=agent_id) if agent_id else None
        report = client.evaluate(
            evaluator=SystemEvaluator.latency(threshold_ms=threshold_ms),
            filters=filters)
        return _ok(tool, {"summary": report.summary(), "report": report},
                   [f"Evaluated latency (threshold {threshold_ms} ms)."])
    except Exception as e:
        return _fail(tool, f"evaluate_latency failed: {e}")


def judge_correctness(project_id, dataset_id, events_table="agent_events",
                      agent_id=None, threshold=0.7):
    """LLM-as-judge correctness over ADK traces (batch). Returns report summary."""
    tool = "judge_correctness"
    try:
        from bigquery_agent_analytics import LLMAsJudge, TraceFilter
        client = _events_client(project_id, dataset_id, events_table)
        filters = TraceFilter(agent_id=agent_id) if agent_id else None
        report = client.evaluate(
            evaluator=LLMAsJudge.correctness(threshold=threshold),
            filters=filters)
        return _ok(tool, {"summary": report.summary(), "report": report},
                   [f"LLM-judge correctness (threshold {threshold})."])
    except Exception as e:
        return _fail(tool, f"judge_correctness failed: {e}")


def match_trajectory(project_id, dataset_id, session_id, golden_trajectory,
                     golden_response=None, match_type="IN_ORDER",
                     events_table="agent_events"):
    """Golden-trajectory match for one ADK session (EXACT/IN_ORDER/ANY_ORDER)."""
    tool = "match_trajectory"
    try:
        import asyncio
        from bigquery_agent_analytics import BigQueryTraceEvaluator
        from bigquery_agent_analytics.trace_evaluator import MatchType
        client = _events_client(project_id, dataset_id, events_table)
        evaluator = BigQueryTraceEvaluator(client)
        mt = getattr(MatchType, match_type.upper())
        result = asyncio.run(evaluator.evaluate_session(
            session_id=session_id, golden_trajectory=golden_trajectory,
            golden_response=golden_response, match_type=mt))
        return _ok(tool, {"session_id": session_id, "result": result},
                   [f"Trajectory match ({match_type}) for '{session_id}'."])
    except Exception as e:
        return _fail(tool, f"match_trajectory failed: {e}")
