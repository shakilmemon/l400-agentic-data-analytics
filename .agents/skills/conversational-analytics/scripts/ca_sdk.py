"""Conversational Analytics API — Python SDK implementation.

Mirrors ca_rest.py call-for-call (same function names, signatures, and order)
so the SDK and REST versions can be diffed side-by-side.

SDK: google-cloud-geminidataanalytics>=0.11.0
     (0.11.0 carries text_type on text messages; 0.3.0 did NOT — it returned no
      text_type at all, so answer/thought/followup could not be distinguished.
      Pin >=0.11.0. See references/api-surface.md.)
Auth: Application Default Credentials (current user) — aligns with the lab's
      OAuth pass-through requirement (do NOT use a privileged service account).

Return schema (house standard, matches the repo's other skills):
    {"status": "success"|"error", "tool_name": str, "messages": [str], "results": {...}}

Functional areas in this file:
    - ca-chat            : chat() dispatcher over all three modes  (BUILT)
    - ca-agent-manage    : create/get/list/delete data agents      (TODO)
    - ca-conversation    : conversation lifecycle + history         (TODO)
    - ca-context-builder : assemble Context / DatasourceReferences  (TODO)
    - ca-datasource-select : dynamic table router                   (TODO)
"""

from google.cloud import geminidataanalytics

import ca_common


@ca_common.trace("sdk_call", backend="sdk")
@ca_common.retry
def _call(fn, *args, _materialize=False, **kwargs):
    """Invoke an SDK client method with shared retry/backoff + tracing. For
    streaming calls, pass _materialize=True so the stream is drained inside the
    retry boundary (transient mid-stream errors get retried)."""
    result = fn(*args, **kwargs)
    return list(result) if _materialize else result


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ok(tool_name, results, messages=None):
    return {"status": "success", "tool_name": tool_name,
            "messages": messages or [], "results": results}


def _err(tool_name, message):
    return {"status": "error", "tool_name": tool_name,
            "messages": [message], "results": {}}


def _parent(project_id, location):
    return f"projects/{project_id}/locations/{location}"


# ---------------------------------------------------------------------------
# Response-stream parsing
# (ported from conversational_analytics_api_helpers.py in the vertex-ai-mlops
#  reference notebook; see references/chat-modes.md)
# ---------------------------------------------------------------------------

def _handle_text(resp):
    return "\n".join(getattr(resp, "parts"))


# Wire values for TextType. Map by value so we stay correct even when the SDK
# enum lags the service (older SDKs didn't name value 4 = FOLLOWUP_QUESTIONS; and
# 0.3.0 didn't carry text_type at all — hence the >=0.11.0 pin). Verified live.
_TEXT_TYPE_BY_VALUE = {0: "TEXT_TYPE_UNSPECIFIED", 1: "FINAL_RESPONSE",
                       2: "THOUGHT", 3: "PROGRESS", 4: "FOLLOWUP_QUESTIONS"}


def _text_type(resp):
    """Return the textType as a canonical string, robust to proto enum vs string
    vs int vs an unrecognized-but-known wire value (SDK lagging the API)."""
    tt = getattr(resp, "text_type", None)
    if tt is None:
        return None
    val = getattr(tt, "value", None)
    if isinstance(val, int) and val in _TEXT_TYPE_BY_VALUE:
        return _TEXT_TYPE_BY_VALUE[val]
    name = getattr(tt, "name", str(tt))
    if name.isdigit() and int(name) in _TEXT_TYPE_BY_VALUE:
        return _TEXT_TYPE_BY_VALUE[int(name)]
    return name.upper()


def _handle_data(resp):
    """Return (label, rows) for a data 'result' message, else (label, None)."""
    if "generated_sql" in resp:
        return ("generated_sql", resp.generated_sql)
    if "result" in resp:
        fields = [f.name for f in resp.result.schema.fields]
        rows = [{f: el[f] for f in fields} for el in resp.result.data]
        return ("data", rows)
    return ("data", None)


