from block import Block
from blockchain import BlockChain
from flask import Flask, abort, render_template, redirect, request
import datetime
import hmac
import json
import logging
import os
import sqlite3
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DB_PATH'] = os.environ.get('DB_PATH', 'blockchain.db')
# When set, /reset requires this token. When unset, /reset is only
# available in debug/testing mode.
app.config['RESET_TOKEN'] = os.environ.get('RESET_TOKEN', '')

blockchain = BlockChain()


def connect_db():
    conn = sqlite3.connect(app.config['DB_PATH'])
    conn.execute("""
        CREATE TABLE IF NOT EXISTS blockchain (
            chain TEXT,
            pending_tx TEXT
        )
    """)
    return conn


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M')


def chain_as_dict():
    chain_data = [block.__dict__ for block in blockchain.chain]
    return {"length": len(chain_data), "chain": chain_data}


def save_db():
    chain = json.dumps(chain_as_dict())
    pending_tx = json.dumps(blockchain.unconfirmed_transactions)

    conn = connect_db()
    with conn:
        count = conn.execute("SELECT COUNT(*) FROM blockchain;").fetchone()[0]
        if count > 0:
            conn.execute("UPDATE blockchain SET chain = ?, pending_tx = ?;",
                         (chain, pending_tx))
        else:
            conn.execute("INSERT INTO blockchain VALUES (?, ?);",
                         (chain, pending_tx))
    conn.close()


def load_db():
    global blockchain
    conn = connect_db()
    data = conn.execute("SELECT * FROM blockchain;").fetchone()
    conn.close()

    if data is None:
        # Persist the genesis block straight away so it stays stable
        # across requests.
        blockchain = BlockChain()
        save_db()
        return

    obj = json.loads(data[0])
    blockchain.chain = [Block.from_dict(block) for block in obj['chain']]
    blockchain.unconfirmed_transactions = json.loads(data[1])


def clear_db():
    conn = connect_db()
    with conn:
        conn.execute("DELETE FROM blockchain;")
    conn.close()


def reset_allowed():
    token = app.config['RESET_TOKEN']
    if not token:
        return app.debug or app.testing
    supplied = request.form.get('token') or request.headers.get('X-Reset-Token', '')
    return hmac.compare_digest(supplied, token)


def parse_transaction(data):
    """
    Return a clean transaction dict, or None if author/content are
    missing or not non-empty strings.
    """
    if not isinstance(data, dict):
        return None
    tx = {}
    for field in ("author", "content"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return None
        tx[field] = value.strip()
    tx["timestamp"] = time.time()
    return tx


@app.route('/')
def index():
    load_db()

    posts = []
    for block in blockchain.chain:
        for tx in block.transactions:
            # Copy so the block's own transactions are left untouched.
            posts.append({**tx, "index": block.index})
    posts.sort(key=lambda k: k['timestamp'], reverse=True)

    return render_template('index.html',
                           title='BlockChain - '
                                 'Distributed content sharing',
                           posts=posts,
                           pending_tx=len(blockchain.unconfirmed_transactions),
                           reset_enabled=bool(app.config['RESET_TOKEN']) or app.debug,
                           reset_needs_token=bool(app.config['RESET_TOKEN']),
                           readable_time=timestamp_to_string)


@app.route('/submit', methods=['POST'])
def submit_textarea():
    tx = parse_transaction(request.form)
    if tx is None:
        return redirect('/')

    load_db()
    blockchain.add_new_transaction(tx)
    save_db()

    return redirect('/')


@app.route('/chain', methods=['GET'])
def get_chain():
    load_db()
    return json.dumps(chain_as_dict()), 200, {'Content-Type': 'application/json'}


@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx = parse_transaction(request.get_json(silent=True))
    if tx is None:
        return "Invalid transaction data", 400

    load_db()
    blockchain.add_new_transaction(tx)
    save_db()

    return "Success", 201


@app.route('/mine', methods=['POST'])
def mine_unconfirmed_transactions():
    load_db()
    result = blockchain.mine()
    if result is None:
        logger.info("Nothing to mine.")
    else:
        logger.info("Block #%s is mined.", result)
        save_db()

    return redirect('/')


@app.route('/reset', methods=['POST'])
def reset_chain():
    if not reset_allowed():
        abort(403)
    clear_db()
    blockchain.reset()
    logger.info("Chain reset.")
    return redirect('/')


# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    load_db()
    return json.dumps(blockchain.unconfirmed_transactions), 200, \
        {'Content-Type': 'application/json'}


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def validate_and_add_block():
    block_data = request.get_json(silent=True)
    required = ("index", "transactions", "timestamp", "previous_hash", "nonce", "hash")
    if not isinstance(block_data, dict) or not all(k in block_data for k in required):
        return "Invalid block data", 400

    load_db()
    block = Block.from_dict(block_data)
    proof = block.hash
    del block.hash

    if block.index != blockchain.last_block.index + 1 or \
            not blockchain.add_block(block, proof):
        return "The block was discarded by the node", 400

    save_db()
    return "Block added to the chain", 201


if __name__ == '__main__':
    app.run(debug=True)
