"""Tests for REST pagination (no silent truncation)."""


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_paginate_follows_next_page_token(monkeypatch):
    import ca_rest
    pages = [
        {"dataAgents": [{"name": "a1"}, {"name": "a2"}], "nextPageToken": "t1"},
        {"dataAgents": [{"name": "a3"}], "nextPageToken": "t2"},
        {"dataAgents": [{"name": "a4"}]},  # no token -> stop
    ]
    seen_tokens = []

    def fake_get(url, params=None, timeout=300):
        seen_tokens.append((params or {}).get("pageToken"))
        return _FakeResp(pages[len(seen_tokens) - 1])

    monkeypatch.setattr(ca_rest, "_get", fake_get)
    items = list(ca_rest._paginate("http://x", "dataAgents"))
    assert [i["name"] for i in items] == ["a1", "a2", "a3", "a4"]
    # first call no token, then follows t1, t2
    assert seen_tokens == [None, "t1", "t2"]


def test_list_data_agents_aggregates_all_pages(monkeypatch):
    import ca_rest
    pages = [
        {"dataAgents": [{"name": "a1", "displayName": "A1", "labels": {}}],
         "nextPageToken": "t1"},
        {"dataAgents": [{"name": "a2", "displayName": "A2", "labels": {}}]},
    ]
    calls = {"n": 0}

    def fake_get(url, params=None, timeout=300):
        r = _FakeResp(pages[calls["n"]])
        calls["n"] += 1
        return r

    monkeypatch.setattr(ca_rest, "_get", fake_get)
    r = ca_rest.list_data_agents("p", "global")
    assert r["results"]["count"] == 2
    assert calls["n"] == 2  # both pages fetched


def test_list_messages_paginates(monkeypatch):
    import ca_rest
    pages = [
        {"messages": [{"messageId": "m1"}], "nextPageToken": "t1"},
        {"messages": [{"messageId": "m2"}, {"messageId": "m3"}]},
    ]
    calls = {"n": 0}

    def fake_get(url, params=None, timeout=300):
        r = _FakeResp(pages[calls["n"]])
        calls["n"] += 1
        return r

    monkeypatch.setattr(ca_rest, "_get", fake_get)
    r = ca_rest.list_messages("projects/p/locations/global/conversations/c")
    assert r["results"]["count"] == 3


def test_list_messages_passes_filter_and_page_size(monkeypatch):
    import ca_rest
    seen = {}

    def fake_get(url, params=None, timeout=300):
        seen.update(params or {})
        return _FakeResp({"messages": [{"messageId": "m1"}]})

    monkeypatch.setattr(ca_rest, "_get", fake_get)
    r = ca_rest.list_messages("projects/p/locations/global/conversations/c",
                              filter_str="create_time>\"2026-01-01\"",
                              page_size=25)
    assert r["results"]["count"] == 1
    assert seen.get("filter") == "create_time>\"2026-01-01\""
    assert seen.get("pageSize") == 25


def test_list_conversations_paginates_and_shapes(monkeypatch):
    import ca_rest
    pages = [
        {"conversations": [
            {"name": "projects/p/locations/global/conversations/c1",
             "agents": ["projects/p/locations/global/dataAgents/a1"]}],
         "nextPageToken": "t1"},
        {"conversations": [
            {"name": "projects/p/locations/global/conversations/c2",
             "agents": ["projects/p/locations/global/dataAgents/a1"]}]},
    ]
    calls = {"n": 0}
    seen = {}

    def fake_get(url, params=None, timeout=300):
        seen.update(params or {})
        r = _FakeResp(pages[calls["n"]])
        calls["n"] += 1
        return r

    monkeypatch.setattr(ca_rest, "_get", fake_get)
    r = ca_rest.list_conversations(
        "p", "global",
        filter_str="agents:projects/p/locations/global/dataAgents/a1")
    assert r["results"]["count"] == 2
    assert calls["n"] == 2  # both pages fetched
    ids = [c["conversation_id"] for c in r["results"]["conversations"]]
    assert ids == ["c1", "c2"]
    assert r["results"]["conversations"][0]["agents"] == [
        "projects/p/locations/global/dataAgents/a1"]
    assert seen.get("filter", "").startswith("agents:")