def parse_stream(responses):
    """Collapse a raw response stream into a clean answer dict.

    Distinguishes text_type (verified live via REST): THOUGHT (reasoning),
    FINAL_RESPONSE (the answer), FOLLOWUP_QUESTIONS (suggested next Qs). `text`
    is the FINAL_RESPONSE(s) — NOT the last text message (which is the follow-up
    questions and would be the wrong answer).

    Returns:
        text          : final natural-language answer (str or None)
        thoughts      : list of THOUGHT parts (reasoning/progress)
        followups     : list of suggested follow-up-question parts
        all_text      : every text part in order
        data          : row dicts from the last data result (or None)
        generated_sql : last generated SQL string (or None)
        has_chart     : bool (chart present in stream)
    Chart PNG rendering is left to the caller/notebook (needs vl_convert).
    """
    answer_parts, thoughts, followups, all_text = [], [], [], []
    data, sql, has_chart = None, None, False
    for resp in responses:
        try:
            m = resp.system_message
        except (AttributeError, TypeError):
            continue
        if "text" in m:
            tmsg = getattr(m, "text")
            t = _handle_text(tmsg)
            if not (t and t.strip()):
                continue
            all_text.append(t)
            tt = _text_type(tmsg)
            if tt == "FINAL_RESPONSE":
                answer_parts.append(t)
            elif tt == "FOLLOWUP_QUESTIONS":
                followups.append(t)
            elif tt in ("THOUGHT", "PROGRESS"):
                thoughts.append(t)
            elif tt in ("TEXT_TYPE_UNSPECIFIED",):
                # known-but-non-answer; don't contaminate the answer
                thoughts.append(t)
            elif tt is None:
                # type genuinely absent: safest to treat as answer
                answer_parts.append(t)
            else:
                # unrecognized future type: keep out of the answer, keep visible
                thoughts.append(t)
        elif "data" in m:
            kind, payload = _handle_data(getattr(m, "data"))
            if kind == "generated_sql" and payload:
                sql = payload
            elif kind == "data" and payload is not None:
                data = payload
        elif "chart" in m:
            has_chart = True
    return {"text": "\n".join(answer_parts) if answer_parts else None,
            "thoughts": thoughts, "followups": followups, "all_text": all_text,
            "data": data, "generated_sql": sql, "has_chart": has_chart}


def find_messages(responses, message_type, text_type=None):
    """Locate raw messages of a given kind in the response list.

    The stream mixes message kinds in non-deterministic order; use this instead
    of positional indexing. `message_type` is one of 'text', 'schema', 'data',
    'chart'. For text, optionally filter by `text_type` ('FINAL_RESPONSE',
    'THOUGHT', 'PROGRESS', 'FOLLOWUP_QUESTIONS'). Returns the matching raw
    Message objects (e.g. to render a chart or inspect generated SQL).
    """
    out = []
    for resp in responses:
        try:
            m = resp.system_message
        except (AttributeError, TypeError):
            continue
        if message_type not in m:
            continue
        if message_type == "text" and text_type is not None:
            if _text_type(getattr(m, "text")) != text_type:
                continue
        out.append(resp)
    return out


# ---------------------------------------------------------------------------
# ca-chat : unified dispatcher over the three interaction modes
# ---------------------------------------------------------------------------

