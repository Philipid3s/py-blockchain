from hashlib import sha256
import json


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash

    def compute_hash(self):
        # The stored hash is not part of its own input.
        content = {k: v for k, v in self.__dict__.items() if k != 'hash'}
        block_string = json.dumps(content, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data):
        """
        Rebuild a block from its serialized form. The nonce must be
        restored, otherwise the block's hash can no longer be verified.
        """
        block = cls(data['index'],
                    data['transactions'],
                    data['timestamp'],
                    data['previous_hash'])
        if 'nonce' in data:
            block.nonce = data['nonce']
        if 'hash' in data:
            block.hash = data['hash']
        return block
