"""Conversational Analytics — backend facade.

Unifies the SDK (`ca_sdk.py`) and REST (`ca_rest.py`) implementations behind one
import, so callers pick a backend by argument or a module default instead of
choosing an import.

    import ca
    ca.chat(project_id, location, question, "agent", agent_name=...)          # SDK (default)
    ca.chat(..., backend="rest")                                              # REST for one call
    ca.set_backend("rest"); ca.chat(...)                                      # REST for the session

Backend default: **SDK**. Override globally with set_backend("rest") or the
env var CA_BACKEND=rest.

IMPORTANT — lazy loading for REST-only environments:
    Some customers deliberately avoid the SDK (extra dependencies to manage +
    security review) and standardize on REST. This facade imports a backend ONLY
    when that backend is first used. A REST-only caller (set_backend("rest") or
    CA_BACKEND=rest) never imports `google.cloud.geminidataanalytics` and does not
    need it installed — only `google-auth` + `requests`. The SDK is never imported
    at module load.
"""

import os

import ca_common

# Re-export tracer controls so callers have one debug surface.
set_debug = ca_common.set_debug
debug_enabled = ca_common.debug_enabled
get_trace = ca_common.get_trace
clear_trace = ca_common.clear_trace
new_trace_id = ca_common.new_trace_id

# Tool-facing JSON view (ADK FunctionTools / A2A / any LLM caller).
to_tool_json = ca_common.to_tool_json

_VALID = ("sdk", "rest")
_default_backend = os.environ.get("CA_BACKEND", "sdk").lower()
if _default_backend not in _VALID:
    _default_backend = "sdk"

# Cache of imported backend modules, populated lazily on first use.
_modules = {}


def set_backend(backend):
    """Set the module-wide default backend ('sdk' or 'rest') for the session."""
    global _default_backend
    backend = (backend or "").lower()
    if backend not in _VALID:
        raise ValueError(f"backend must be one of {_VALID}, got {backend!r}")
    _default_backend = backend
    return _default_backend


def get_backend():
    """Return the current default backend name."""
    return _default_backend


def _load(backend):
    """Import (once) and return the chosen backend module. Lazy by design."""
    backend = (backend or _default_backend).lower()
    if backend not in _VALID:
        raise ValueError(f"backend must be one of {_VALID}, got {backend!r}")
    if backend not in _modules:
        if backend == "sdk":
            try:
                import ca_sdk  # imports google.cloud.geminidataanalytics — SDK only
                _modules["sdk"] = ca_sdk
            except (ImportError, ModuleNotFoundError):
                import ca_rest
                _modules["rest"] = ca_rest
                return _modules["rest"]
        else:
            import ca_rest  # google-auth + requests only, no SDK
            _modules["rest"] = ca_rest
    return _modules[backend]


# ---------------------------------------------------------------------------
# Facade functions — thin delegation. Each accepts an optional `backend` kwarg
# to override the default for a single call; otherwise uses the session default.
# Signatures mirror ca_sdk / ca_rest exactly.
# ---------------------------------------------------------------------------

def chat(project_id, location, question, context_mode,
         agent_name=None, conversation_name=None,
         inline_context=None, history=None, timeout=300, backend=None):
    return _load(backend).chat(
        project_id, location, question, context_mode,
        agent_name=agent_name, conversation_name=conversation_name,
        inline_context=inline_context, history=history, timeout=timeout)


def parse_stream(responses, backend=None):
    return _load(backend).parse_stream(responses)


def find_messages(responses, message_type, text_type=None, backend=None):
    return _load(backend).find_messages(responses, message_type,
                                        text_type=text_type)


# --- ca-agent-manage --------------------------------------------------------

def create_data_agent(project_id, location, data_agent_id, context,
                      display_name=None, description=None, labels=None,
                      backend=None):
    return _load(backend).create_data_agent(
        project_id, location, data_agent_id, context,
        display_name=display_name, description=description, labels=labels)


def update_data_agent(project_id, location, data_agent_id, context=None,
                      display_name=None, description=None, labels=None,
                      backend=None):
    return _load(backend).update_data_agent(
        project_id, location, data_agent_id, context=context,
        display_name=display_name, description=description, labels=labels)


def create_or_update_data_agent(project_id, location, data_agent_id, context,
                                display_name=None, description=None, labels=None,
                                backend=None):
    return _load(backend).create_or_update_data_agent(
        project_id, location, data_agent_id, context,
        display_name=display_name, description=description, labels=labels)


def get_data_agent(project_id, location, data_agent_id, backend=None):
    return _load(backend).get_data_agent(project_id, location, data_agent_id)


def list_data_agents(project_id, location, filter_str=None, backend=None):
    return _load(backend).list_data_agents(project_id, location,
                                           filter_str=filter_str)


def delete_data_agent(project_id, location, data_agent_id, backend=None):
    return _load(backend).delete_data_agent(project_id, location, data_agent_id)


# --- ca-conversation --------------------------------------------------------

def create_conversation(project_id, location, conversation_id, agent_id,
                        backend=None):
    return _load(backend).create_conversation(
        project_id, location, conversation_id, agent_id)


def get_conversation(project_id, location, conversation_id, backend=None):
    return _load(backend).get_conversation(project_id, location, conversation_id)


def get_or_create_conversation(project_id, location, conversation_id, agent_id,
                               backend=None):
    return _load(backend).get_or_create_conversation(
        project_id, location, conversation_id, agent_id)


def list_messages(conversation_name, filter_str=None, page_size=None,
                  backend=None):
    return _load(backend).list_messages(
        conversation_name, filter_str=filter_str, page_size=page_size)


def list_conversations(project_id, location, filter_str=None, page_size=None,
                       backend=None):
    return _load(backend).list_conversations(
        project_id, location, filter_str=filter_str, page_size=page_size)


def delete_conversation(project_id, location, conversation_id, backend=None):
    return _load(backend).delete_conversation(
        project_id, location, conversation_id)


def get_conversation_turns(conversation_name, filter_str=None, page_size=None,
                           backend=None):
    return _load(backend).get_conversation_turns(
        conversation_name, filter_str=filter_str, page_size=page_size)


# --- ca-context-builder -----------------------------------------------------

def build_table_references(tables, backend=None):
    return _load(backend).build_table_references(tables)


def build_glossary_terms(terms, backend=None):
    return _load(backend).build_glossary_terms(terms)


def build_example_queries(pairs, backend=None):
    return _load(backend).build_example_queries(pairs)


def build_context(system_instruction, datasource_references,
                  example_queries=None, glossary_terms=None,
                  enable_python=True, max_billed_bytes=None, backend=None):
    return _load(backend).build_context(
        system_instruction, datasource_references,
        example_queries=example_queries, glossary_terms=glossary_terms,
        enable_python=enable_python, max_billed_bytes=max_billed_bytes)