def chat(project_id, location, question, context_mode,
         agent_name=None, conversation_name=None,
         inline_context=None, history=None, timeout=300):
    """Send a question to the Conversational Analytics API.

    context_mode:
        'conversation' — STATEFUL. Server holds history. Needs conversation_name
                         + agent_name.
        'agent'        — STATELESS with a stored agent. Caller passes `history`.
                         Needs agent_name.
        'inline'       — STATELESS, no stored agent. Needs inline_context
                         (a geminidataanalytics.Context, e.g. from
                         ca-context-builder). Caller passes `history`.

    Returns the house-standard dict; results holds the parsed answer plus the
    raw response count. Raw Message objects are returned under results['raw']
    for advanced use.
    """
    tool = "chat"
    try:
        client = geminidataanalytics.DataChatServiceClient()

        user_message = geminidataanalytics.Message()
        user_message.user_message.text = question

        request_kwargs = {"parent": _parent(project_id, location)}

        if context_mode == "conversation":
            if not (conversation_name and agent_name):
                return _err(tool, "conversation mode requires conversation_name and agent_name")
            request_kwargs["messages"] = [user_message]
            ref = geminidataanalytics.ConversationReference()
            ref.conversation = conversation_name
            ref.data_agent_context.data_agent = agent_name
            request_kwargs["conversation_reference"] = ref
        elif context_mode == "agent":
            if not agent_name:
                return _err(tool, "agent mode requires agent_name")
            request_kwargs["messages"] = (history or []) + [user_message]
            ctx = geminidataanalytics.DataAgentContext()
            ctx.data_agent = agent_name
            request_kwargs["data_agent_context"] = ctx
        elif context_mode == "inline":
            if inline_context is None:
                return _err(tool, "inline mode requires inline_context (a Context)")
            request_kwargs["messages"] = (history or []) + [user_message]
            request_kwargs["inline_context"] = inline_context
        else:
            return _err(tool, "context_mode must be 'conversation', 'agent', or 'inline'")

        request = geminidataanalytics.ChatRequest(**request_kwargs)
        responses = _call(client.chat, request=request, timeout=timeout,
                          _materialize=True)

        parsed = parse_stream(responses)
        # For stateless modes, the caller needs the updated history to continue.
        updated_history = request_kwargs["messages"] + responses
        results = {"answer": parsed,
                   "response_count": len(responses),
                   "history": updated_history,
                   "raw": responses}
        msg = f"Received {len(responses)} responses in '{context_mode}' mode."
        return _ok(tool, results, [msg])
    except Exception as e:
        return _err(tool, f"chat failed: {e}")


# ---------------------------------------------------------------------------
# ca-agent-manage : create / get / list / delete stored data agents
# ---------------------------------------------------------------------------

def create_data_agent(project_id, location, data_agent_id, context,
                      display_name=None, description=None, labels=None):
    """Create a stored data agent (the stateful/durable path).

    `context` is a geminidataanalytics.Context (from ca-context-builder, or built
    inline). `display_name`/`description`/`labels` set the agent identity fields
    (verified surface — see references/api-surface.md).

    Uses create_data_agent_sync with an explicit data_agent_id (no numeric-name
    retry loop needed). Returns the created agent's resource name.
    """
    tool = "create_data_agent"
    try:
        client = geminidataanalytics.DataAgentServiceClient()

        data_agent = geminidataanalytics.DataAgent()
        data_agent.data_analytics_agent.published_context = context
        data_agent.name = (
            f"{_parent(project_id, location)}/dataAgents/{data_agent_id}")
        if display_name is not None:
            data_agent.display_name = display_name
        if description is not None:
            data_agent.description = description
        if labels:
            data_agent.labels = labels

        request = geminidataanalytics.CreateDataAgentRequest(
            parent=_parent(project_id, location),
            data_agent_id=data_agent_id,
            data_agent=data_agent,
        )
        response = _call(client.create_data_agent_sync, request=request)
        return _ok(tool, {"name": response.name, "data_agent_id": data_agent_id},
                   [f"Created data agent '{data_agent_id}'."])
    except Exception as e:
        return _err(tool, f"create_data_agent failed: {e}")


def update_data_agent(project_id, location, data_agent_id, context=None,
                      display_name=None, description=None, labels=None):
    """Update an existing data agent. Only provided fields are changed
    (update_mask built from non-None args)."""
    tool = "update_data_agent"
    try:
        client = geminidataanalytics.DataAgentServiceClient()
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        data_agent = geminidataanalytics.DataAgent()
        data_agent.name = name
        paths = []
        if context is not None:
            data_agent.data_analytics_agent.published_context = context
            paths.append("data_analytics_agent.published_context")
        if display_name is not None:
            data_agent.display_name = display_name
            paths.append("display_name")
        if description is not None:
            data_agent.description = description
            paths.append("description")
        if labels is not None:
            data_agent.labels = labels
            paths.append("labels")
        if not paths:
            return _err(tool, "nothing to update (all fields None)")
        request = geminidataanalytics.UpdateDataAgentRequest(
            data_agent=data_agent,
            update_mask={"paths": paths})
        _call(client.update_data_agent, request=request)
        return _ok(tool, {"name": name, "updated": paths},
                   [f"Updated data agent '{data_agent_id}' ({', '.join(paths)})."])
    except Exception as e:
        return _err(tool, f"update_data_agent failed: {e}")


