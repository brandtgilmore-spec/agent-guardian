"""
Publish the guardian's audit-log hash to Base Sepolia (a free testnet).

This writes a zero-value transaction to yourself with the hash in the
`data` field. The transaction itself is the proof: anyone can look up
its timestamp and data on a block explorer forever. No smart contract
needed for this.

SETUP
    pip install web3
    1. Get a free RPC URL: https://docs.base.org/base-chain/quickstart/connecting-to-base
       (or use a public one like https://sepolia.base.org)
    2. Create a throwaway wallet (MetaMask -> new account). Never reuse
       a wallet that holds real funds for this.
    3. Fund it with free Base Sepolia test ETH from a faucet, e.g.
       https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
    4. Put the private key in an environment variable, never in code:
           export GUARDIAN_TESTNET_KEY="0x..."
    5. export GUARDIAN_RPC_URL="https://sepolia.base.org"

USAGE
    from guardian import Guardian
    from examples.base_sepolia_checkpoint import publish_to_base_sepolia

    g = Guardian(dry_run=True)
    ...
    g.log.checkpoint(publisher=publish_to_base_sepolia)
"""
import os


def publish_to_base_sepolia(chain_tip_hash: str) -> str:
    """Writes chain_tip_hash to a Base Sepolia transaction's data field.
    Returns the transaction hash (your proof), or raises if misconfigured.
    """
    from web3 import Web3  # imported lazily so this file doesn't require
                            # web3 to be installed unless you actually use it

    rpc_url = os.environ.get("GUARDIAN_RPC_URL", "https://sepolia.base.org")
    private_key = os.environ.get("GUARDIAN_TESTNET_KEY")
    if not private_key:
        raise RuntimeError(
            "Set GUARDIAN_TESTNET_KEY to a TESTNET-ONLY private key. "
            "Never put a real key in code or commit it to git."
        )

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = w3.eth.account.from_key(private_key)

    tx = {
        "from": acct.address,
        "to": acct.address,                       # self-send; data is the point
        "value": 0,
        "data": "0x" + chain_tip_hash.encode().hex(),
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 30000,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "chainId": w3.eth.chain_id,
        "type": 2,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()


if __name__ == "__main__":
    # Quick manual test: python examples/base_sepolia_checkpoint.py <hash>
    import sys
    h = sys.argv[1] if len(sys.argv) > 1 else "test" * 16
    print("tx:", publish_to_base_sepolia(h))
