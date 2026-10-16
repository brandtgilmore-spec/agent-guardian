"""
guardian.py — a pattern-based supervisor for multi-agent systems.

WHAT THIS IS
    A small, boring, deterministic watchdog. It does not judge intent or
    "understand" whether an agent is malicious. It watches for concrete,
    pre-defined signals (missed heartbeats, repeated identical payloads,
    limit violations) and reacts the same way every time. Deterministic
    behavior is what makes it auditable and trustworthy.

WHAT THIS IS NOT
    - Not a legal or moral judge of agent behavior.
    - Not a tool for attributing real-world identity to an actor.
    - Not a guarantee of safety — it is one layer. Least-privilege
      credentials, network isolation, and human review of flagged
      events still do the real work.

Setup (once), if using the Docker cage:
    docker network create agent_main
    docker network create --internal agent_cage   # --internal = no route out

Run with dry_run=True until you've read through what it does.
"""
import hashlib
import json
import re
import subprocess
import time
from collections import defaultdict

MAIN_NET = "agent_main"
CAGE_NET = "agent_cage"
HEARTBEAT_TIMEOUT = 15        # seconds of silence before quarantine
REPLICATION_THRESHOLD = 3     # same payload sent this many times -> quarantine
LOG_PATH = "guardian_audit.jsonl"

CODE_HINTS = re.compile(r"(import |def |class |exec\(|eval\(|subprocess|base64|os\.system)")


class AuditLog:
    """Append-only, hash-chained log. Each line commits to the previous
    one, so an edited or deleted line breaks the chain and is detectable
    by anyone replaying the log — including you.

    Optionally checkpointed to a blockchain: see checkpoint().
    """

    def __init__(self, path=LOG_PATH):
        self.path, self.prev = path, "genesis"

    def write(self, event, **data):
        rec = {"t": time.time(), "event": event, "prev": self.prev, **data}
        line = json.dumps(rec, sort_keys=True)
        self.prev = hashlib.sha256(line.encode()).hexdigest()
        with open(self.path, "a") as f:
            f.write(line + "\n")
        return self.prev

    def checkpoint(self, publisher=None):
        """Publish the current chain tip somewhere external and tamper-evident.

        `publisher` is any callable taking the hash string and doing something
        with it — e.g. writing it into a testnet transaction's memo field.
        Keeping this pluggable means you aren't forced to pay gas or depend
        on a particular chain just to use the guardian. See examples/
        for a sample testnet publisher.
        """
        if publisher:
            publisher(self.prev)
        self.write("checkpoint", chain_tip=self.prev)


class Guardian:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.log = AuditLog()
        self.last_seen = {}
        self.quarantined = set()
        self.blob_counts = defaultdict(int)   # (sender, blob_hash) -> times sent

    # ---- inputs -------------------------------------------------------
    def heartbeat(self, agent_id):
        self.last_seen[agent_id] = time.time()

    def route_message(self, sender, recipient, payload: str) -> bool:
        """Every inter-agent message should be passed through here.
        Returns True if delivered, False if blocked.
        """
        # The cage: quarantined agents may only reach other quarantined agents.
        if (sender in self.quarantined) != (recipient in self.quarantined):
            self.log.write("blocked_cross_cage", sender=sender, recipient=recipient)
            return False

        if sender not in self.quarantined and CODE_HINTS.search(payload):
            h = hashlib.sha256(payload.encode()).hexdigest()[:16]
            self.blob_counts[(sender, h)] += 1
            n = self.blob_counts[(sender, h)]
            self.log.write("code_in_message", sender=sender, recipient=recipient, blob=h, count=n)
            if n >= REPLICATION_THRESHOLD:
                self.quarantine(sender, f"replicating payload {h} x{n}")
                return False
        return True

    # ---- checks ---------------------------------------------------------
    def check_heartbeats(self):
        now = time.time()
        for agent, seen in list(self.last_seen.items()):
            if agent not in self.quarantined and now - seen > HEARTBEAT_TIMEOUT:
                self.quarantine(agent, "missed heartbeat")

    # ---- actions --------------------------------------------------------
    def quarantine(self, agent_id, reason):
        """Contain, don't destroy. Quarantine is reversible; a human decides
        whether it should be permanent."""
        if agent_id in self.quarantined:
            return
        self.quarantined.add(agent_id)
        self.log.write("quarantine", agent=agent_id, reason=reason)
        self._revoke_exchange_access(agent_id)
        self._move_to_cage(agent_id)

    def release(self, agent_id, approver):
        """Humans only. The guardian never calls this on its own."""
        self.quarantined.discard(agent_id)
        self.log.write("release", agent=agent_id, approver=approver)
        self._run(["docker", "network", "disconnect", CAGE_NET, agent_id])
        self._run(["docker", "network", "connect", MAIN_NET, agent_id])

    def _revoke_exchange_access(self, agent_id):
        # Hook this up to your exchange: cancel open orders, disable the
        # agent's scoped API key. Deliberately left unimplemented here
        # since it's exchange-specific.
        self.log.write("todo_revoke_keys_and_cancel_orders", agent=agent_id)

    def _move_to_cage(self, agent_id):
        self._run(["docker", "network", "disconnect", MAIN_NET, agent_id])
        self._run(["docker", "network", "connect", CAGE_NET, agent_id])

    def _run(self, cmd):
        self.log.write("exec", cmd=cmd, dry_run=self.dry_run)
        if not self.dry_run:
            subprocess.run(cmd, check=False)