def create_or_update_data_agent(project_id, location, data_agent_id, context,
                                display_name=None, description=None, labels=None):
    """Idempotent: create the agent, or update it if it already exists.

    Lab cells get re-run constantly; this survives re-runs cleanly instead of
    failing on 'already exists'.
    """
    tool = "create_or_update_data_agent"
    existing = get_data_agent(project_id, location, data_agent_id)
    if existing["status"] == "success":
        r = update_data_agent(project_id, location, data_agent_id, context=context,
                              display_name=display_name, description=description,
                              labels=labels)
        if r["status"] == "success":
            r["results"]["created"] = False
            r["tool_name"] = tool
        return r
    if "soft-deleted" in (existing.get("messages") or [""])[0]:
        # Stuck state: get() says deleted but the id is still reserved, so create
        # 409s and there is no undelete API. Purge is ~30 days out. Fail with a
        # clear, actionable message instead of a raw 409/400.
        return _err(tool, f"data agent '{data_agent_id}' is soft-deleted and "
                          f"cannot be recreated until purged (~30 days), and the "
                          f"API has no undelete. Use a different data_agent_id, or "
                          f"avoid hard-deleting agents you intend to re-run.")
    r = create_data_agent(project_id, location, data_agent_id, context,
                          display_name=display_name, description=description,
                          labels=labels)
    if r["status"] == "success":
        r["results"]["created"] = True
        r["tool_name"] = tool
    return r


def get_data_agent(project_id, location, data_agent_id):
    """Retrieve a stored data agent by id."""
    tool = "get_data_agent"
    try:
        client = geminidataanalytics.DataAgentServiceClient()
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        agent = _call(client.get_data_agent, name=name)
        # A soft-deleted (tombstoned) agent still returns from get until it is
        # purged (~30 days). Treat it as NOT FOUND so create-or-update recreates
        # instead of trying to update a dead resource (which 400s).
        if getattr(agent, "delete_time", None):
            return _err(tool, f"data agent '{data_agent_id}' is soft-deleted "
                              f"(delete_time set); treat as not found")
        return _ok(tool, {
            "name": agent.name,
            "display_name": getattr(agent, "display_name", None),
            "description": getattr(agent, "description", None),
            "labels": dict(getattr(agent, "labels", {}) or {}),
        }, [f"Retrieved data agent '{data_agent_id}'."])
    except Exception as e:
        return _err(tool, f"get_data_agent failed: {e}")


def list_data_agents(project_id, location, filter_str=None):
    """List data agents in the project/location. Optional API filter string
    (e.g. filter on labels) to enumerate agents by config or domain."""
    tool = "list_data_agents"
    try:
        client = geminidataanalytics.DataAgentServiceClient()
        kwargs = {"parent": _parent(project_id, location)}
        if filter_str:
            kwargs["filter"] = filter_str
        agents = [{
            "name": a.name,
            "display_name": getattr(a, "display_name", None),
            "labels": dict(getattr(a, "labels", {}) or {}),
        } for a in _call(client.list_data_agents, **kwargs)]
        return _ok(tool, {"agents": agents, "count": len(agents)},
                   [f"Found {len(agents)} data agent(s)."])
    except Exception as e:
        return _err(tool, f"list_data_agents failed: {e}")


def delete_data_agent(project_id, location, data_agent_id):
    """Delete a stored data agent by id."""
    tool = "delete_data_agent"
    try:
        client = geminidataanalytics.DataAgentServiceClient()
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        _call(client.delete_data_agent, name=name)
        return _ok(tool, {"name": name}, [f"Deleted data agent '{data_agent_id}'."])
    except Exception as e:
        return _err(tool, f"delete_data_agent failed: {e}")


# ---------------------------------------------------------------------------
# ca-conversation : durable conversation lifecycle + history (stateful path)
# ---------------------------------------------------------------------------

def create_conversation(project_id, location, conversation_id, agent_id):
    """Create a durable conversation bound to a stored agent (stateful chat).

    After this, call chat(..., context_mode='conversation',
    conversation_name=<returned name>, agent_name=<agent resource name>).
    """
    tool = "create_conversation"
    try:
        client = geminidataanalytics.DataChatServiceClient()
        agent_name = f"{_parent(project_id, location)}/dataAgents/{agent_id}"
        conversation = geminidataanalytics.Conversation()
        conversation.agents = [agent_name]
        conversation.name = (
            f"{_parent(project_id, location)}/conversations/{conversation_id}")
        request = geminidataanalytics.CreateConversationRequest(
            parent=_parent(project_id, location),
            conversation_id=conversation_id,
            conversation=conversation,
        )
        response = _call(client.create_conversation, request=request)
        return _ok(tool, {"name": response.name, "conversation_id": conversation_id},
                   [f"Created conversation '{conversation_id}'."])
    except Exception as e:
        return _err(tool, f"create_conversation failed: {e}")


