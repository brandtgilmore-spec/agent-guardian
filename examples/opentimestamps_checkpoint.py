"""
Publish the guardian's audit-log hash via OpenTimestamps, anchored to
Bitcoin. Free, no wallet needed, strongest immutability guarantee of any
option here. Tradeoff: confirmation takes hours (Bitcoin batches many
users' timestamps together before anchoring), so use this for durable
historical checkpoints, not real-time alerts — your local hash-chained
log already covers real-time.

SETUP
    pip install opentimestamps-client

USAGE
    from guardian import Guardian
    from examples.opentimestamps_checkpoint import publish_to_opentimestamps

    g = Guardian(dry_run=True)
    ...
    g.log.checkpoint(publisher=publish_to_opentimestamps)

    # Later (hours later), upgrade the proof once Bitcoin has confirmed it:
    #   ots upgrade checkpoints/<hash>.txt.ots
    # Verify anytime after that:
    #   ots verify checkpoints/<hash>.txt.ots
"""
import os
import subprocess

CHECKPOINT_DIR = "checkpoints"


def publish_to_opentimestamps(chain_tip_hash: str) -> str:
    """Writes the hash to a file and stamps it with OpenTimestamps.
    Returns the path to the .ots proof file.

    Requires the `ots` CLI (pip install opentimestamps-client) to be on
    your PATH. Shelling out to the CLI is simpler and more maintained
    than driving the Python library directly for this use case.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, f"{chain_tip_hash}.txt")
    with open(path, "w") as f:
        f.write(chain_tip_hash)

    result = subprocess.run(["ots", "stamp", path], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ots stamp failed: {result.stderr}")

    return path + ".ots"


if __name__ == "__main__":
    import sys
    h = sys.argv[1] if len(sys.argv) > 1 else "test" * 16
    print("proof file:", publish_to_opentimestamps(h))
