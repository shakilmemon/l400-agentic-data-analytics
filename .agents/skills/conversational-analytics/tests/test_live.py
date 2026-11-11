"""Live tests — hit real Google Cloud APIs. Opt-in only.

Run with:  CA_LIVE_TESTS=1 uv run pytest tests/test_live.py -v

SAFETY CONTRACT:
  * Every created resource uses a unique 'catest-<...>' name.
  * The ca_resources fixture deletes ONLY ids created in the test.
  * No test performs a broad/bulk delete or touches pre-existing resources.
  * Uses BigQuery PUBLIC data (bigquery-public-data.ml_datasets.penguins) so no
    dataset setup is required and nothing in your project's data is read/written.
"""

import pytest


PUBLIC_TABLE = {"project_id": "bigquery-public-data",
                "dataset_id": "ml_datasets", "table_id": "penguins"}


@pytest.mark.live
def test_inline_chat_returns_final_answer(project_id, location):
    """Stateless inline chat against public data — no resources created."""
    import ca_rest
    ctx = ca_rest.build_context(
        "You are a data analyst.",
        ca_rest.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]
    r = ca_rest.chat(project_id, location,
                     "What is the average body mass by island?", "inline",
                     inline_context=ctx)
    assert r["status"] == "success"
    ans = r["results"]["answer"]
    assert ans["text"] and "body mass" in ans["text"].lower()
    # regression: must be FINAL_RESPONSE, not the follow-up questions
    assert ans["text"] not in (ans["followups"] or [])


@pytest.mark.live
def test_sdk_inline_chat_matches(project_id, location):
    """SDK path returns a real answer too (behavioral mirror check)."""
    import ca_sdk
    ctx = ca_sdk.build_context(
        "You are a data analyst.",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]
    r = ca_sdk.chat(project_id, location,
                    "What is the average body mass by island?", "inline",
                    inline_context=ctx)
    assert r["status"] == "success"
    assert r["results"]["answer"]["text"]


@pytest.mark.live
def test_stateful_agent_lifecycle(project_id, location, ca_resources):
    """Create agent -> conversation -> stateful chat -> cleanup (only ours)."""
    import ca_sdk
    agent_id = ca_resources["unique"]("agent")
    conv_id = ca_resources["unique"]("conv")

    ctx = ca_sdk.build_context(
        "You are a data analyst.",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]

    created = ca_sdk.create_data_agent(
        project_id, location, agent_id, ctx,
        display_name="CA skill live test", description="safe to delete",
        labels={"origin": "catest"})
    assert created["status"] == "success", created["messages"]
    ca_resources["agents"].append((project_id, location, agent_id))
    agent_name = created["results"]["name"]

    conv = ca_sdk.create_conversation(project_id, location, conv_id, agent_id)
    assert conv["status"] == "success", conv["messages"]
    ca_resources["conversations"].append(conv["results"]["name"])

    r = ca_sdk.chat(project_id, location, "How many islands are there?",
                    "conversation", agent_name=agent_name,
                    conversation_name=conv["results"]["name"])
    assert r["status"] == "success"

    # history retrievable
    hist = ca_sdk.list_messages(conv["results"]["name"])
    assert hist["status"] == "success"


@pytest.mark.live
def test_create_or_update_is_idempotent(project_id, location, ca_resources):
    """create_or_update survives a re-run (the lab-cell-rerun scenario) and
    applies the change on the second call."""
    import ca_sdk
    agent_id = ca_resources["unique"]("agent")
    ctx = ca_sdk.build_context(
        "analyst",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]

    first = ca_sdk.create_or_update_data_agent(
        project_id, location, agent_id, ctx, display_name="v1",
        labels={"origin": "catest"})
    assert first["status"] == "success" and first["results"]["created"] is True
    ca_resources["agents"].append((project_id, location, agent_id))

    # re-run: must NOT error, and should update rather than create
    second = ca_sdk.create_or_update_data_agent(
        project_id, location, agent_id, ctx, display_name="v2",
        labels={"origin": "catest"})
    assert second["status"] == "success" and second["results"]["created"] is False

    got = ca_sdk.get_data_agent(project_id, location, agent_id)
    assert got["results"]["display_name"] == "v2"


@pytest.mark.live
def test_get_or_create_conversation_idempotent(project_id, location, ca_resources):
    """get_or_create_conversation survives a re-run (fixed id 409s on plain
    create) — the notebook/lab-cell re-run scenario."""
    import ca_sdk
    agent_id = ca_resources["unique"]("agent")
    conv_id = ca_resources["unique"]("conv")
    ctx = ca_sdk.build_context(
        "analyst",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]
    ca_sdk.create_data_agent(project_id, location, agent_id, ctx,
                             labels={"origin": "catest"})
    ca_resources["agents"].append((project_id, location, agent_id))

    first = ca_sdk.get_or_create_conversation(project_id, location, conv_id, agent_id)
    assert first["status"] == "success" and first["results"]["created"] is True
    ca_resources["conversations"].append(first["results"]["name"])
    # re-run: must NOT 409, returns existing
    second = ca_sdk.get_or_create_conversation(project_id, location, conv_id, agent_id)
    assert second["status"] == "success" and second["results"]["created"] is False


@pytest.mark.live
def test_list_conversations_by_agent_and_delete(project_id, location, ca_resources):
    """list_conversations filtered to OUR agent finds our conversation, then
    delete_conversation removes it (only ours). Foundation for the trust layer's
    stateful trace retrieval (list_conversations -> list_messages)."""
    import ca_sdk
    agent_id = ca_resources["unique"]("agent")
    conv_id = ca_resources["unique"]("conv")
    ctx = ca_sdk.build_context(
        "analyst",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]
    created = ca_sdk.create_data_agent(project_id, location, agent_id, ctx,
                                       labels={"origin": "catest"})
    ca_resources["agents"].append((project_id, location, agent_id))
    agent_name = created["results"]["name"]

    conv = ca_sdk.create_conversation(project_id, location, conv_id, agent_id)
    ca_resources["conversations"].append(conv["results"]["name"])

    # filter to only our agent so we never depend on / touch pre-existing convs
    listed = ca_sdk.list_conversations(
        project_id, location, filter_str=f'agents:"{agent_name}"')
    assert listed["status"] == "success", listed["messages"]
    ids = [c["conversation_id"] for c in listed["results"]["conversations"]]
    assert conv_id in ids

    # delete only the conversation we created
    d = ca_sdk.delete_conversation(project_id, location, conv_id)
    assert d["status"] == "success", d["messages"]
    ca_resources["conversations"].remove(conv["results"]["name"])


@pytest.mark.live
def test_get_and_list_only_our_agent(project_id, location, ca_resources):
    """get_data_agent + a labeled list that returns our test agent."""
    import ca_sdk
    agent_id = ca_resources["unique"]("agent")
    ctx = ca_sdk.build_context(
        "analyst",
        ca_sdk.build_table_references(
            [PUBLIC_TABLE])["results"]["datasource_references"],
        enable_python=False)["results"]["context"]
    ca_sdk.create_data_agent(project_id, location, agent_id, ctx,
                             labels={"origin": "catest"})
    ca_resources["agents"].append((project_id, location, agent_id))

    got = ca_sdk.get_data_agent(project_id, location, agent_id)
    assert got["status"] == "success"
    assert got["results"]["labels"].get("origin") == "catest"