def get_conversation(project_id, location, conversation_id):
    """Retrieve a conversation by id."""
    tool = "get_conversation"
    try:
        client = geminidataanalytics.DataChatServiceClient()
        name = f"{_parent(project_id, location)}/conversations/{conversation_id}"
        conv = _call(client.get_conversation, name=name)
        return _ok(tool, {"name": conv.name, "conversation_id": conversation_id},
                   [f"Retrieved conversation '{conversation_id}'."])
    except Exception as e:
        return _err(tool, f"get_conversation failed: {e}")


def get_or_create_conversation(project_id, location, conversation_id, agent_id):
    """Idempotent: return the existing conversation, or create it.

    Conversations have no update semantics, so re-running a notebook/lab cell with
    a fixed conversation_id 409s on create. This returns the existing one instead.
    """
    tool = "get_or_create_conversation"
    existing = get_conversation(project_id, location, conversation_id)
    if existing["status"] == "success":
        existing["results"]["created"] = False
        existing["tool_name"] = tool
        return existing
    r = create_conversation(project_id, location, conversation_id, agent_id)
    if r["status"] == "success":
        r["results"]["created"] = True
        r["tool_name"] = tool
    return r


def list_messages(conversation_name, filter_str=None, page_size=None):
    """List messages (history) in a durable conversation.

    `conversation_name` is the full resource path returned by create_conversation.
    Optional `filter_str` (server-side filter, e.g. on create_time) and
    `page_size` (per-page hint; all pages are still drained). The SDK pager
    auto-follows page tokens, so the full history is returned regardless.
    """
    tool = "list_messages"
    try:
        client = geminidataanalytics.DataChatServiceClient()
        # filter/page_size aren't flattened method kwargs — they live on the
        # request object (the flattened method only takes `parent`).
        req = geminidataanalytics.ListMessagesRequest(parent=conversation_name)
        if filter_str:
            req.filter = filter_str
        if page_size:
            req.page_size = page_size
        messages = _call(client.list_messages, request=req, _materialize=True)
        return _ok(tool, {"messages": messages, "count": len(messages)},
                   [f"Retrieved {len(messages)} message(s)."])
    except Exception as e:
        return _err(tool, f"list_messages failed: {e}")


def list_conversations(project_id, location, filter_str=None, page_size=None):
    """List durable conversations in the project/location.

    Optional `filter_str` — a server-side filter string. The Conversation
    resource carries an `agents` field, so filtering by agent (to enumerate all
    conversations for one deployed agent) is the primary use for the trust layer.
    `page_size` is a per-page hint; the SDK pager drains all pages either way.
    Returns lightweight dicts (name, agents, id) — call list_messages() per
    conversation to pull the turns.
    """
    tool = "list_conversations"
    try:
        client = geminidataanalytics.DataChatServiceClient()
        # filter/page_size live on the request object, not as flattened kwargs.
        req = geminidataanalytics.ListConversationsRequest(
            parent=_parent(project_id, location))
        if filter_str:
            req.filter = filter_str
        if page_size:
            req.page_size = page_size
        convs = [{
            "name": c.name,
            "agents": list(getattr(c, "agents", []) or []),
            "conversation_id": c.name.rsplit("/", 1)[-1] if c.name else None,
        } for c in _call(client.list_conversations, request=req,
                         _materialize=True)]
        return _ok(tool, {"conversations": convs, "count": len(convs)},
                   [f"Found {len(convs)} conversation(s)."])
    except Exception as e:
        return _err(tool, f"list_conversations failed: {e}")


