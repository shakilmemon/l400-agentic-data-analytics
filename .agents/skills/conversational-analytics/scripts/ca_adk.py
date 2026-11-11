"""OPTIONAL Google ADK integration for the conversational-analytics skill.

ADK is entirely optional: direct CAI users ignore this file. It exists for users
who want the skill inside a larger agentic system. Importing this module does NOT
require ADK unless you call build_cai_tools() (ADK is imported lazily there).

Design decisions (see references/adk-integration.md):
  * Tools return JSON (via ca_common.to_tool_json) — the model reasons over
    table lists, rationale, answer text, not Context protos or numpy arrays.
  * ADK owns session memory; CAI runs STATELESS INLINE per turn. This keeps each
    tool call pure and sidesteps the "inline history is tied to the request's
    tables" problem — the orchestrator holds the resolved question/context.
  * For a standalone conversational data agent (A2A), prefer a STATEFUL stored
    agent (or stateless-with-defined-agent) so CAI manages history server-side;
    inline is best for embedded per-question tools.

The tool functions below are plain callables returning JSON dicts, so they work
as ADK FunctionTools, LangChain tools, or any tool-calling framework.
"""

import ca
import ca_common


# --- Plain tool callables (framework-agnostic; JSON in, JSON out) ------------

def tool_ask_cai(question, tables, system_instruction, project, location="global",
                 backend=None):
    """Answer a question with CAI over an explicit table set (stateless inline).
    Returns JSON with the answer text, data, and SQL.

    `tables` is a curated list (from the OKF CA-agent authoring flow / staging).
    For calling a pre-built stored agent from ADK, prefer the first-party
    DataAgentToolset (see references/ecosystem-integration.md)."""
    tr = ca.build_table_references(tables)
    if tr["status"] != "success":
        return ca_common.to_tool_json(tr)
    ctx = ca.build_context(system_instruction,
                           tr["results"]["datasource_references"])
    if ctx["status"] != "success":
        return ca_common.to_tool_json(ctx)
    r = ca.chat(project, location, question, "inline",
                inline_context=ctx["results"]["context"], backend=backend)
    return ca_common.to_tool_json(r)


# --- ADK FunctionTool wrapping (lazy; only needs ADK if called) --------------

def build_cai_tools():
    """Return the tool callables wrapped as ADK FunctionTools.

    Requires `google-adk`. Imported lazily so this module is safe to import
    without ADK installed.
    """
    from google.adk.tools import FunctionTool  # lazy: ADK only needed here
    return [
        FunctionTool(tool_ask_cai),
    ]
