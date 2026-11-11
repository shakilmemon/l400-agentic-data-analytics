"""Deploy a CA agent from an OKF agent-definition YAML (repo-side bridge).

Consumes the structured agent def produced by the OKF authoring flow
(ca-generate-* prompts -> ca-okf-staging-to-okf prompt ->
okf/conversational-analytics/<agent>.md). Parses its YAML and deploys via the CAI
skill's GENERIC builders. Dependency direction: bridge -> skill. The skill core
stays OKF-unaware; this lives in evals/ as applied glue.

Design (per team decisions):
  * Agent-def file is an EXPLICIT path argument (no hardcoded filename / discovery).
  * project_id / dataset_id resolve: explicit arg -> agent-config.json -> the YAML's own
    values (last-resort default). So one agent def deploys to any project without
    editing the YAML.
  * No glossary_terms — glossary is linked to tables in Knowledge Catalog, not on
    the agent.

The agent-def YAML (Data Agents REST-shaped) is expected to contain:
    dataAgentId, displayName, description,
    datasource: { project_id, dataset_id, tables: [BARE_TABLE, ...] },
    systemInstruction: <text>,
    exampleQueries: [ { naturalLanguageQuestion, sqlQuery }, ... ]

Run:
    uv run python evals/deploy_ca_from_okf.py <path-to-agent.md>            # dry run
    uv run python evals/deploy_ca_from_okf.py <path-to-agent.md> --deploy   # create it
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "scripts")))

import ca  # noqa: E402

# evals/ -> conversational-analytics -> skills -> .agents -> repo root (4 up)
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", "..", ".."))


def _load_agy_env():
    """Best-effort read of the repo's agent-config.json (returns {} if absent)."""
    path = os.path.join(_REPO, "agent-config.json")
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def parse_agent_def(agent_file):
    """Parse the OKF agent-def YAML frontmatter into a dict."""
    import yaml  # dev/eval dependency (see pyproject); not needed by the skill core
    text = open(agent_file, encoding="utf-8").read()
    body = text.strip()
    if body.startswith("---"):
        body = body.split("---", 2)[1] if body.count("---") >= 2 else body[3:]
    return yaml.safe_load(body)


def build_context_from_agent_def(agent_file, project_id=None, dataset_id=None):
    """Read the agent def and assemble a CAI Context via the skill's builders.

    Returns (context_result, meta) where meta has the resolved fields for deploy.
    project/dataset precedence: arg -> agent-config.json -> YAML defaults.
    """
    spec = parse_agent_def(agent_file)
    ds = spec.get("datasource", {}) or {}
    env = _load_agy_env()

    project = project_id or env.get("gcp-project-id") or ds.get("project_id")
    dataset = dataset_id or env.get("bigquery-dataset") or ds.get("dataset_id")
    if not (project and dataset):
        raise ValueError("Could not resolve project_id/dataset_id (arg, "
                         "agent-config.json, or YAML datasource).")

    # tables in the YAML are BARE names; qualify with the resolved project.dataset.
    # Assumes the agent's tables live in the target project's `dataset` (true for
    # the l400-agentic-data-analytics flow — deploy l400-agentic-data-analytics to any project). If a def ever needs
    # tables from a different project/dataset, list them fully-qualified instead.
    tables = [t if t.count(".") >= 2 else f"{project}.{dataset}.{t}"
              for t in ds.get("tables", [])]
    tr = ca.build_table_references(tables)

    eq_pairs = [{"natural_language_question": q.get("naturalLanguageQuestion", ""),
                 "sql_query": q.get("sqlQuery", "")}
                for q in spec.get("exampleQueries", []) or []]
    eq = ca.build_example_queries(eq_pairs)

    ctx = ca.build_context(
        spec.get("systemInstruction", ""),
        tr["results"]["datasource_references"],
        example_queries=eq["results"]["example_queries"])

    meta = {
        "data_agent_id": spec.get("dataAgentId"),
        "display_name": spec.get("displayName"),
        "description": spec.get("description"),
        "project": project, "dataset": dataset,
        "table_count": len(tables),
        "example_query_count": len(eq_pairs),
        "system_prompt_chars": len(spec.get("systemInstruction", "")),
    }
    return ctx, meta


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        print("ERROR: provide the agent-def file path.")
        return
    agent_file = args[0]
    deploy = "--deploy" in sys.argv

    ctx, meta = build_context_from_agent_def(agent_file)
    print(f"Built Context from {os.path.basename(agent_file)}:")
    for k in ("data_agent_id", "display_name", "project", "dataset",
              "table_count", "example_query_count", "system_prompt_chars"):
        print(f"  {k:22}: {meta[k]}")

    if not meta["data_agent_id"]:
        print("\nERROR: agent def missing dataAgentId; cannot deploy.")
        return

    if deploy:
        res = ca.create_or_update_data_agent(
            meta["project"], "global", meta["data_agent_id"],
            ctx["results"]["context"],
            display_name=meta["display_name"], description=meta["description"],
            labels={"origin": "okf"})
        print("\ndeploy:", res["status"], "|", res["messages"][0])
        if res.get("status") == "success":
            resource_uri = f"https://geminidataanalytics.googleapis.com/v1beta/projects/{meta['project']}/locations/global/dataAgents/{meta['data_agent_id']}"
            try:
                with open(agent_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if "resource:" not in content:
                    lines = content.splitlines(keepends=True)
                    new_lines = []
                    inserted = False
                    for line in lines:
                        new_lines.append(line)
                        if not inserted and line.strip().startswith("dataAgentId:"):
                            new_lines.append(f"resource: {resource_uri}\n")
                            new_lines.append(f"rest_api: {resource_uri}\n")
                            inserted = True
                    with open(agent_file, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
            except Exception as e:
                print(f"Warning: could not update OKF resource frontmatter: {e}")
    else:
        print("\n(dry run — pass --deploy to create/update the agent on GCP)")


if __name__ == "__main__":
    main()
