# Spec: Duplicate Uploads Fix

## Overview

Currently the application allows the same Excel file (or any file containing overlapping transactions) to be uploaded multiple times. Each upload silently inserts every row again, doubling balances and inflating all dashboard totals. This step adds a DB-level uniqueness constraint on the `transactions` table so that exact and partial duplicates are silently skipped on insert, and the user is told how many rows were imported versus how many were ignored.

## Depends on

- Step 02 (Excel Parsing) — `services/excel_parser.py` and the `/upload` route must already exist.
- Step 09 (XLS Support) — both `.xls` and `.xlsx` paths feed into `insert_transactions()`; both must be deduplicated.

## Routes

No new routes.  
The existing `POST /upload` route is modified to surface a richer flash message.

## Database changes

- Add a `UNIQUE` constraint on `(date, beneficiary, txn_note, withdraw_amount, deposit_amount)` to the `transactions` table.
- Because SQLite does not support `ALTER TABLE ADD CONSTRAINT`, `init_db()` must perform a migration:
  1. Create `transactions_new` with the new constraint.
  2. `INSERT OR IGNORE INTO transactions_new SELECT … FROM transactions` to deduplicate existing rows.
  3. `DROP TABLE transactions`.
  4. `ALTER TABLE transactions_new RENAME TO transactions`.
- The migration must be idempotent — guard it by checking whether the unique index already exists via `PRAGMA index_list(transactions)` before running.

## Templates

No new templates.  
- **Modify:** `templates/profile.html` — no template change needed; the richer flash message is generated in `app.py`.

## Files to change

- `database/db.py`
  - `init_db()` — add migration logic to add the unique constraint on existing installs.
  - `insert_transactions()` — switch to `INSERT OR IGNORE`, count actually-inserted rows, return a `dict` with `inserted` and `skipped` counts instead of a plain list of ids.
- `app.py`
  - `/upload` route — consume the new return value from `insert_transactions()` and show a flash message that reports both imported and skipped counts.

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only.
- Passwords hashed with werkzeug.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Use `INSERT OR IGNORE` — do **not** use `INSERT OR REPLACE`, which deletes and re-inserts rows, destroying existing `category` assignments.
- For `INSERT OR IGNORE`, a skipped row sets `cursor.lastrowid` to `0`. Use this to distinguish inserted rows from skipped ones.
- The migration in `init_db()` must not run if the unique index already exists. Check `PRAGMA index_list(transactions)` and look for an index whose `origin` is `u` (unique) covering the five columns before migrating.
- If the `transactions` table is empty or doesn't exist yet, the normal `CREATE TABLE IF NOT EXISTS` path (with the constraint already included) is sufficient — no migration needed.
- After migration, the row count must be ≤ the original count (no data added, only duplicates removed).
- `insert_transactions()` signature change: return `{"inserted": int, "skipped": int}` instead of `list[int]`. Update the call site in `app.py` accordingly.

## Definition of done

- [ ] Uploading the same `.xlsx` file twice shows a flash like "0 transactions imported. 42 duplicates skipped." on the second upload.
- [ ] Uploading the same `.xls` file twice behaves identically.
- [ ] Uploading a second file that shares some rows with the first imports only the new rows and reports the correct skipped count.
- [ ] The dashboard totals and transaction list are unchanged after a duplicate upload attempt.
- [ ] An existing database without the constraint is migrated correctly on app restart: duplicate rows (if any) are removed and the unique index is present afterwards.
- [ ] A fresh database (no existing `transactions` table) starts with the constraint in place — no migration needed.
- [ ] All existing tests pass (`pytest`).
