"""Example 01 — Stateful agent (create → conversation → multi-turn chat).

Stateful mode: a stored data agent + a durable conversation; the server retains
history so you send only the new message each turn.

Run:  uv run python evals/01_stateful_agent.py
Uses BigQuery public data (penguins) — no dataset setup. Cleans up its agent.
Set CA_TEST_PROJECT to override the ADC project.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "scripts")))

import ca  # noqa: E402


def main():
    import google.auth
    project = os.environ.get("CA_TEST_PROJECT") or google.auth.default()[1]
    location = "global"
    agent_id = f"example-stateful-{uuid.uuid4().hex[:8]}"
    conv_id = f"example-conv-{uuid.uuid4().hex[:8]}"

    tr = ca.build_table_references(
        ["bigquery-public-data.ml_datasets.penguins"])
    ctx = ca.build_context(
        "You are a helpful data analyst for a penguin research dataset.",
        tr["results"]["datasource_references"], enable_python=False)

    try:
        agent = ca.create_data_agent(
            project, location, agent_id, ctx["results"]["context"],
            display_name="Example stateful agent", labels={"origin": "example"})
        print("created agent:", agent["results"]["name"])

        conv = ca.create_conversation(project, location, conv_id, agent_id)
        conv_name = conv["results"]["name"]

        for q in ["How many penguins are on each island?",
                  "Which of those islands has the heaviest penguins on average?"]:
            print(f"\nQ: {q}")
            r = ca.chat(project, location, q, "conversation",
                        agent_name=agent["results"]["name"],
                        conversation_name=conv_name)
            print("A:", (r["results"]["answer"]["text"] or "")[:300])

        hist = ca.list_messages(conv_name)
        print(f"\nconversation history: {hist['results']['count']} messages")
    finally:
        ca.delete_data_agent(project, location, agent_id)
        print("cleaned up agent", agent_id)


if __name__ == "__main__":
    main()