def delete_conversation(project_id, location, conversation_id):
    """Delete a durable conversation by id (cleans up the stateful path)."""
    tool = "delete_conversation"
    try:
        client = geminidataanalytics.DataChatServiceClient()
        name = f"{_parent(project_id, location)}/conversations/{conversation_id}"
        _call(client.delete_conversation, name=name)
        return _ok(tool, {"name": name},
                   [f"Deleted conversation '{conversation_id}'."])
    except Exception as e:
        return _err(tool, f"delete_conversation failed: {e}")


def _inner_messages(list_messages_result):
    """Unwrap StorageMessage -> inner Message, sorted oldest-first.

    list_messages returns StorageMessage (message_id + message); the API returns
    them newest-first. We sort by the inner message timestamp ascending so turns
    reconstruct in the order they were asked.
    """
    inner = [getattr(sm, "message", sm)
             for sm in list_messages_result["results"]["messages"]]
    inner.sort(key=lambda m: getattr(m, "timestamp", None) or 0)
    return inner


def get_conversation_turns(conversation_name, filter_str=None, page_size=None):
    """Reconstruct a stateful conversation into {prompt, response, timestamp}
    turns — the NATIVE trace-retrieval path (no ADK, no plugin).

    Fetches the stored history (list_messages), unwraps StorageMessage, groups by
    user turn: each user_message opens a turn; the system_messages that follow are
    parsed (via parse_stream) into that turn's final answer, thoughts, followups,
    data, and SQL. This is how you audit what a deployed stateful agent actually
    answered — the basis for acceptance/observability/evaluation.

    Returns results = {turns: [{prompt, response, timestamp, thoughts, followups,
    data, generated_sql}], count}.
    """
    tool = "get_conversation_turns"
    try:
        lm = list_messages(conversation_name, filter_str=filter_str,
                           page_size=page_size)
        if lm["status"] != "success":
            return _err(tool, lm["messages"][0])
        turns, current, sys_batch = [], None, []

        def _flush():
            if current is None:
                return
            parsed = parse_stream(sys_batch)
            turns.append({
                "prompt": current["prompt"],
                "response": parsed["text"],
                "timestamp": current["timestamp"],
                "thoughts": parsed["thoughts"],
                "followups": parsed["followups"],
                "data": parsed["data"],
                "generated_sql": parsed["generated_sql"],
            })

        for m in _inner_messages(lm):
            if "user_message" in m:
                _flush()
                ts = getattr(m, "timestamp", None)
                current = {"prompt": m.user_message.text,
                           "timestamp": ts.isoformat() if ts else None}
                sys_batch = []
            elif "system_message" in m and current is not None:
                sys_batch.append(m)
        _flush()
        return _ok(tool, {"turns": turns, "count": len(turns)},
                   [f"Reconstructed {len(turns)} turn(s)."])
    except Exception as e:
        return _err(tool, f"get_conversation_turns failed: {e}")


# ---------------------------------------------------------------------------
# ca-context-builder : assemble a Context / DatasourceReferences from primitives
# This is the seam where the router (ca-datasource-select) plugs in, and the
# bridge from the lab's Dataplex glossary artifacts into CAI.
#
# NOTE (verified against v0.3.0 by introspection, differs from public docs):
#   * Glossaries ARE a structured field: Context.glossary_terms (GlossaryTerm
#     with display_name/description). No need to hand-author YAML for terms.
#   * ExampleQuery has only natural_language_question + sql_query — NO parameters
#     in this SDK version.
#   * User-defined functions (UserFunctions/BigQueryRoutine) are NOT present in
#     v0.3.0 — omitted here; revisit when the SDK adds them.
# These builders return SDK objects (not dicts) for use with ca_sdk functions.
# ---------------------------------------------------------------------------

RECOMMENDED_TABLE_THRESHOLD = 20  # Google best-practice: reconsider beyond this.


def _parse_table(t):
    """Accept 'project.dataset.table' string or a dict and return components."""
    if isinstance(t, str):
        parts = t.split(".")
        if len(parts) != 3:
            raise ValueError(f"table string must be 'project.dataset.table', got {t!r}")
        return {"project_id": parts[0], "dataset_id": parts[1], "table_id": parts[2]}
    return {"project_id": t["project_id"], "dataset_id": t["dataset_id"],
            "table_id": t["table_id"], "schema_context": t.get("schema_context")}


