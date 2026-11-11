"""Tests for the opt-in debug tracer (ca_common)."""

import pytest


@pytest.fixture(autouse=True)
def reset_tracer():
    import ca_common
    ca_common.clear_trace()
    was = ca_common.debug_enabled()
    yield
    ca_common.set_debug(was)
    ca_common.clear_trace()


def test_no_records_when_disabled():
    import ca_common
    ca_common.set_debug(False)

    @ca_common.trace("op_x")
    def f():
        return "y"

    assert f() == "y"
    assert ca_common.get_trace() == []


def test_records_timing_and_status_when_enabled(capsys):
    import ca_common
    ca_common.set_debug(True)

    @ca_common.trace("op_ok", backend="rest")
    def f(a):
        return {"status": "success"}

    f(1)
    recs = ca_common.get_trace()
    assert len(recs) == 1
    r = recs[0]
    assert r["op"] == "op_ok" and r["backend"] == "rest"
    assert r["status"] == "ok" and r["result_status"] == "success"
    assert "ms" in r


def test_records_errors_and_reraises():
    import ca_common
    ca_common.set_debug(True)

    @ca_common.trace("op_err")
    def boom():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        boom()
    recs = ca_common.get_trace()
    assert recs[-1]["status"] == "error" and "nope" in recs[-1]["error"]


def test_trace_id_correlates_pipeline():
    import ca_common
    ca_common.set_debug(True)
    tid = ca_common.new_trace_id()

    @ca_common.trace("step")
    def step(trace_id=None):
        return 1

    step(trace_id=tid)
    step(trace_id=tid)
    assert len(ca_common.get_trace(tid)) == 2


def test_facade_reexports_tracer():
    import ca
    for fn in ["set_debug", "debug_enabled", "get_trace", "clear_trace",
               "new_trace_id"]:
        assert hasattr(ca, fn)
