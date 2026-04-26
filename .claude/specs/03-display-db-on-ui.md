# Spec: Display DB Data on UI

## Overview

Replace placeholder data on the profile page with actual data fetched from the database.

The profile page currently displays hardcoded placeholder data. This needs to be replaced with real data retrieved from the database. Update the `profile()` function in `app.py` to achieve this.

The `users` table contains only one user, whose details should be used. Statistics are computed from the `transactions` table. The 15 most recent transactions are displayed, and the 5 most used categories (by spend) are shown.

## Depends on

- Step 01 — Database initialisation (`users` and `transactions` tables must exist)
- Step 02 — Excel parsing (transactions must be importable so the profile has real data to display)

## Routes

No new routes. The existing `GET /profile` route is modified to pass real data instead of hardcoded placeholders.

## Database changes

No database changes.

## Templates

- **Modify:** `templates/profile.html` — update Jinja variables to match the new data shapes passed from the route (see Data Mapping below)

## Files to change

- `app.py` — rewrite the `profile()` function to query the DB

## Files to create

No new files.

## New dependencies

No new dependencies.

## Data mapping

### User information

Fetch the first user from the `users` table:

```python
user = {
    "name":     row["name"],
    "email":    row["email"],
    "joined":   row["created_at"],   # raw datetime string from DB
    "initials": "".join(w[0].upper() for w in row["name"].split() if w),
}
```

### Statistics

Compute from the `transactions` table:

```python
stats = {
    "total_spent":       <SUM(withdraw_amount)>,
    "transaction_count": <COUNT(*)>,
    "top_category":      <category with highest SUM(withdraw_amount), or "N/A" if no rows>,
}
```

> **Note:** The DB column is `withdraw_amount` (not `withdrawal_amount`). Match this exactly.

### Recent transactions

```python
transactions = []  # 15 rows ordered by date DESC
```

Each row passed to the template:

```python
{
    "date":        row["date"],
    "description": row["beneficiary"],
    "category":    row["category"] or "Uncategorised",
    "amount":      row["withdraw_amount"],
}
```

### Categories

```python
categories = []  # top 5 categories by total withdraw_amount
```

Each entry:

```python
{
    "name":   category,
    "amount": total_withdraw_amount,
    "pct":    int(total / overall_total * 100) if overall_total else 0,
}
```

Use `GROUP BY category ORDER BY SUM(withdraw_amount) DESC LIMIT 5`. Skip rows where `category` is empty or NULL.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only
- Parameterised queries only — never string-interpolate SQL
- Passwords hashed with werkzeug (not relevant here, included for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `pathlib` for all file system and path operations
- Handle empty database gracefully: if no user exists redirect to login; if no transactions exist, show zeros and empty lists
- `top_category` should fall back to `"N/A"` when the transactions table is empty
- Format currency amounts as plain floats — let the template handle display formatting
- All DB logic stays inside `profile()` in `app.py` (no new helper functions in `db.py` required)

## Definition of done

- [ ] Profile page loads without error when logged in
- [ ] User name, email, and joined date shown on the profile page match the `users` table (verify with `sqlite3 data/app.db "SELECT name, email, created_at FROM users LIMIT 1"`)
- [ ] User initials are derived from the full name (e.g. "John Doe" → "JD")
- [ ] `total_spent` matches `SELECT SUM(withdraw_amount) FROM transactions`
- [ ] `transaction_count` matches `SELECT COUNT(*) FROM transactions`
- [ ] `top_category` matches the category with the highest `SUM(withdraw_amount)`
- [ ] Recent transactions table shows at most 15 rows, sorted newest first
- [ ] Categories section shows at most 5 entries, sorted by total spend descending
- [ ] Profile page loads without error when the `transactions` table is empty (shows zeros and empty lists)
- [ ] No hardcoded placeholder data remains in the `profile()` function
