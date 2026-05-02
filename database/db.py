import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = Path(__file__).parent.parent / "data" / "app.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)

    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transactions'"
    ).fetchone() is not None

    if table_exists:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
        if cols and "id" not in cols:
            conn.execute("DROP TABLE transactions")
            table_exists = False

    if table_exists:
        indices = conn.execute("PRAGMA index_list(transactions)").fetchall()
        has_unique_constraint = any(idx["origin"] == "u" for idx in indices)
        if not has_unique_constraint:
            conn.execute("""
                CREATE TABLE transactions_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    date            TEXT    NOT NULL,
                    beneficiary     TEXT    NOT NULL,
                    txn_note        TEXT    NOT NULL DEFAULT '',
                    withdraw_amount REAL    NOT NULL,
                    deposit_amount  REAL    NOT NULL,
                    category        TEXT,
                    UNIQUE(date, beneficiary, txn_note, withdraw_amount, deposit_amount)
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO transactions_new
                    (id, date, beneficiary, txn_note, withdraw_amount, deposit_amount, category)
                SELECT id, date, beneficiary, COALESCE(txn_note, ''),
                       withdraw_amount, deposit_amount, category
                FROM transactions
            """)
            conn.execute("DROP TABLE transactions")
            conn.execute("ALTER TABLE transactions_new RENAME TO transactions")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            beneficiary     TEXT    NOT NULL,
            txn_note        TEXT    NOT NULL DEFAULT '',
            withdraw_amount REAL    NOT NULL,
            deposit_amount  REAL    NOT NULL,
            category        TEXT,
            UNIQUE(date, beneficiary, txn_note, withdraw_amount, deposit_amount)
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count > 0:
        conn.close()
        return

    rows = [
        ("2026-04-01", "Salary Credit",   "April salary",         0.0,      85000.00, "Income"),
        ("2026-04-02", "Big Bazaar",       "Monthly groceries",    3200.00,  0.0,      "Groceries"),
        ("2026-04-04", "Ola Cabs",         "Airport drop",         650.00,   0.0,      "Transport"),
        ("2026-04-06", "Airtel",           "Broadband bill",       999.00,   0.0,      "Bills"),
        ("2026-04-08", "Apollo Pharmacy",  "Medicines",            480.00,   0.0,      "Health"),
        ("2026-04-10", "Zomato",           "Dinner order",         720.00,   0.0,      "Food"),
        ("2026-04-14", "Netflix",          "Monthly subscription", 649.00,   0.0,      "Entertainment"),
        ("2026-04-17", "HDFC Home Loan",   "EMI debit",            22000.00, 0.0,      "Housing"),
        ("2026-04-20", "Amazon",           "Electronics purchase", 5400.00,  0.0,      "Shopping"),
        ("2026-04-23", "Cafe Coffee Day",  "Team outing",          1350.00,  0.0,      "Food"),
    ]
    conn.executemany(
        "INSERT INTO transactions (date, beneficiary, txn_note, withdraw_amount, deposit_amount, category) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def insert_transactions(rows) -> dict:
    conn = get_db()
    inserted, skipped, ids = 0, 0, []
    for r in rows:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO transactions "
            "(date, beneficiary, txn_note, withdraw_amount, deposit_amount, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (r["date"], r["beneficiary"], r["txn_note"] or "",
             r["withdraw_amount"], r["deposit_amount"], r["category"]),
        )
        if cursor.lastrowid:
            inserted += 1
            ids.append(cursor.lastrowid)
        else:
            skipped += 1
    conn.commit()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "ids": ids}


def update_transaction_category(txn_id: int, category: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE transactions SET category = ? WHERE id = ?",
        (category, txn_id),
    )
    conn.commit()
    conn.close()


def create_user(name, email, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return user
