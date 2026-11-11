"""Shared helpers for the agent-quality trust skill.

House-standard return dict + small utilities used by acceptance, observability,
and the two grader tiers. Kept dependency-free (no BigQuery / Vertex / CAI import
at module load) so importing this module is cheap; heavy deps are imported lazily
inside the functions that need them.

The trust trio's currency is a ROW:
    {"question", "agent_response", "ground_truth", "expectation_type"}
Acceptance and observability produce rows; the graders consume them.
"""

import json
import os

# The ways a case can be judged. Ground truth means different things per type:
#   answer                   -> a reference value / golden SQL
#   clarification            -> the agent must ASK (mustAsk); no answer expected
#   refusal                  -> the agent must DECLINE or mask (mustRefuse)
#   clarification_then_answer-> multi-turn: agent asks (mustAsk), a simulated user
#                               reply (followUpUserResponse) is sent, then the
#                               agent must ANSWER correctly (golden SQL). Both the
#                               ask and the resolved answer are graded.
EXPECTATION_TYPES = ("answer", "clarification", "refusal",
                     "clarification_then_answer")


def _ok(tool_name, results, messages=None):
    return {"status": "success", "tool_name": tool_name,
            "messages": messages or [], "results": results}


def _fail(tool_name, message):
    return {"status": "failed", "tool_name": tool_name,
            "messages": [message], "results": None}


def load_env_config(env_file_path="agent-config.json"):
    """Load repo config (agent-config.json), matching sibling skills. Best-effort:
    checks the given path then cwd; returns {} if not found (the skill is
    portable and may run outside this repo)."""
    for path in (env_file_path, os.path.join(os.getcwd(), "agent-config.json")):
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def resolve_project_dataset(project_id=None, dataset_id=None,
                            dataset_key="agent-quality-dataset",
                            default_dataset="agent_quality"):
    """Fill project/dataset from agent-config.json when omitted. `dataset_key` lets
    callers pull a purpose-specific dataset (results vs events) from env."""
    if project_id and dataset_id:
        return project_id, dataset_id
    env = load_env_config()
    project_id = project_id or env.get("gcp-project-id")
    dataset_id = dataset_id or env.get(dataset_key) or default_dataset
    return project_id, dataset_id


def normalize_rows(rows):
    """Coerce a list of graded/gradable rows to the canonical row shape, filling
    missing keys with None so downstream graders/SQL never KeyError. Unknown keys
    are preserved (e.g. an id or category for reporting)."""
    out = []
    for r in rows:
        row = dict(r)
        row.setdefault("question", None)
        row.setdefault("agent_response", None)
        row.setdefault("ground_truth", None)
        et = row.get("expectation_type") or "answer"
        if et not in EXPECTATION_TYPES:
            et = "answer"
        row["expectation_type"] = et
        out.append(row)
    return out
