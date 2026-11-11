"""Shared cross-cutting helpers for the conversational-analytics skill.

Dependency-light (stdlib only) so importing it never pulls the SDK — preserves
the REST-only lazy-load guarantee. Home for retry/backoff now; the debug tracer
lands here too.
"""

import functools
import itertools
import os
import sys
import time
import uuid

# Substrings that indicate a transient/retryable failure. Matched against the
# stringified exception so it works for both SDK exceptions and REST HTTP text.
_RETRYABLE = (
    "RESOURCE_EXHAUSTED",   # quota
    "429",                  # too many requests
    "503",                  # unavailable
    "500",                  # internal
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
    "Connection reset",
    "Connection aborted",
)

_MAX_ATTEMPTS = int(os.environ.get("CA_RETRY_ATTEMPTS", "5"))
_BASE_DELAY = float(os.environ.get("CA_RETRY_BASE_DELAY", "1.0"))
_MAX_DELAY = float(os.environ.get("CA_RETRY_MAX_DELAY", "60.0"))


def is_retryable(exc):
    s = str(exc)
    return any(marker in s for marker in _RETRYABLE)


def _sleep_for(attempt):
    # Exponential backoff. Deterministic (no random) so it's testable; the API's
    # own jitter + our increasing delay are enough to de-synchronize callers.
    return min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)


# ---------------------------------------------------------------------------
# Debug tracer (opt-in via CA_DEBUG=1)
# Records each traced call: trace-id, op name, backend, timing, ok/err, and
# lightweight arg/result summaries. Lets a full router->context->chat run be
# reconstructed. Dependency-light; safe to import in the REST-only path.
# ---------------------------------------------------------------------------

_DEBUG = os.environ.get("CA_DEBUG") == "1"
_trace_log = []            # in-memory ring of trace records
_seq = itertools.count(1)


def debug_enabled():
    return _DEBUG


def set_debug(on):
    """Toggle tracing at runtime (overrides the CA_DEBUG env default)."""
    global _DEBUG
    _DEBUG = bool(on)
    return _DEBUG


def get_trace(trace_id=None):
    """Return recorded trace records, optionally filtered by trace_id."""
    if trace_id is None:
        return list(_trace_log)
    return [r for r in _trace_log if r.get("trace_id") == trace_id]


def clear_trace():
    _trace_log.clear()


def new_trace_id():
    """A short id to correlate a multi-step pipeline (router->context->chat)."""
    return f"catrace-{uuid.uuid4().hex[:10]}"


def _summarize(value, limit=200):
    """A compact, safe repr for tracing (never dumps huge payloads/vectors)."""
    try:
        if isinstance(value, dict):
            return {k: _summarize(v, 80) for k, v in list(value.items())[:8]}
        if isinstance(value, (list, tuple)):
            return f"{type(value).__name__}[{len(value)}]"
        s = repr(value)
        return s if len(s) <= limit else s[:limit] + "…"
    except Exception:
        return "<unrepr>"


def trace(op, backend=None, trace_id=None):
    """Decorator: record timing + outcome of a call when debugging is enabled.

    Zero overhead when CA_DEBUG is off (returns the function unwrapped). Records
    are appended to the in-memory log and echoed to stderr.
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not _DEBUG:
                return func(*args, **kwargs)
            tid = kwargs.get("trace_id") or trace_id or new_trace_id()
            rec = {"seq": next(_seq), "trace_id": tid, "op": op,
                   "backend": backend, "args": _summarize(args),
                   "kwargs": _summarize(kwargs)}
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                rec["ms"] = round((time.time() - t0) * 1000, 1)
                rec["status"] = "ok"
                if isinstance(result, dict) and "status" in result:
                    rec["result_status"] = result.get("status")
                _trace_log.append(rec)
                print(f"[ca:{tid}] {op} {rec['ms']}ms ok", file=sys.stderr)
                return result
            except Exception as e:
                rec["ms"] = round((time.time() - t0) * 1000, 1)
                rec["status"] = "error"
                rec["error"] = _summarize(str(e))
                _trace_log.append(rec)
                print(f"[ca:{tid}] {op} {rec['ms']}ms ERROR: {e}",
                      file=sys.stderr)
                raise
        return wrapper
    return decorate


# ---------------------------------------------------------------------------
# Tool-facing JSON normalization (for ADK FunctionTools / A2A / any LLM caller)
# Code-facing results carry rich objects (Context protos, numpy arrays, raw
# Message streams). ADK tools need JSON-serializable returns the model reasons
# over. to_tool_json() keeps the useful, serializable fields and drops the rest.
# ---------------------------------------------------------------------------

# Keys whose values are rich/non-serializable and should be dropped from a
# tool-facing view (they exist for in-process code composition, not for LLMs).
_DROP_KEYS = {"context", "datasource_references", "corpus", "raw", "history",
              "embeddings", "messages"}


def _jsonify(value, _depth=0):
    """Best-effort conversion to JSON-serializable primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {k: _jsonify(v, _depth + 1) for k, v in value.items()
                if k not in _DROP_KEYS}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v, _depth + 1) for v in value]
    # numpy scalar/array
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return value.tolist()
        except Exception:
            pass
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)  # last resort: a readable repr


def to_tool_json(result):
    """Return a JSON-serializable view of a house-standard result dict.

    Suitable as an ADK FunctionTool / A2A return value: keeps status, messages,
    and the serializable parts of results (table lists, rationale, answer text,
    counts, names) while dropping rich objects (Context protos, numpy arrays,
    raw streams). Idempotent and safe on any of the skill's return dicts.
    """
    if not isinstance(result, dict):
        return _jsonify(result)
    out = {"status": result.get("status"),
           "tool_name": result.get("tool_name"),
           "messages": result.get("messages", [])}
    results = result.get("results", {})
    if isinstance(results, dict):
        out["results"] = {k: _jsonify(v) for k, v in results.items()
                          if k not in _DROP_KEYS}
        # Preserve the answer's text/data even though the raw stream is dropped.
        ans = results.get("answer")
        if isinstance(ans, dict):
            out["results"]["answer"] = {
                "text": ans.get("text"),
                "data": _jsonify(ans.get("data")),
                "generated_sql": ans.get("generated_sql"),
                "followups": ans.get("followups"),
                "has_chart": ans.get("has_chart")}
    else:
        out["results"] = _jsonify(results)
    return out


def retry(fn=None, *, attempts=None, sleep=time.sleep):
    """Retry a callable on transient errors with exponential backoff.

    Usable as @retry or @retry(attempts=3). `sleep` is injectable for tests.
    Re-raises the last exception once attempts are exhausted or the error is not
    retryable. Non-retryable errors raise immediately (no wasted waiting).
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            n = attempts or _MAX_ATTEMPTS
            last = None
            for attempt in range(n):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 - re-raised below
                    last = e
                    if attempt == n - 1 or not is_retryable(e):
                        raise
                    sleep(_sleep_for(attempt))
            raise last  # unreachable, but explicit
        return wrapper
    return decorate(fn) if callable(fn) else decorate
