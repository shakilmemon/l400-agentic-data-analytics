"""Tests for the shared retry/backoff wrapper (ca_common)."""

import pytest


def test_retries_then_succeeds():
    import ca_common
    calls = {"n": 0}
    slept = []

    @ca_common.retry(sleep=slept.append)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("RESOURCE_EXHAUSTED: quota")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3
    assert len(slept) == 2  # slept before each retry


def test_non_retryable_raises_immediately():
    import ca_common
    calls = {"n": 0}
    slept = []

    @ca_common.retry(sleep=slept.append)
    def boom():
        calls["n"] += 1
        raise ValueError("bad argument")  # not in the retryable set

    with pytest.raises(ValueError):
        boom()
    assert calls["n"] == 1
    assert slept == []  # never waited


def test_exhausts_attempts_and_reraises():
    import ca_common
    calls = {"n": 0}

    @ca_common.retry(attempts=4, sleep=lambda s: None)
    def always():
        calls["n"] += 1
        raise RuntimeError("503 UNAVAILABLE")

    with pytest.raises(RuntimeError):
        always()
    assert calls["n"] == 4


def test_backoff_is_exponential_and_capped():
    import ca_common
    d0 = ca_common._sleep_for(0)
    d1 = ca_common._sleep_for(1)
    d2 = ca_common._sleep_for(2)
    assert d1 == d0 * 2 and d2 == d0 * 4
    assert ca_common._sleep_for(100) <= ca_common._MAX_DELAY


def test_is_retryable_markers():
    import ca_common
    assert ca_common.is_retryable(RuntimeError("RESOURCE_EXHAUSTED"))
    assert ca_common.is_retryable(RuntimeError("429 Too Many Requests"))
    assert not ca_common.is_retryable(ValueError("nope"))
