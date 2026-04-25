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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            date        TEXT    NOT NULL,
            beneficiary TEXT    NOT NULL,
            txn_note    TEXT,
            withdraw_amount      REAL    NOT NULL,
            deposit_amount      REAL    NOT NULL,
            category    TEXT 
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


def insert_transactions(rows):
    conn = get_db()
    conn.executemany(
        "INSERT INTO transactions "
        "(date, beneficiary, txn_note, withdraw_amount, deposit_amount, category) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(r["date"], r["beneficiary"], r["txn_note"],
          r["withdraw_amount"], r["deposit_amount"], r["category"])
         for r in rows],
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