def build_table_references(tables):
    """Build a DatasourceReferences from a list of tables.

    Each table is 'project.dataset.table' or a dict optionally carrying
    'schema_context' = {description, synonyms, tags, fields:[{name, description,
    synonyms, tags}]} for per-table/column structured context.
    """
    tool = "build_table_references"
    try:
        if len(tables) > RECOMMENDED_TABLE_THRESHOLD:
            note = (f"WARNING: {len(tables)} tables exceeds the recommended "
                    f"threshold ({RECOMMENDED_TABLE_THRESHOLD}); accuracy may drop.")
        else:
            note = f"{len(tables)} table(s) referenced."

        refs = []
        for t in tables:
            info = _parse_table(t)
            ref = geminidataanalytics.BigQueryTableReference(
                project_id=info["project_id"], dataset_id=info["dataset_id"],
                table_id=info["table_id"])
            sc = info.get("schema_context")
            if sc:
                if sc.get("description"):
                    ref.schema.description = sc["description"]
                if sc.get("synonyms"):
                    ref.schema.synonyms = sc["synonyms"]
                if sc.get("tags"):
                    ref.schema.tags = sc["tags"]
                for col in sc.get("fields", []):
                    field = geminidataanalytics.Field(name=col["name"])
                    if col.get("description"):
                        field.description = col["description"]
                    if col.get("synonyms"):
                        field.synonyms = col["synonyms"]
                    if col.get("tags"):
                        field.tags = col["tags"]
                    ref.schema.fields.append(field)
            refs.append(ref)

        datasource = geminidataanalytics.DatasourceReferences()
        datasource.bq.table_references = refs
        return _ok(tool, {"datasource_references": datasource,
                          "table_count": len(refs)}, [note])
    except Exception as e:
        return _err(tool, f"build_table_references failed: {e}")


def build_glossary_terms(terms):
    """Build a list of GlossaryTerm from [{display_name, description}] dicts.

    This is the lab's Dataplex-glossary -> CAI bridge (structured, not YAML).
    """
    tool = "build_glossary_terms"
    try:
        out = []
        for t in terms:
            gt = geminidataanalytics.GlossaryTerm()
            gt.display_name = t["display_name"]
            if t.get("description"):
                gt.description = t["description"]
            out.append(gt)
        return _ok(tool, {"glossary_terms": out, "count": len(out)},
                   [f"Built {len(out)} glossary term(s)."])
    except Exception as e:
        return _err(tool, f"build_glossary_terms failed: {e}")


def build_example_queries(pairs):
    """Build a list of ExampleQuery (golden queries) from
    [{natural_language_question, sql_query}] dicts.

    v0.3.0 ExampleQuery has no `parameters` field; parameterized golden queries
    are not supported by this SDK version.
    """
    tool = "build_example_queries"
    try:
        out = [geminidataanalytics.ExampleQuery(
                   natural_language_question=p["natural_language_question"],
                   sql_query=p["sql_query"])
               for p in pairs]
        return _ok(tool, {"example_queries": out, "count": len(out)},
                   [f"Built {len(out)} example query(ies)."])
    except Exception as e:
        return _err(tool, f"build_example_queries failed: {e}")


def build_context(system_instruction, datasource_references,
                  example_queries=None, glossary_terms=None,
                  enable_python=True, max_billed_bytes=None):
    """Assemble a Context from primitives (all SDK objects).

    system_instruction : str (free text / YAML for relationships & extra guidance)
    datasource_references : from build_table_references()['results'][...]
    example_queries : from build_example_queries() (optional)
    glossary_terms  : from build_glossary_terms() (optional)
    """
    tool = "build_context"
    try:
        context = geminidataanalytics.Context()
        context.system_instruction = system_instruction
        context.datasource_references = datasource_references

        options = geminidataanalytics.ConversationOptions()
        options.analysis.python.enabled = bool(enable_python)
        if max_billed_bytes is not None:
            options.datasource.big_query_max_billed_bytes = int(max_billed_bytes)
        context.options = options

        if example_queries:
            context.example_queries = example_queries
        if glossary_terms:
            context.glossary_terms = glossary_terms

        return _ok(tool, {"context": context},
                   ["Built Context (system_instruction + datasources"
                    + (", example_queries" if example_queries else "")
                    + (", glossary_terms" if glossary_terms else "") + ")."])
    except Exception as e:
        return _err(tool, f"build_context failed: {e}")
