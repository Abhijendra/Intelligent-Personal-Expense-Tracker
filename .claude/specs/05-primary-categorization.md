# Spec: Primary Categorization

## Overview

Implement keyword-based transaction categorization using `config/categories.json`.

Currently, all transactions are stored with `category = NULL` and displayed as "Uncategorised" on the profile page. This feature introduces the **primary categorization method**: after an Excel file is uploaded and transactions are stored, each debit (withdrawal) transaction is matched against the keyword lists in `categories.json`. The match is attempted first on `txn_note`, then on `beneficiary`. Credit (deposit) transactions are left uncategorized intentionally. Matched transactions are updated in the database with their inferred category.

## Depends on

- Step 02 — Excel Parsing (`excel_parser.py` must parse and insert transactions)
- Step 03 — Display DB on UI (profile page must show real transaction data)

## Routes

No new routes.

## Database changes

Add `id INTEGER PRIMARY KEY AUTOINCREMENT` to the `transactions` table.

The table currently has no primary key, which makes it impossible to reliably update individual rows after insert. Adding `id` is required for the post-insert UPDATE flow described below.

**Migration:** Drop and recreate the table in `init_db()`. Since this is a dev/demo app with seeded data, no migration script is needed — the table is recreated on next startup. Note that existing data in `spendly.db` will be lost and must be re-imported.

Updated schema:
```sql
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    beneficiary     TEXT    NOT NULL,
    txn_note        TEXT,
    withdraw_amount REAL    NOT NULL,
    deposit_amount  REAL    NOT NULL,
    category        TEXT
)
```

## Templates

No template changes.

## Files to change

- `database/db.py`
  - Update `init_db()` to add `id` column to transactions schema
  - Add `update_transaction_category(txn_id, category)` helper function
- `services/categoriser.py`
  - Implement `categorise_transactions(txn_ids)` — categorizes only the newly inserted transactions
- `app.py`
  - In the `/upload` route: after `insert_transactions(rows)`, retrieve the IDs of newly inserted rows and pass them to `categorise_transactions()`
  - Import `categorise_transactions` from `services/categoriser`

## Files to create

No new files.

## New dependencies

No new dependencies.

## Implementation notes

### Processing flow

```
POST /upload
  → parse_file(dest)                  # returns rows with category=None
  → insert_transactions(rows)         # stores rows; returns list of new row IDs
  → categorise_transactions(txn_ids)  # updates category for each debit row
  → redirect to /profile
```

### `insert_transactions` return value

Modify `insert_transactions(rows)` in `database/db.py` to return the list of `lastrowid` values for each inserted row, so the upload route can pass them to the categoriser.

```python
def insert_transactions(rows) -> list[int]:
    conn = get_db()
    ids = []
    for r in rows:
        cursor = conn.execute(
            "INSERT INTO transactions (date, beneficiary, txn_note, withdraw_amount, deposit_amount, category) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (r["date"], r["beneficiary"], r["txn_note"],
             r["withdraw_amount"], r["deposit_amount"], r["category"])
        )
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids
```

### `categorise_transactions` in `services/categoriser.py`

```python
import json
from pathlib import Path
from database.db import get_db, update_transaction_category

CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "categories.json"


def _load_categories() -> dict[str, list[str]]:
    with open(CATEGORIES_PATH) as f:
        return json.load(f)


def _match_keyword(text: str, categories: dict[str, list[str]]) -> str | None:
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return category
    return None


def categorise_transactions(txn_ids: list[int]) -> None:
    if not txn_ids:
        return
    categories = _load_categories()
    conn = get_db()
    placeholders = ",".join("?" * len(txn_ids))
    rows = conn.execute(
        f"SELECT id, txn_note, beneficiary, withdraw_amount "
        f"FROM transactions WHERE id IN ({placeholders})",
        txn_ids,
    ).fetchall()
    conn.close()

    for row in rows:
        if row["withdraw_amount"] == 0.0:  # skip credits
            continue
        category = _match_keyword(row["txn_note"], categories) \
                or _match_keyword(row["beneficiary"], categories)
        if category:
            update_transaction_category(row["id"], category)
```

### `update_transaction_category` in `database/db.py`

```python
def update_transaction_category(txn_id: int, category: str) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE transactions SET category = ? WHERE id = ?",
        (category, txn_id),
    )
    conn.commit()
    conn.close()
```

### Upload route in `app.py`

```python
from services.categoriser import categorise_transactions

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("statement")
    if not file or not file.filename.endswith(".xlsx"):
        flash("Please upload a valid .xlsx file.", "error")
        return redirect(url_for("profile"))
    dest = UPLOAD_DIR / file.filename
    file.save(dest)
    rows = parse_file(dest)
    txn_ids = insert_transactions(rows)
    categorise_transactions(txn_ids)
    flash(f"{len(rows)} transactions imported successfully.", "success")
    return redirect(url_for("profile"))
```

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only
- Parameterised queries only — never string-interpolate SQL values
- Passwords hashed with werkzeug (not relevant here, included for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `pathlib` for file system and path operations
- Categorization applies **only** to debit transactions (`withdraw_amount > 0`); deposit rows must not be categorized
- Keyword matching is **case-insensitive** (`text.lower()` vs `keyword.lower()`)
- Keyword match on `txn_note` takes priority over `beneficiary`
- If neither field matches, the transaction remains `NULL` (not "Uncategorised") — the UI handles display
- LLM fallback is **out of scope** for this step

## Definition of done

- [ ] Uploading an Excel file with a transaction whose `txn_note` contains a known keyword (e.g. `tetanus`) results in that transaction being categorized as `health` in the DB
- [ ] Uploading a transaction with an empty `txn_note` but a known `beneficiary` keyword (e.g. `paytmqr1m53n1bw1s`) results in it being categorized as `food`
- [ ] Uploading a transaction whose `txn_note` matches a keyword takes priority over the `beneficiary` (txn_note match wins)
- [ ] Deposit transactions (`deposit_amount > 0`, `withdraw_amount == 0`) are **not** categorized — their `category` remains `NULL`
- [ ] Transactions with no matching keywords in either field remain `NULL` in the DB (displayed as "Uncategorised" on the UI)
- [ ] The profile page shows correct category labels for matched transactions after upload
- [ ] Keyword matching is case-insensitive (e.g. `ZOMATO` matches the `food` keyword `zomato`)
- [ ] `pytest` passes with no regressions
