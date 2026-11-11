"""Test fixtures + linkage to the skill's code (single source of truth).

Inserts the skill's scripts/ dir on sys.path so tests import the CURRENT
ca_sdk / ca_rest / ca modules directly — never a copy. This mirrors
the skill's own documented import pattern.
"""

import os
import sys
import uuid

import pytest

# tests/ live inside the skill: ../scripts holds the code. Skill is portable, so
# resolve relative to this file (not any repo path).
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.abspath(os.path.join(_HERE, ".."))
_SCRIPTS = os.path.join(_SKILL, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.live tests unless CA_LIVE_TESTS=1 is set."""
    if os.environ.get("CA_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="live test; set CA_LIVE_TESTS=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def project_id():
    pid = os.environ.get("CA_TEST_PROJECT")
    if not pid:
        import google.auth
        _, pid = google.auth.default()
    return pid


@pytest.fixture(scope="session")
def location():
    return os.environ.get("CA_TEST_LOCATION", "global")


@pytest.fixture
def ca_resources():
    """Track created CA resources and delete ONLY those at teardown.

    SAFETY: never a broad sweep. Each test registers the exact ids it creates;
    teardown deletes only those. Anything pre-existing is never touched.
    """
    import ca_sdk
    created = {"agents": [], "conversations": []}

    def unique(prefix):
        name = f"catest-{prefix}-{uuid.uuid4().hex[:8]}"
        return name

    created["unique"] = unique
    yield created

    # Teardown: delete only what this test created, best-effort, isolated.
    for conv in created["conversations"]:
        try:
            ca_sdk.geminidataanalytics.DataChatServiceClient().delete_conversation(
                name=conv)
        except Exception:
            pass
    for pid, loc, agent_id in created["agents"]:
        try:
            ca_sdk.delete_data_agent(pid, loc, agent_id)
        except Exception:
            pass
