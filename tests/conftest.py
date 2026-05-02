import sqlite3
import pytest


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            beneficiary     TEXT    NOT NULL,
            txn_note        TEXT    NOT NULL DEFAULT '',
            withdraw_amount REAL    NOT NULL,
            deposit_amount  REAL    NOT NULL,
            category        TEXT
        )
    """)
    conn.commit()
    yield conn
    conn.close()
