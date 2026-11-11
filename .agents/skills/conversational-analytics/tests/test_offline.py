"""Offline tests — no network. Fast default suite.

Covers: mirror parity, facade coverage, the THOUGHT-vs-answer parser fix
(regression guard for the live bug found 2026-07-16), context builders, and the
full router pipeline with injected embeddings/LLM responses.
"""

import ast
import os


_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))


def _public_sigs(fname):
    path = os.path.join(_SCRIPTS, fname)
    tree = ast.parse(open(path).read())
    out = {}
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
            out[n.name] = ([a.arg for a in n.args.args], len(n.args.defaults))
    return out


# --- structure --------------------------------------------------------------

def test_sdk_rest_mirror_parity():
    sdk, rest = _public_sigs("ca_sdk.py"), _public_sigs("ca_rest.py")
    assert list(sdk) == list(rest), "SDK/REST public function names must match"
    mismatch = {k: (sdk[k], rest[k]) for k in sdk if sdk[k] != rest[k]}
    assert not mismatch, f"signature mismatches: {mismatch}"


def test_facade_covers_all_backend_functions():
    sdk = set(_public_sigs("ca_sdk.py"))
    fac = set(_public_sigs("ca.py")) - {"set_backend", "get_backend"}
    assert sdk <= fac, f"facade missing: {sdk - fac}"


def test_rest_backend_does_not_import_sdk():
    """The REST path must not trigger an SDK import. Run in a SUBPROCESS: once
    any other in-process test imports the SDK, sys.modules stays polluted for the
    whole process, so this guarantee can only be asserted in a clean interpreter.
    """
    import subprocess
    import sys as _sys
    code = (
        "import sys; sys.path.insert(0, r'%s'); import ca; "
        "ca.set_backend('rest'); ca.build_table_references(['p.d.t']); "
        "print('google.cloud.geminidataanalytics' in sys.modules)" % _SCRIPTS)
    out = subprocess.check_output([_sys.executable, "-c", code], text=True)
    assert out.strip() == "False"


# --- parser: the live-found THOUGHT-vs-answer bug ---------------------------

def _rest_msg(text, text_type):
    return {"systemMessage": {"text": {"parts": [text], "textType": text_type}}}


def test_parse_stream_returns_final_response_not_followups():
    import ca_rest
    stream = [
        _rest_msg("Analyzing context", "THOUGHT"),
        _rest_msg("Running a query", "THOUGHT"),
        _rest_msg("The average body mass is 4200g.", "FINAL_RESPONSE"),
        _rest_msg("What about flipper length?", "FOLLOWUP_QUESTIONS"),
    ]
    p = ca_rest.parse_stream(stream)
    assert p["text"] == "The average body mass is 4200g."
    assert len(p["thoughts"]) == 2
    assert p["followups"] == ["What about flipper length?"]


def test_parse_stream_unknown_type_treated_as_answer():
    import ca_rest
    stream = [{"systemMessage": {"text": {"parts": ["hi"]}}}]  # no textType
    assert ca_rest.parse_stream(stream)["text"] == "hi"


def test_rest_progress_and_followups_excluded_from_answer():
    import ca_rest
    stream = [
        _rest_msg("working...", "PROGRESS"),
        _rest_msg("The answer is 42.", "FINAL_RESPONSE"),
        _rest_msg("Want more?", "FOLLOWUP_QUESTIONS"),
    ]
    p = ca_rest.parse_stream(stream)
    assert p["text"] == "The answer is 42."
    assert "working..." in p["thoughts"]


def test_sdk_text_type_maps_wire_value_4_to_followups():
    """v0.3.0 SDK enum knows only 0-3; API returns 4 (FOLLOWUP_QUESTIONS).
    Regression for the live 'Unrecognized TextType enum value: 4' warning."""
    import ca_sdk

    class _FakeEnum:
        def __init__(self, value):
            self.value = value
            self.name = str(value)  # SDK can't name unknown value -> digit string

    class _FakeText:
        def __init__(self, parts, tv):
            self.parts = parts
            self.text_type = _FakeEnum(tv)

    assert ca_sdk._text_type(_FakeText(["q?"], 4)) == "FOLLOWUP_QUESTIONS"
    assert ca_sdk._text_type(_FakeText(["a"], 1)) == "FINAL_RESPONSE"
    assert ca_sdk._text_type(_FakeText(["p"], 3)) == "PROGRESS"


