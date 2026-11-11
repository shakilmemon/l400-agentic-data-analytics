"""Conversational Analytics API — REST-from-Python implementation.

Mirrors ca_sdk.py call-for-call (same function names, signatures, and order)
so the SDK and REST versions can be diffed side-by-side. This version shows
exactly what the SDK does under the hood: raw HTTP + JSON.

Auth: Application Default Credentials (current user) via google.auth — aligns
      with the lab's OAuth pass-through requirement.

Endpoints (note the version split, verified against the HTTP build guide):
    :chat                    -> v1
    dataAgents:createSync    -> v1beta
    conversations            -> v1

Return schema matches ca_sdk.py and the repo's other skills:
    {"status": "success"|"error", "tool_name": str, "messages": [str], "results": {...}}

Functional areas in this file:
    - ca-chat            : chat() dispatcher over all three modes  (BUILT)
    - ca-agent-manage    : create/get/list/delete data agents      (TODO)
    - ca-conversation    : conversation lifecycle + history         (TODO)
    - ca-context-builder : assemble datasource/context dicts        (TODO)
    - ca-datasource-select : dynamic table router                   (TODO)
"""

import google.auth
import google.auth.transport.requests
import requests

import ca_common

_BASE = "https://geminidataanalytics.googleapis.com"
_BASE_V1 = f"{_BASE}/v1"
_BASE_V1BETA = f"{_BASE}/v1beta"


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


def _access_token():
    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _headers():
    return {"Content-Type": "application/json",
            "Authorization": f"Bearer {_access_token()}"}


