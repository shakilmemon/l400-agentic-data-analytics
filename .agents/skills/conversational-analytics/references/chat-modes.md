# CAI Chat Modes

The `chat()` function dispatches over three interaction modes. All three POST to
the same `:chat` endpoint (v1); what differs is the context field in the request.

## 1. `'conversation'` — Stateful

Server retains conversation history. You create a `Conversation` once (ca-conversation),
then send only the new message each turn.

- **Requires:** `conversation_name` + `agent_name`
- **SDK:** `ChatRequest(parent, messages=[msg], conversation_reference=ConversationReference(conversation=..., data_agent_context.data_agent=...))`
- **REST:** body `{parent, messages:[{userMessage:{text}}], conversationReference:{conversation, dataAgentContext:{dataAgent}}}`
- **History:** managed by the server — send one message per turn.

## 2. `'agent'` — Stateless with a stored agent

The agent is persisted (ca-agent-manage), but there is no server-side conversation.
You resend the full message history each call.

- **Requires:** `agent_name`; you pass `history`
- **SDK:** `ChatRequest(parent, messages=history+[msg], data_agent_context=DataAgentContext(data_agent=...))`
- **REST:** body `{parent, messages:history+[...], dataAgentContext:{dataAgent}}`
- **History:** caller-managed — pass `results["history"]` back into the next call.

## 3. `'inline'` — Stateless, no stored agent

No agent is created at all. You pass the full `Context` inline with every request.
This is the target for **dynamic per-question routing** (ca-datasource-select →
ca-context-builder → chat inline): curate the minimal-sufficient tables, build a
context, ask, discard.

- **Requires:** `inline_context` (SDK: `Context`; REST: dict); you pass `history`
- **SDK:** `ChatRequest(parent, messages=history+[msg], inline_context=Context(...))`
- **REST:** body `{parent, messages:history+[...], inlineContext:{datasourceReferences, options}}`
- **History:** caller-managed.

## Response stream — what's in it and how to find each piece

`chat()` returns a list of messages (SDK `Message` objects / REST JSON dicts) in
**non-deterministic order** — a single answer is spread across many messages. Each
message carries a `system_message` (SDK) / `systemMessage` (REST) of one kind:

| message kind | field | what it holds |
|---|---|---|
| **text** | `text.parts` + `text.textType` | natural-language content — but *which* kind depends on `textType` (below) |
| **schema** | `schema` | schema-resolution step (which datasources/columns were used) |
| **data** | `data.generatedSql` / `data.result` | the generated SQL and the returned rows |
| **chart** | `chart` | a Vega-Lite chart spec (render to PNG with `vl_convert`) |

### `textType` — the key to text messages (verified live)

Text messages are NOT all the answer. The `textType` distinguishes them:

| `textType` (wire value) | meaning | where `parse_stream` puts it |
|---|---|---|
| `FINAL_RESPONSE` (1) | the actual answer | `text` |
| `THOUGHT` (2) | reasoning / planning narration | `thoughts` |
| `PROGRESS` (3) | progress updates ("Running a query") | `thoughts` |
| `FOLLOWUP_QUESTIONS` (4) | suggested next questions | `followups` |

> **Gotcha we hit:** the *last* text message is usually `FOLLOWUP_QUESTIONS`, not
> the answer — never take the last text as the answer. Also, the v0.3.0 SDK proto
> enum only knows values 0–3, but the live API returns **4**; the skill maps by
> wire value so `FOLLOWUP_QUESTIONS` is handled correctly (see api-surface.md).

### The easy path: `parse_stream(responses)`

Collapses the whole list into a clean dict — use this unless you need raw messages:

```python
p = ca.parse_stream(resp["results"]["raw"])   # or read resp["results"]["answer"]
p["text"]           # the FINAL_RESPONSE answer (str or None)
p["thoughts"]       # list[str] — THOUGHT + PROGRESS narration
p["followups"]      # list[str] — suggested follow-up questions
p["data"]           # list[dict] — returned rows from the last data result
p["generated_sql"]  # str — the SQL the agent ran
p["has_chart"]      # bool — a chart is present (render separately)
p["all_text"]       # list[str] — every text part, in order, unbucketed
```

`chat()` already returns this pre-parsed under `results["answer"]`, plus the raw
list under `results["raw"]` and (stateless modes) `results["history"]`.

### The precise path: `find_messages(responses, message_type, text_type=None)`

To locate specific raw messages in the list (e.g. to render a chart, inspect the
schema step, or pull only the answer text messages):

```python
raw = resp["results"]["raw"]
answers   = ca.find_messages(raw, "text", text_type="FINAL_RESPONSE")
followups = ca.find_messages(raw, "text", text_type="FOLLOWUP_QUESTIONS")
charts    = ca.find_messages(raw, "chart")   # -> render each with vl_convert
data_msgs = ca.find_messages(raw, "data")    # generated SQL + result rows
```

### Images / charts

`parse_stream` only flags `has_chart` (True/False) to keep the skill
dependency-light; it does not rasterize. To render, pull the chart messages with
`find_messages(raw, "chart")` and convert the Vega-Lite spec to PNG with
`vl_convert` (see the reference notebook's `handle_chart_response`). The raw
messages are always returned so a notebook can render on demand.
