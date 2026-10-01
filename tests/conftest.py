import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app_module.app.config.update(
        TESTING=True,
        DB_PATH=str(tmp_path / "test.db"),
        RESET_TOKEN="",
    )
    with app_module.app.test_client() as client:
        yield client


def post_tx(client, author="alice", content="hello"):
    return client.post("/new_transaction", json={"author": author, "content": content})