@ca_common.trace("rest_post", backend="rest")
@ca_common.retry
def _post(url, body, params=None, timeout=300):
    resp = requests.post(url, json=body, params=params,
                         headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


@ca_common.trace("rest_get", backend="rest")
@ca_common.retry
def _get(url, params=None, timeout=300):
    resp = requests.get(url, params=params, headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


@ca_common.trace("rest_delete", backend="rest")
@ca_common.retry
def _delete(url, timeout=300):
    resp = requests.delete(url, headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


@ca_common.trace("rest_patch", backend="rest")
@ca_common.retry
def _patch(url, body, params=None, timeout=300):
    resp = requests.patch(url, json=body, params=params,
                          headers=_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Response-stream parsing
# The :chat endpoint returns a streamed JSON array of Message objects. Each
# element carries a "systemMessage" with one of text/data/chart (camelCase
# over REST, vs snake_case system_message in the SDK).
# ---------------------------------------------------------------------------

def _handle_text(text_msg):
    return "\n".join(text_msg.get("parts", []))


def _text_type(text_msg):
    # REST returns textType as a string name (camelCase key). May be absent.
    return text_msg.get("textType") or text_msg.get("text_type")


def _handle_data(data_msg):
    if "generatedSql" in data_msg:
        return ("generated_sql", data_msg["generatedSql"])
    if "result" in data_msg:
        result = data_msg["result"]
        fields = [f["name"] for f in result.get("schema", {}).get("fields", [])]
        rows = [{f: el.get(f) for f in fields} for el in result.get("data", [])]
        return ("data", rows)
    return ("data", None)


def parse_stream(responses):
    """Collapse the parsed JSON message list into a clean answer dict.

    Distinguishes textType (verified live): THOUGHT (reasoning/progress),
    FINAL_RESPONSE (the actual answer), FOLLOWUP_QUESTIONS (suggested next Qs).
    `text` is the concatenated FINAL_RESPONSE(s) — NOT the last text message,
    which would wrongly return the follow-up questions.

    Returns: text, thoughts[], followups[], all_text[], data, generated_sql,
    has_chart. Same shape as ca_sdk.parse_stream.
    """
    answer_parts, thoughts, followups, all_text = [], [], [], []
    data, sql, has_chart = None, None, False
    for resp in responses:
        m = resp.get("systemMessage", {})
        if "text" in m:
            t = _handle_text(m["text"])
            if not (t and t.strip()):
                continue
            all_text.append(t)
            tt = _text_type(m["text"])
            if tt == "FINAL_RESPONSE":
                answer_parts.append(t)
            elif tt == "FOLLOWUP_QUESTIONS":
                followups.append(t)
            elif tt in ("THOUGHT", "PROGRESS", "TEXT_TYPE_UNSPECIFIED"):
                thoughts.append(t)
            elif tt is None:
                # type genuinely absent: safest to treat as answer
                answer_parts.append(t)
            else:
                # unrecognized future type: keep out of the answer, keep visible
                thoughts.append(t)
        elif "data" in m:
            kind, payload = _handle_data(m["data"])
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
    """Locate raw messages of a given kind in the response list (REST dicts).

    `message_type` is one of 'text', 'schema', 'data', 'chart'. For text,
    optionally filter by `text_type` ('FINAL_RESPONSE', 'THOUGHT', 'PROGRESS',
    'FOLLOWUP_QUESTIONS'). Returns the matching raw message dicts. Mirrors
    ca_sdk.find_messages.
    """
    out = []
    for resp in responses:
        m = resp.get("systemMessage", {})
        if message_type not in m:
            continue
        if message_type == "text" and text_type is not None:
            if _text_type(m["text"]) != text_type:
                continue
        out.append(resp)
    return out


# ---------------------------------------------------------------------------
# ca-chat : unified dispatcher over the three interaction modes
# ---------------------------------------------------------------------------

def chat(project_id, location, question, context_mode,
         agent_name=None, conversation_name=None,
         inline_context=None, history=None, timeout=300):
    """Send a question to the Conversational Analytics API :chat endpoint.

    Same semantics as ca_sdk.chat. Here `inline_context` is a plain dict
    (e.g. {"datasource_references": {...}, "options": {...}}) rather than a
    Context proto. `history` is a list of message dicts.

    Returns the house-standard dict; results holds the parsed answer, the raw
    decoded response list, and the updated history for stateless continuation.
    """
    tool = "chat"
    try:
        user_message = {"userMessage": {"text": question}}
        body = {"parent": _parent(project_id, location)}

        if context_mode == "conversation":
            if not (conversation_name and agent_name):
                return _err(tool, "conversation mode requires conversation_name and agent_name")
            body["messages"] = [user_message]
            body["conversationReference"] = {
                "conversation": conversation_name,
                "dataAgentContext": {"dataAgent": agent_name},
            }
        elif context_mode == "agent":
            if not agent_name:
                return _err(tool, "agent mode requires agent_name")
            if not agent_name.startswith("projects/"):
                agent_name = f"{_parent(project_id, location)}/dataAgents/{agent_name}"
            body["messages"] = (history or []) + [user_message]
            body["dataAgentContext"] = {"dataAgent": agent_name}
        elif context_mode == "inline":
            if inline_context is None:
                return _err(tool, "inline mode requires inline_context (a dict)")
            body["messages"] = (history or []) + [user_message]
            body["inlineContext"] = inline_context
        else:
            return _err(tool, "context_mode must be 'conversation', 'agent', or 'inline'")

        url = f"{_BASE_V1}/{_parent(project_id, location)}:chat"
        resp = _post(url, body, timeout=timeout)
        responses = resp.json()
        # The streamed response decodes to a JSON array of Message objects.
        if isinstance(responses, dict):
            responses = [responses]

        parsed = parse_stream(responses)
        updated_history = body["messages"] + responses
        results = {"answer": parsed,
                   "response_count": len(responses),
                   "history": updated_history,
                   "raw": responses}
        msg = f"Received {len(responses)} responses in '{context_mode}' mode."
        return _ok(tool, results, [msg])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"chat HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"chat failed: {e}")


# ---------------------------------------------------------------------------
# ca-agent-manage : create / get / list / delete stored data agents
# ---------------------------------------------------------------------------

def create_data_agent(project_id, location, data_agent_id, context,
                      display_name=None, description=None, labels=None):
    """Create a stored data agent (stateful/durable path).

    `context` here is a dict (published_context body: datasource_references,
    system_instruction, options, example_queries, ...). Uses the synchronous
    dataAgents:createSync endpoint (NOTE: v1beta, unlike :chat which is v1).
    """
    tool = "create_data_agent"
    try:
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        data_agent = {
            "name": name,
            "data_analytics_agent": {"published_context": context},
        }
        if display_name is not None:
            data_agent["displayName"] = display_name
        if description is not None:
            data_agent["description"] = description
        if labels:
            data_agent["labels"] = labels

        url = (f"{_BASE_V1BETA}/{_parent(project_id, location)}"
               f"/dataAgents:createSync")
        # createSync takes data_agent_id as a query parameter.
        resp = _post(url, data_agent, params={"data_agent_id": data_agent_id})
        return _ok(tool, {"name": name, "data_agent_id": data_agent_id,
                          "response": resp.json()},
                   [f"Created data agent '{data_agent_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"create_data_agent HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"create_data_agent failed: {e}")


def update_data_agent(project_id, location, data_agent_id, context=None,
                      display_name=None, description=None, labels=None):
    """Update an existing data agent (PATCH with updateMask). Only provided
    fields are changed."""
    tool = "update_data_agent"
    try:
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        body = {"name": name}
        paths = []
        if context is not None:
            body["dataAnalyticsAgent"] = {"publishedContext": context}
            paths.append("data_analytics_agent.published_context")
        if display_name is not None:
            body["displayName"] = display_name
            paths.append("display_name")
        if description is not None:
            body["description"] = description
            paths.append("description")
        if labels is not None:
            body["labels"] = labels
            paths.append("labels")
        if not paths:
            return _err(tool, "nothing to update (all fields None)")
        url = f"{_BASE_V1BETA}/{name}"
        _patch(url, body, params={"updateMask": ",".join(paths)})
        return _ok(tool, {"name": name, "updated": paths},
                   [f"Updated data agent '{data_agent_id}' ({', '.join(paths)})."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"update_data_agent HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"update_data_agent failed: {e}")


def create_or_update_data_agent(project_id, location, data_agent_id, context,
                                display_name=None, description=None, labels=None):
    """Idempotent: create the agent, or update it if it already exists."""
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
        url = (f"{_BASE_V1BETA}/{_parent(project_id, location)}"
               f"/dataAgents/{data_agent_id}")
        agent = _get(url).json()
        # Soft-deleted (tombstoned) agents still return until purged; treat as
        # NOT FOUND so create-or-update recreates instead of 400-ing on update.
        if agent.get("deleteTime"):
            return _err(tool, f"data agent '{data_agent_id}' is soft-deleted "
                              f"(deleteTime set); treat as not found")
        return _ok(tool, {
            "name": agent.get("name"),
            "display_name": agent.get("displayName"),
            "description": agent.get("description"),
            "labels": agent.get("labels", {}),
        }, [f"Retrieved data agent '{data_agent_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"get_data_agent HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"get_data_agent failed: {e}")


def _paginate(url, item_key, base_params=None, page_size=100):
    """Yield all items across pages, following nextPageToken to completion.

    Prevents silent truncation: a single _get returns only the first page.
    """
    params = dict(base_params or {})
    params["pageSize"] = page_size
    token = None
    while True:
        if token:
            params["pageToken"] = token
        body = _get(url, params=params).json()
        for item in body.get(item_key, []):
            yield item
        token = body.get("nextPageToken")
        if not token:
            break


def list_data_agents(project_id, location, filter_str=None):
    """List ALL data agents (paginated). Optional API filter (e.g. on labels)."""
    tool = "list_data_agents"
    try:
        url = f"{_BASE_V1BETA}/{_parent(project_id, location)}/dataAgents"
        base = {"filter": filter_str} if filter_str else None
        agents = [{
            "name": a.get("name"),
            "display_name": a.get("displayName"),
            "labels": a.get("labels", {}),
        } for a in _paginate(url, "dataAgents", base)]
        return _ok(tool, {"agents": agents, "count": len(agents)},
                   [f"Found {len(agents)} data agent(s)."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"list_data_agents HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"list_data_agents failed: {e}")


def delete_data_agent(project_id, location, data_agent_id):
    """Delete a stored data agent by id."""
    tool = "delete_data_agent"
    try:
        name = f"{_parent(project_id, location)}/dataAgents/{data_agent_id}"
        url = f"{_BASE_V1BETA}/{name}"
        _delete(url)
        return _ok(tool, {"name": name}, [f"Deleted data agent '{data_agent_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"delete_data_agent HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"delete_data_agent failed: {e}")


# ---------------------------------------------------------------------------
# ca-conversation : durable conversation lifecycle + history (stateful path)
# ---------------------------------------------------------------------------

def create_conversation(project_id, location, conversation_id, agent_id):
    """Create a durable conversation bound to a stored agent (stateful chat)."""
    tool = "create_conversation"
    try:
        agent_name = f"{_parent(project_id, location)}/dataAgents/{agent_id}"
        name = f"{_parent(project_id, location)}/conversations/{conversation_id}"
        body = {"agents": [agent_name], "name": name}
        url = (f"{_BASE_V1}/{_parent(project_id, location)}/conversations"
               f"?conversation_id={conversation_id}")
        resp = _post(url, body)
        return _ok(tool, {"name": name, "conversation_id": conversation_id,
                          "response": resp.json()},
                   [f"Created conversation '{conversation_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"create_conversation HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"create_conversation failed: {e}")


def get_conversation(project_id, location, conversation_id):
    """Retrieve a conversation by id."""
    tool = "get_conversation"
    try:
        name = f"{_parent(project_id, location)}/conversations/{conversation_id}"
        body = _get(f"{_BASE_V1}/{name}").json()
        return _ok(tool, {"name": body.get("name", name),
                          "conversation_id": conversation_id},
                   [f"Retrieved conversation '{conversation_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"get_conversation HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"get_conversation failed: {e}")


def get_or_create_conversation(project_id, location, conversation_id, agent_id):
    """Idempotent: return the existing conversation, or create it. Mirrors
    ca_sdk.get_or_create_conversation (survives lab-cell re-runs)."""
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
    Optional `filter_str` (server-side filter) and `page_size` (per-page hint);
    _paginate follows nextPageToken so the full history is returned either way.
    """
    tool = "list_messages"
    try:
        url = f"{_BASE_V1}/{conversation_name}/messages"
        base = {"filter": filter_str} if filter_str else None
        messages = list(_paginate(url, "messages", base,
                                  page_size=page_size or 100))
        return _ok(tool, {"messages": messages, "count": len(messages)},
                   [f"Retrieved {len(messages)} message(s)."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"list_messages HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"list_messages failed: {e}")


def list_conversations(project_id, location, filter_str=None, page_size=None):
    """List ALL durable conversations (paginated). Optional server-side filter.

    The Conversation resource carries an `agents` field, so filtering by agent is
    the primary use for the trust layer. Returns lightweight dicts; call
    list_messages() per conversation to pull the turns. Mirrors ca_sdk.
    """
    tool = "list_conversations"
    try:
        url = f"{_BASE_V1}/{_parent(project_id, location)}/conversations"
        base = {"filter": filter_str} if filter_str else None
        convs = [{
            "name": c.get("name"),
            "agents": c.get("agents", []) or [],
            "conversation_id": (c.get("name") or "").rsplit("/", 1)[-1] or None,
        } for c in _paginate(url, "conversations", base,
                             page_size=page_size or 100)]
        return _ok(tool, {"conversations": convs, "count": len(convs)},
                   [f"Found {len(convs)} conversation(s)."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"list_conversations HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"list_conversations failed: {e}")


def delete_conversation(project_id, location, conversation_id):
    """Delete a durable conversation by id (cleans up the stateful path)."""
    tool = "delete_conversation"
    try:
        name = f"{_parent(project_id, location)}/conversations/{conversation_id}"
        _delete(f"{_BASE_V1}/{name}")
        return _ok(tool, {"name": name},
                   [f"Deleted conversation '{conversation_id}'."])
    except requests.exceptions.HTTPError as e:
        detail = e.response.text if e.response is not None else str(e)
        return _err(tool, f"delete_conversation HTTP error: {detail}")
    except Exception as e:
        return _err(tool, f"delete_conversation failed: {e}")


def _inner_messages(list_messages_result):
    """Unwrap StorageMessage dict -> inner message dict, sorted oldest-first.

    REST list_messages returns [{messageId, message}, ...] newest-first; sort by
    the inner message timestamp ascending so turns reconstruct in ask order.
    """
    inner = [sm.get("message", sm)
             for sm in list_messages_result["results"]["messages"]]
    inner.sort(key=lambda m: m.get("timestamp") or "")
    return inner


def get_conversation_turns(conversation_name, filter_str=None, page_size=None):
    """Reconstruct a stateful conversation into {prompt, response, timestamp}
    turns — the NATIVE trace-retrieval path (no ADK). Mirrors ca_sdk.

    Each userMessage opens a turn; the systemMessages that follow are parsed (via
    parse_stream) into that turn's final answer/thoughts/followups/data/SQL. The
    inner message dicts already carry a 'systemMessage' key, so parse_stream
    consumes them directly.
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
            if "userMessage" in m:
                _flush()
                current = {"prompt": m["userMessage"].get("text"),
                           "timestamp": m.get("timestamp")}
                sys_batch = []
            elif "systemMessage" in m and current is not None:
                sys_batch.append(m)
        _flush()
        return _ok(tool, {"turns": turns, "count": len(turns)},
                   [f"Reconstructed {len(turns)} turn(s)."])
    except Exception as e:
        return _err(tool, f"get_conversation_turns failed: {e}")


# ---------------------------------------------------------------------------
# ca-context-builder : assemble context dicts from primitives
# Returns plain JSON dicts (camelCase) usable as BOTH published_context (create
# agent) and inline_context (chat). Mirrors ca_sdk builders.
#
# NOTE (see ca_sdk for the verified v0.3.0 caveats): glossary_terms is a
# structured field; example queries have no parameters; UDFs unsupported.
# ---------------------------------------------------------------------------

RECOMMENDED_TABLE_THRESHOLD = 20


def _parse_table(t):
    if isinstance(t, str):
        parts = t.split(".")
        if len(parts) != 3:
            raise ValueError(f"table string must be 'project.dataset.table', got {t!r}")
        return {"project_id": parts[0], "dataset_id": parts[1], "table_id": parts[2]}
    return {"project_id": t["project_id"], "dataset_id": t["dataset_id"],
            "table_id": t["table_id"], "schema_context": t.get("schema_context")}


def build_table_references(tables):
    """Build a datasourceReferences dict from a list of tables (see ca_sdk)."""
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
            ref = {"projectId": info["project_id"],
                   "datasetId": info["dataset_id"],
                   "tableId": info["table_id"]}
            sc = info.get("schema_context")
            if sc:
                schema = {}
                if sc.get("description"):
                    schema["description"] = sc["description"]
                if sc.get("synonyms"):
                    schema["synonyms"] = sc["synonyms"]
                if sc.get("tags"):
                    schema["tags"] = sc["tags"]
                if sc.get("fields"):
                    schema["fields"] = []
                    for col in sc["fields"]:
                        f = {"name": col["name"]}
                        if col.get("description"):
                            f["description"] = col["description"]
                        if col.get("synonyms"):
                            f["synonyms"] = col["synonyms"]
                        if col.get("tags"):
                            f["tags"] = col["tags"]
                        schema["fields"].append(f)
                if schema:
                    ref["schema"] = schema
            refs.append(ref)

        datasource = {"bq": {"tableReferences": refs}}
        return _ok(tool, {"datasource_references": datasource,
                          "table_count": len(refs)}, [note])
    except Exception as e:
        return _err(tool, f"build_table_references failed: {e}")


def build_glossary_terms(terms):
    """Build a list of glossaryTerm dicts from [{display_name, description}]."""
    tool = "build_glossary_terms"
    try:
        out = []
        for t in terms:
            gt = {"displayName": t["display_name"]}
            if t.get("description"):
                gt["description"] = t["description"]
            out.append(gt)
        return _ok(tool, {"glossary_terms": out, "count": len(out)},
                   [f"Built {len(out)} glossary term(s)."])
    except Exception as e:
        return _err(tool, f"build_glossary_terms failed: {e}")


def build_example_queries(pairs):
    """Build a list of exampleQuery dicts (golden queries). No parameters field."""
    tool = "build_example_queries"
    try:
        out = [{"naturalLanguageQuestion": p["natural_language_question"],
                "sqlQuery": p["sql_query"]} for p in pairs]
        return _ok(tool, {"example_queries": out, "count": len(out)},
                   [f"Built {len(out)} example query(ies)."])
    except Exception as e:
        return _err(tool, f"build_example_queries failed: {e}")


def build_context(system_instruction, datasource_references,
                  example_queries=None, glossary_terms=None,
                  enable_python=True, max_billed_bytes=None):
    """Assemble a context dict from primitives (camelCase JSON).

    Usable as published_context (create_data_agent) or inline_context (chat).
    """
    tool = "build_context"
    try:
        options = {"analysis": {"python": {"enabled": bool(enable_python)}}}
        if max_billed_bytes is not None:
            options["datasource"] = {"bigQueryMaxBilledBytes": str(int(max_billed_bytes))}

        context = {
            "systemInstruction": system_instruction,
            "datasourceReferences": datasource_references,
            "options": options,
        }
        if example_queries:
            context["exampleQueries"] = example_queries
        if glossary_terms:
            context["glossaryTerms"] = glossary_terms

        return _ok(tool, {"context": context},
                   ["Built context dict (systemInstruction + datasources"
                    + (", exampleQueries" if example_queries else "")
                    + (", glossaryTerms" if glossary_terms else "") + ")."])
    except Exception as e:
        return _err(tool, f"build_context failed: {e}")
