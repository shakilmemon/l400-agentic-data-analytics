"""Example 02 — Stateless inline (no stored agent).

Inline mode: pass the full context with each request; nothing is persisted. This
is the target for dynamic per-question routing and for ADK-embedded tools.
Also shows switching backend='rest' (no SDK dependency) for the same call.

Run:  uv run python evals/02_stateless_inline.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "scripts")))

import ca  # noqa: E402


def ask(project, backend):
    tr = ca.build_table_references(
        ["bigquery-public-data.ml_datasets.penguins"], backend=backend)
    ctx = ca.build_context(
        "You are a penguin data analyst.",
        tr["results"]["datasource_references"], enable_python=False,
        backend=backend)
    r = ca.chat(project, "global",
                "What is the average flipper length by species?", "inline",
                inline_context=ctx["results"]["context"], backend=backend)
    print(f"[{backend}] status={r['status']}")
    print("  answer:", (r["results"]["answer"]["text"] or "")[:250])
    print("  sql?", bool(r["results"]["answer"]["generated_sql"]),
          "| followups:", len(r["results"]["answer"]["followups"] or []))


def main():
    import google.auth
    project = os.environ.get("CA_TEST_PROJECT") or google.auth.default()[1]
    # SDK path (default)
    ask(project, "sdk")
    # REST path (no SDK import) — same call, different backend
    ask(project, "rest")


if __name__ == "__main__":
    main()
