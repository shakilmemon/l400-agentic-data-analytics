"""Tests for the OKF agent-def -> deploy bridge (deploy_ca_from_okf.py).

Offline: parses a YAML agent def and asserts the Context is built with the right
fields + the project/dataset override precedence. No network.
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_BRIDGE = os.path.join(_HERE, "deploy_ca_from_okf.py")
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))

_SAMPLE = """---
type: Conversational Analytics Agent
dataAgentId: sample-agent
displayName: Sample Agent
description: A sample.
datasource:
  type: bigquery
  project_id: yaml-proj
  dataset_id: yaml_ds
  tables:
    - SLS_ORD_HDR
    - dim_business_events
systemInstruction: |
  You are a sample analyst.
exampleQueries:
  - naturalLanguageQuestion: "How many orders?"
    sqlQuery: |
      SELECT COUNT(*) FROM `yaml_ds.SLS_ORD_HDR`
---
"""


def _load():
    import sys
    sys.path.insert(0, _SCRIPTS)
    spec = importlib.util.spec_from_file_location("deploy_ca_from_okf", _BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_agent_def(tmp_path):
    b = _load()
    f = tmp_path / "agent.md"
    f.write_text(_SAMPLE)
    spec = b.parse_agent_def(str(f))
    assert spec["dataAgentId"] == "sample-agent"
    assert spec["datasource"]["tables"] == ["SLS_ORD_HDR", "dim_business_events"]
    assert len(spec["exampleQueries"]) == 1


def test_explicit_project_overrides_yaml(tmp_path):
    b = _load()
    f = tmp_path / "agent.md"
    f.write_text(_SAMPLE)
    ctx, meta = b.build_context_from_agent_def(str(f), project_id="my-proj",
                                               dataset_id="my_ds")
    assert meta["project"] == "my-proj" and meta["dataset"] == "my_ds"
    assert meta["table_count"] == 2
    assert meta["example_query_count"] == 1
    assert ctx["status"] == "success"


def test_falls_back_to_yaml_when_no_arg_no_env(tmp_path, monkeypatch):
    b = _load()
    # force agy-env lookup to return empty so YAML values are used
    monkeypatch.setattr(b, "_load_agy_env", lambda: {})
    f = tmp_path / "agent.md"
    f.write_text(_SAMPLE)
    _, meta = b.build_context_from_agent_def(str(f))
    assert meta["project"] == "yaml-proj" and meta["dataset"] == "yaml_ds"


def test_real_repo_agent_def_if_present():
    """If Adam's real agent def exists, it parses and builds a Context."""
    real = os.path.join(_REPO, "okf", "conversational-analytics",
                        "premium_outdoor_gear_agent.md")
    if not os.path.exists(real):
        import pytest
        pytest.skip("real agent def not present")
    b = _load()
    ctx, meta = b.build_context_from_agent_def(real, project_id="p", dataset_id="d")
    assert ctx["status"] == "success"
    assert meta["table_count"] >= 10
    assert meta["example_query_count"] >= 1
