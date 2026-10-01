import app as app_module
from blockchain import BlockChain

from conftest import post_tx


def get_chain(client):
    return client.get("/chain").get_json()


def test_genesis_is_stable_across_requests(client):
    first = get_chain(client)["chain"][0]["hash"]
    second = get_chain(client)["chain"][0]["hash"]
    assert first == second


def test_new_transaction_goes_to_pending(client):
    assert post_tx(client).status_code == 201
    pending = client.get("/pending_tx").get_json()
    assert len(pending) == 1
    assert pending[0]["author"] == "alice"
    assert set(pending[0]) == {"author", "content", "timestamp"}


def test_new_transaction_rejects_invalid_data(client):
    assert client.post("/new_transaction", data="not json").status_code == 400
    assert client.post("/new_transaction", json=[1, 2]).status_code == 400
    assert client.post("/new_transaction", json={"author": "a"}).status_code == 400
    assert client.post("/new_transaction", json={"author": 1, "content": "x"}).status_code == 400
    assert client.post("/new_transaction", json={"author": " ", "content": "x"}).status_code == 400


def test_submit_form_adds_pending(client):
    client.post("/submit", data={"author": "bob", "content": "hi"})
    assert len(client.get("/pending_tx").get_json()) == 1


def test_mine_persists_valid_chain(client):
    post_tx(client, content="one")
    client.post("/mine")
    post_tx(client, content="two")
    client.post("/mine")

    data = get_chain(client)
    assert data["length"] == 3
    assert all("nonce" in b for b in data["chain"][1:])
    assert client.get("/pending_tx").get_json() == []

    # Reload from the database and verify the whole chain.
    app_module.load_db()
    assert app_module.blockchain.check_chain_validity()


def test_mine_is_post_only(client):
    assert client.get("/mine").status_code == 405
    assert client.get("/reset").status_code == 405


def test_index_does_not_mutate_chain(client):
    post_tx(client)
    client.post("/mine")
    page = client.get("/")
    assert page.status_code == 200
    assert b"hello" in page.data

    tx = get_chain(client)["chain"][1]["transactions"][0]
    assert set(tx) == {"author", "content", "timestamp"}


def test_chain_reflects_reset(client):
    post_tx(client)
    client.post("/mine")
    assert client.post("/reset").status_code == 302
    assert get_chain(client)["length"] == 1


def test_reset_requires_token_when_configured(client):
    app_module.app.config["RESET_TOKEN"] = "s3cret"
    assert client.post("/reset").status_code == 403
    assert client.post("/reset", data={"token": "wrong"}).status_code == 403
    assert client.post("/reset", data={"token": "s3cret"}).status_code == 302
    assert client.post("/reset", headers={"X-Reset-Token": "s3cret"}).status_code == 302


def test_reset_disabled_without_token_in_production(client):
    app_module.app.config["TESTING"] = False
    assert client.post("/reset").status_code == 403


def _next_block(client):
    last = get_chain(client)["chain"][-1]
    block = app_module.Block(last["index"] + 1,
                             [{"author": "peer", "content": "x", "timestamp": 1.0}],
                             2.0, last["hash"])
    proof = BlockChain.proof_of_work(block)
    payload = dict(block.__dict__)
    payload["hash"] = proof
    return payload


def test_add_block_accepts_valid_external_block(client):
    payload = _next_block(client)
    assert client.post("/add_block", json=payload).status_code == 201
    assert get_chain(client)["length"] == 2

    app_module.load_db()
    assert app_module.blockchain.check_chain_validity()


def test_add_block_rejects_invalid_blocks(client):
    assert client.post("/add_block", data="nope").status_code == 400
    assert client.post("/add_block", json={"index": 1}).status_code == 400

    payload = _next_block(client)
    payload["transactions"][0]["content"] = "forged"
    assert client.post("/add_block", json=payload).status_code == 400

    payload = _next_block(client)
    payload["index"] = 5
    assert client.post("/add_block", json=payload).status_code == 400
    assert get_chain(client)["length"] == 1
