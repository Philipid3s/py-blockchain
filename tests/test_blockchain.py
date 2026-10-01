from block import Block
from blockchain import BlockChain


def mined_chain(*contents):
    chain = BlockChain()
    for content in contents:
        chain.add_new_transaction({"author": "a", "content": content, "timestamp": 1.0})
        chain.mine()
    return chain


def test_genesis_block():
    chain = BlockChain()
    assert len(chain.chain) == 1
    assert chain.last_block.index == 0
    assert chain.last_block.previous_hash == "0"
    assert chain.check_chain_validity()


def test_mine_without_transactions_returns_none():
    chain = BlockChain()
    assert chain.mine() is None
    assert len(chain.chain) == 1


def test_mine_links_blocks_and_satisfies_difficulty():
    chain = mined_chain("one", "two")
    assert [b.index for b in chain.chain] == [0, 1, 2]
    assert chain.unconfirmed_transactions == []
    for previous, block in zip(chain.chain, chain.chain[1:]):
        assert block.previous_hash == previous.hash
        assert block.hash.startswith("0" * BlockChain.difficulty)
    assert chain.check_chain_validity()


def test_compute_hash_ignores_stored_hash():
    chain = mined_chain("one")
    block = chain.last_block
    assert block.compute_hash() == block.hash


def test_tampered_transaction_is_detected():
    chain = mined_chain("one", "two")
    chain.chain[1].transactions[0]["content"] = "forged"
    assert not chain.check_chain_validity()


def test_broken_link_is_detected():
    chain = mined_chain("one", "two")
    chain.chain[2].previous_hash = "00" + "f" * 62
    assert not chain.check_chain_validity()


def test_round_trip_keeps_chain_valid():
    chain = mined_chain("one", "two")
    restored = BlockChain()
    restored.chain = [Block.from_dict(dict(b.__dict__)) for b in chain.chain]
    assert restored.check_chain_validity()


def test_add_block_rejects_bad_proof_and_wrong_parent():
    chain = BlockChain()
    block = Block(1, [], 1.0, chain.last_block.hash)
    assert not chain.add_block(block, "00bad")

    orphan = Block(1, [], 1.0, "0" * 64)
    proof = BlockChain.proof_of_work(orphan)
    assert not chain.add_block(orphan, proof)


def test_add_block_accepts_valid_block():
    chain = BlockChain()
    block = Block(1, [], 1.0, chain.last_block.hash)
    proof = BlockChain.proof_of_work(block)
    assert chain.add_block(block, proof)
    assert chain.check_chain_validity()
