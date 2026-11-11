# Evals & worked examples

Runnable examples for the `conversational-analytics` skill. Generic skill
verification lives in `../tests/`; this folder is the *applied* layer — how the
skill is used against real project data.

| File | What | Portable? |
|---|---|---|
| `01_stateful_agent.py` | stored agent + conversation + multi-turn chat | ✅ public data |
| `02_stateless_inline.py` | stateless inline chat (SDK + REST backends) | ✅ public data |
| `observability_closed_loop.py` + `.md` | dogfoods the skill: a CA agent that analyzes ADK `agent_events` (instrument → analyze in NL → evaluate) | l400-agentic-data-analytics-adjacent |
| `deploy_ca_from_okf.py` | deploy a CA agent from an OKF agent-def YAML (`okf/conversational-analytics/<agent>.md`) → generic builders → `create_or_update_data_agent` | repo-specific |
| `deploy-checklist.md` | standing up `l400-agentic-data-analytics` in a dedicated project | repo-specific |

## For an agent reading this skill

Worked, runnable examples of the skill's capabilities:

- **Interaction modes** → `01` (stateful), `02` (stateless inline, SDK+REST)
- **Deploying from a curated context** → both demos build a Context via
  `build_table_references` / `build_example_queries` / `build_context` and deploy.
  In this repo the curated inputs (table list, system prompt, golden queries) are
  authored upstream by the `ca-generate-*` prompt flow into
  `okf-staging/conversational-analytics/*` (see the skills README).
- **Closed-loop observability** → `observability_closed_loop.*`

## Running

```bash
# from the skill root (.agents/skills/conversational-analytics/)
uv sync
uv run python evals/02_stateless_inline.py         # portable demo
uv run pytest tests/ -q                             # offline tests
CA_LIVE_TESTS=1 uv run pytest tests/test_live.py    # live (creates + cleans its own resources)
```

Requires ADC (`gcloud auth application-default login`). Portable demos use
`bigquery-public-data` — no lab deployment needed.

## What the tests lock down

- SDK/REST **mirror parity**; **facade** covers every backend fn; REST path never imports the SDK
- **Parser correctness** (`FINAL_RESPONSE` vs `THOUGHT`/`PROGRESS`/`FOLLOWUP_QUESTIONS`; SDK ≥0.11.0 pin)
- **Robustness**: retry/backoff, pagination, idempotent create-or-update, soft-delete handling
- **ADK tool-JSON** normalization
