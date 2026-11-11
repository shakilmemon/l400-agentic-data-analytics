"""Tests for tool-facing JSON normalization + ADK tool callables. Offline."""

import json


def test_to_tool_json_is_serializable_and_drops_rich_objects():
    import ca_common

    class _Proto:  # stand-in for a Context proto (dropped)
        def __repr__(self):
            return "<Context proto>"

    class _Scalar:  # stand-in for a numpy-like scalar (coerced via .item())
        def item(self):
            return 2

    result = {
        "status": "success", "tool_name": "build_context",
        "messages": ["built"],
        "results": {
            "context": _Proto(),                 # dropped (rich object key)
            "tables": ["p.d.a", "p.d.b"],         # kept
            "rationale": "because",               # kept
            "count": _Scalar(),                   # coerced to int via .item()
        },
    }
    tj = ca_common.to_tool_json(result)
    # fully serializable
    json.dumps(tj)
    assert "context" not in tj["results"]
    assert tj["results"]["tables"] == ["p.d.a", "p.d.b"]
    assert tj["results"]["count"] == 2


def test_to_tool_json_preserves_answer_fields():
    import ca_common
    result = {
        "status": "success", "tool_name": "chat", "messages": [],
        "results": {
            "raw": ["<huge stream>"],            # dropped
            "history": ["<messages>"],           # dropped
            "answer": {"text": "42", "data": [{"n": 1}],
                       "generated_sql": "SELECT 1",
                       "followups": ["more?"], "has_chart": False,
                       "thoughts": ["..."]},
        },
    }
    tj = ca_common.to_tool_json(result)
    json.dumps(tj)
    assert "raw" not in tj["results"]
    assert tj["results"]["answer"]["text"] == "42"
    assert tj["results"]["answer"]["generated_sql"] == "SELECT 1"


def test_facade_exposes_to_tool_json():
    import ca
    assert hasattr(ca, "to_tool_json")


def test_adk_module_imports_without_adk():
    """ca_adk must import even when google-adk is not installed."""
    import ca_adk
    assert hasattr(ca_adk, "build_cai_tools")
    assert hasattr(ca_adk, "tool_ask_cai")


def test_tool_ask_cai_returns_json(monkeypatch):
    import ca_adk
    import ca
    # stub the CAI calls so no network; assert JSON-serializable tool output
    monkeypatch.setattr(ca, "build_table_references",
                        lambda *a, **k: {"status": "success", "messages": [],
                        "results": {"datasource_references": object()}})
    monkeypatch.setattr(ca, "build_context",
                        lambda *a, **k: {"status": "success", "messages": [],
                        "results": {"context": object()}})
    monkeypatch.setattr(ca, "chat",
                        lambda *a, **k: {"status": "success", "tool_name": "chat",
                        "messages": [], "results": {"answer": {"text": "answer"}}})
    out = ca_adk.tool_ask_cai("q", ["p.d.A"], "sys", "proj")
    json.dumps(out)  # serializable
    assert out["results"]["answer"]["text"] == "answer"