def test_parse_stream_full_shape_and_chart_flag():
    import ca_rest
    stream = [
        _rest_msg("thinking", "THOUGHT"),
        {"systemMessage": {"chart": {"result": {}}}},
        _rest_msg("the answer", "FINAL_RESPONSE"),
        _rest_msg("next?", "FOLLOWUP_QUESTIONS"),
    ]
    p = ca_rest.parse_stream(stream)
    # every documented key is present
    for k in ("text", "thoughts", "followups", "all_text", "data",
              "generated_sql", "has_chart"):
        assert k in p
    assert p["text"] == "the answer"
    assert p["thoughts"] == ["thinking"]
    assert p["followups"] == ["next?"]
    assert p["has_chart"] is True
    assert len(p["all_text"]) == 3


def test_find_messages_by_kind_and_texttype():
    import ca_rest
    stream = [
        _rest_msg("t", "THOUGHT"),
        _rest_msg("ans", "FINAL_RESPONSE"),
        _rest_msg("q?", "FOLLOWUP_QUESTIONS"),
        {"systemMessage": {"chart": {"result": {}}}},
        {"systemMessage": {"data": {"generatedSql": "SELECT 1"}}},
    ]
    assert len(ca_rest.find_messages(stream, "chart")) == 1
    assert len(ca_rest.find_messages(stream, "data")) == 1
    answers = ca_rest.find_messages(stream, "text", text_type="FINAL_RESPONSE")
    assert len(answers) == 1
    followups = ca_rest.find_messages(stream, "text",
                                      text_type="FOLLOWUP_QUESTIONS")
    assert len(followups) == 1
    assert len(ca_rest.find_messages(stream, "text")) == 3  # all text msgs


def test_parse_stream_extracts_data_and_sql():
    import ca_rest
    stream = [
        {"systemMessage": {"data": {"generatedSql": "SELECT 1"}}},
        {"systemMessage": {"data": {"result": {
            "schema": {"fields": [{"name": "n"}]},
            "data": [{"n": 1}, {"n": 2}]}}}},
    ]
    p = ca_rest.parse_stream(stream)
    assert p["generated_sql"] == "SELECT 1"
    assert p["data"] == [{"n": 1}, {"n": 2}]


# --- context builders (REST, no network) ------------------------------------

def test_build_context_rest_shapes():
    import ca_rest
    tr = ca_rest.build_table_references([
        {"project_id": "p", "dataset_id": "d", "table_id": "T",
         "schema_context": {"description": "desc",
                            "fields": [{"name": "c", "description": "col"}]}}])
    assert tr["status"] == "success"
    eq = ca_rest.build_example_queries(
        [{"natural_language_question": "q", "sql_query": "SELECT 1"}])
    gt = ca_rest.build_glossary_terms(
        [{"display_name": "Net Revenue", "description": "d"}])
    ctx = ca_rest.build_context("sys", tr["results"]["datasource_references"],
                                example_queries=eq["results"]["example_queries"],
                                glossary_terms=gt["results"]["glossary_terms"],
                                max_billed_bytes=100)["results"]["context"]
    assert ctx["systemInstruction"] == "sys"
    assert ctx["datasourceReferences"]["bq"]["tableReferences"][0]["tableId"] == "T"
    assert ctx["exampleQueries"][0]["naturalLanguageQuestion"] == "q"
    assert ctx["glossaryTerms"][0]["displayName"] == "Net Revenue"
    assert ctx["options"]["datasource"]["bigQueryMaxBilledBytes"] == "100"


