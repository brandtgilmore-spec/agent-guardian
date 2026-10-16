# agent-guardian

A small, deterministic supervisor for multi-agent systems. It watches for
concrete signals — missed heartbeats, an agent repeatedly sending the same
payload, limit violations — and quarantines the offending agent into an
isolated network. It does not try to judge intent, and it does not try to
identify who is behind an agent.

## Why deterministic, not "smart"

It's tempting to want the guardian to *understand* whether an agent is
behaving maliciously. That's a harder and much riskier design: a judgment-
based system can be fooled by anything that doesn't match its training, and
it makes consequential, hard-to-explain calls. This guardian instead reacts
the same way every time to the same pattern. That's what makes it auditable
and safe to give real power (killing network access, revoking keys) to.

## What it does

- **Heartbeat monitoring** — agents that go silent get quarantined.
- **Replication detection** — an agent sending the same payload repeatedly
  gets quarantined (regex-based code-pattern matching; tune to your needs).
- **The cage** — quarantined agents are moved to an isolated Docker network
  (`--internal`, no route to the outside world) and can only talk to other
  quarantined agents. Contain, don't destroy: state is preserved for review.
- **Hash-chained audit log** — every action is appended to a log where each
  line commits to the previous one, so edits are detectable.
- **Optional blockchain checkpointing** — periodically publish the log's
  hash externally for tamper-evidence beyond your own disk. Two ready-to-
  configure options, pick one or use both:
  - `examples/base_sepolia_checkpoint.py` — fast (seconds), needs a free
    testnet wallet + faucet funds. Good for frequent checkpoints.
  - `examples/opentimestamps_checkpoint.py` — free, no wallet, anchored to
    Bitcoin. Slower (hours to confirm) but the strongest immutability
    guarantee. Good for durable historical checkpoints.

  Only hashes are ever published, never payloads or code. Use testnets /
  throwaway wallets — never point real funds at this.

## What it deliberately does not do

- **It does not decide what's "nefarious."** It matches patterns you
  configure. Flagged agents should be reviewed by a human before any
  destructive or permanent action is taken.
- **It does not attribute identity.** Tracing a wallet or agent ID back to
  a real company or person is, in general, not something message logs or
  on-chain data can do on their own — that requires KYC'd intermediaries,
  subpoenas, or voluntary disclosure.
- **It is not a security boundary by itself.** The isolation comes from
  your container/network configuration, not from the Python code. Give
  each agent its own container, no Docker socket access, and scoped,
  revocable credentials. The guardian is one layer among several you need.

## Setup

```bash
docker network create agent_main
docker network create --internal agent_cage   # --internal = no route out
pip install -r requirements.txt
```

Run everything with `Guardian(dry_run=True)` first and read the audit log
it produces before pointing it at real infrastructure.

## Usage

```python
from guardian import Guardian

g = Guardian(dry_run=True)
g.heartbeat("agent_07")

# route every inter-agent message through the guardian
delivered = g.route_message("agent_07", "agent_12", payload)

# run periodically (e.g. every few seconds) in your scheduler
g.check_heartbeats()

# a human, not the guardian, decides to release
g.release("agent_07", approver="human:your_name")

# optional: checkpoint the audit log externally (see examples/)
from examples.base_sepolia_checkpoint import publish_to_base_sepolia
g.log.checkpoint(publisher=publish_to_base_sepolia)
```

## Status

Early / reference implementation. `_revoke_exchange_access` is a stub —
wire it to your exchange's API to cancel orders and disable keys on
quarantine. Replication detection is a simple regex; replace with
something more robust for production use.

## License

MIT — see LICENSE.
