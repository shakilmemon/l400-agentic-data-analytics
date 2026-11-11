"""Test fixtures + linkage to the skill's code (single source of truth).

Inserts the skill's scripts/ dir on sys.path so tests import the CURRENT modules
directly. Mirrors the conversational-analytics skill's test setup.
"""

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.abspath(os.path.join(_HERE, ".."))
_SCRIPTS = os.path.join(_SKILL, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.live tests unless AQ_LIVE_TESTS=1 is set."""
    if os.environ.get("AQ_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="live test; set AQ_LIVE_TESTS=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


class FakeCA:
    """A stand-in for the conversational-analytics `ca` facade, so acceptance /
    observability logic can be tested offline without hitting the API."""

    def __init__(self, answers=None, conversations=None, turns=None):
        # answers: {question -> {"text":..., "followups":[...]}}
        self.answers = answers or {}
        self._conversations = conversations or []
        self._turns = turns or {}  # conversation_name -> [turn dicts]

    def chat(self, project_id, location, question, mode, agent_name=None,
             history=None, **kw):
        a = self.answers.get(question, {"text": f"answer to {question}",
                                        "followups": []})
        # mirror the full answer shape ca.chat exposes so tests can assert the
        # fuller trace acceptance captures (sql/thoughts/data), not just text.
        return {"status": "success", "tool_name": "chat", "messages": [],
                "results": {"answer": {
                    "text": a.get("text"),
                    "followups": a.get("followups", []),
                    "generated_sql": a.get("generated_sql"),
                    "thoughts": a.get("thoughts", []),
                    "data": a.get("data"),
                }}}

    def list_conversations(self, project_id, location, filter_str=None, **kw):
        return {"status": "success", "tool_name": "list_conversations",
                "messages": [], "results": {"conversations": self._conversations,
                                            "count": len(self._conversations)}}

    def get_conversation_turns(self, conversation_name, **kw):
        turns = self._turns.get(conversation_name, [])
        return {"status": "success", "tool_name": "get_conversation_turns",
                "messages": [], "results": {"turns": turns, "count": len(turns)}}