def test_get_data_agent_treats_soft_deleted_as_not_found(monkeypatch):
    """A soft-deleted (tombstoned) agent has delete_time set and must be reported
    as not-found so create-or-update doesn't try to update a dead resource."""
    import ca_sdk

    class _Agent:
        name = "projects/p/locations/global/dataAgents/x"
        display_name = "x"
        description = ""
        labels = {}
        delete_time = "2026-07-17T12:00:00Z"   # tombstoned

    class _Client:
        def get_data_agent(self, name=None):
            return _Agent()

    monkeypatch.setattr(ca_sdk, "_call", lambda fn, **kw: fn(**kw))
    monkeypatch.setattr(ca_sdk.geminidataanalytics, "DataAgentServiceClient",
                        _Client)
    r = ca_sdk.get_data_agent("p", "global", "x")
    assert r["status"] == "error" and "soft-deleted" in r["messages"][0]


def test_create_or_update_reports_stuck_soft_deleted(monkeypatch):
    """When the id is soft-deleted, create_or_update returns a clear actionable
    error (not a raw 409/400)."""
    import ca_sdk
    monkeypatch.setattr(ca_sdk, "get_data_agent",
                        lambda *a, **k: {"status": "error", "tool_name": "get",
                        "messages": ["data agent 'x' is soft-deleted (delete_time set)"],
                        "results": {}})
    r = ca_sdk.create_or_update_data_agent("p", "global", "x", object())
    assert r["status"] == "error"
    assert "purged" in r["messages"][0] and "undelete" in r["messages"][0]


def test_get_conversation_turns_rest_pairs_prompt_and_answer(monkeypatch):
    """Reconstruct turns from stored StorageMessages: group each userMessage with
    the systemMessages that follow, taking the FINAL_RESPONSE as the answer.
    Input is intentionally newest-first (as the API returns) to prove sorting."""
    import ca_rest

    def sm(inner):  # wrap an inner message dict as a StorageMessage dict
        return {"messageId": inner.get("_id", "x"), "message": inner}

    def user(text, ts):
        return sm({"userMessage": {"text": text}, "timestamp": ts})

    def systext(text, tt, ts):
        return sm({"systemMessage": {"text": {"parts": [text], "textType": tt}},
                   "timestamp": ts})

    # newest-first order, two turns interleaved as the API would return them
    stored = [
        systext("Next question?", "FOLLOWUP_QUESTIONS", "2026-07-24T00:00:06Z"),
        systext("Biscoe has the most.", "FINAL_RESPONSE", "2026-07-24T00:00:05Z"),
        user("Which island has the most?", "2026-07-24T00:00:04Z"),
        systext("There are 3 islands.", "FINAL_RESPONSE", "2026-07-24T00:00:02Z"),
        systext("thinking", "THOUGHT", "2026-07-24T00:00:01Z"),
        user("How many islands?", "2026-07-24T00:00:00Z"),
    ]
    monkeypatch.setattr(ca_rest, "list_messages", lambda *a, **k: {
        "status": "success", "tool_name": "list_messages",
        "messages": [], "results": {"messages": stored, "count": len(stored)}})

    r = ca_rest.get_conversation_turns("projects/p/locations/global/conversations/c")
    assert r["status"] == "success"
    turns = r["results"]["turns"]
    assert [t["prompt"] for t in turns] == [
        "How many islands?", "Which island has the most?"]
    assert turns[0]["response"] == "There are 3 islands."
    assert turns[0]["thoughts"] == ["thinking"]
    assert turns[1]["response"] == "Biscoe has the most."
    assert turns[1]["followups"] == ["Next question?"]


def test_get_conversation_turns_propagates_list_error(monkeypatch):
    import ca_rest
    monkeypatch.setattr(ca_rest, "list_messages", lambda *a, **k: {
        "status": "error", "tool_name": "list_messages",
        "messages": ["boom"], "results": {}})
    r = ca_rest.get_conversation_turns("x")
    assert r["status"] == "error" and r["messages"][0] == "boom"


def test_build_table_references_bad_input():
    import ca_rest
    r = ca_rest.build_table_references(["only.two"])
    assert r["status"] == "error"


def test_threshold_warning():
    import ca_rest
    r = ca_rest.build_table_references([f"p.d.t{i}" for i in range(25)])
    assert "WARNING" in r["messages"][0]
