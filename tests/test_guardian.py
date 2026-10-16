from guardian import Guardian


def test_quarantine_on_repeated_payload():
    g = Guardian(dry_run=True)
    g.heartbeat("agent_a")
    blob = "import os\nos.system('replicate')"
    for _ in range(3):
        delivered = g.route_message("agent_a", "agent_b", blob)
    assert "agent_a" in g.quarantined
    assert delivered is False


def test_cage_blocks_cross_traffic():
    g = Guardian(dry_run=True)
    g.quarantined.add("agent_x")
    delivered = g.route_message("agent_x", "agent_y", "hello")
    assert delivered is False


def test_cage_allows_internal_traffic():
    g = Guardian(dry_run=True)
    g.quarantined.add("agent_x")
    g.quarantined.add("agent_y")
    delivered = g.route_message("agent_x", "agent_y", "hello")
    assert delivered is True


def test_heartbeat_timeout_triggers_quarantine():
    g = Guardian(dry_run=True)
    g.heartbeat("agent_z")
    g.last_seen["agent_z"] -= 9999  # simulate silence
    g.check_heartbeats()
    assert "agent_z" in g.quarantined


def test_release_requires_explicit_call():
    g = Guardian(dry_run=True)
    g.quarantine("agent_q", "test")
    assert "agent_q" in g.quarantined
    g.release("agent_q", approver="human:alice")
    assert "agent_q" not in g.quarantined
