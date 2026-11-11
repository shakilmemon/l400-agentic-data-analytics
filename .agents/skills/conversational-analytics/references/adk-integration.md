# ADK Integration (optional)

ADK is **optional**. Direct CAI users ignore `ca_adk.py` entirely. This is for
placing CAI inside a larger agentic system (Google ADK), where the skill's
functions become tools an orchestrating agent calls.

## Tool-facing JSON (why it exists)

The skill's normal return `results` carry rich, non-serializable objects — Context
protos, numpy corpus arrays, raw Message streams — perfect for in-process code
composition, useless as a tool return an LLM reasons over. `ca.to_tool_json(result)`
produces a JSON-serializable view: keeps status, messages, table lists, rationale,
and answer text/data/SQL; drops the rich objects. Every `ca_adk` tool returns this.

## Memory: ADK owns it; CAI runs stateless inline

The clean split:

- **ADK holds session state** (history, the resolved/rewritten question).
- **CAI runs STATELESS INLINE per turn** — each tool call is pure: route → build
  context → ask → return.

This sidesteps a real problem with inline mode: an inline conversation's history is
tied to the *tables of that request*. A follow-up that shifts or expands the topic
needs different tables, so replaying raw inline history is fragile. Letting the
orchestrator own memory (and re-route per turn, rewriting the question with context)
keeps each CAI call self-contained and correct.

## A2A / standalone data agent: prefer stateful (or defined-agent)

If CAI is exposed as a standalone conversational data agent over **A2A**, prefer a
**stateful stored agent** (or stateless-with-defined-agent). There, CAI manages
conversation history server-side, which is easier than reconstructing it — and a
stored agent has a stable identity to address. Rule of thumb:

| Shape | Mode | Who owns history |
|---|---|---|
| Embedded per-question tool inside ADK | stateless **inline** | ADK orchestrator |
| Standalone data agent over A2A | **stateful** (or stateless + defined agent) | CAI server |

## Usage

```python
import ca_adk
# framework-agnostic callable (JSON in, JSON out): answer over a curated table set
ca_adk.tool_ask_cai(question, tables, system_instruction, project)

# as ADK FunctionTools (requires google-adk; imported lazily):
tools = ca_adk.build_cai_tools()
# agent = LlmAgent(model="gemini-2.5-flash", tools=tools, instruction="...")
```

`build_cai_tools()` is the only thing needing `google-adk`; everything else in
`ca_adk.py` runs without it.
