# Spec: Date Range Filter

## Overview

Add a **date range filter** to the profile page UI.

Currently, users cannot filter transactions on the UI. All summaries (total spent, transaction count, top category) are calculated using all records from the `transactions` table. This limits user control and flexibility.

Introduce a date range filtering feature on the profile page, allowing users to filter transactions within a selected date range and view updated summaries based only on the filtered data.

## Depends on

- Step 03 — Display DB Data on UI (profile page must already display real data from the DB)

## Routes

No new routes. The existing `GET /profile` route is extended to accept optional `start_date` and `end_date` query parameters. When both are provided, all queries are scoped to that date range. Pagination (`page`) continues to work alongside the filter params.

## Database changes

No database changes. The `date` column already exists on the `transactions` table as a `TEXT` field in `YYYY-MM-DD` format, which supports direct string comparison in SQLite.

## Templates

- **Modify:** `templates/profile.html` — add a compact filter bar above the summary cards containing:
  - Start Date input (`type="date"`)
  - End Date input (`type="date"`)
  - An "Apply" button to submit the form as a GET request
  - A "Clear" link that navigates back to `/profile` without query params
  - Display the active filter range (e.g. "Showing results from 2026-01-01 to 2026-03-31") when a filter is active

## Files to change

- `app.py` — modify `profile()` to read `start_date` and `end_date` from query params and inject them into all SQL queries as WHERE clause conditions
- `templates/profile.html` — add the filter bar UI and pass `start_date`/`end_date` back into the form so inputs retain their values after submit
- `static/css/style.css` — add styles for the filter bar

## Files to create

No new files.

## New dependencies

No new dependencies.

## Implementation notes

### Query param handling in `profile()`

```python
start_date = request.args.get("start_date", "").strip()
end_date   = request.args.get("end_date", "").strip()
```

Build a reusable WHERE clause fragment:

```python
date_filter  = ""
date_params  = []
if start_date and end_date:
    date_filter = "WHERE date >= ? AND date <= ?"
    date_params = [start_date, end_date]
elif start_date:
    date_filter = "WHERE date >= ?"
    date_params = [start_date]
elif end_date:
    date_filter = "WHERE date <= ?"
    date_params = [end_date]
```

Apply `date_filter` and `date_params` consistently to:

1. **Stats query** (total_spent, transaction_count)
2. **Top category query**
3. **Pagination count query** (`SELECT COUNT(*) FROM transactions {date_filter}`)
4. **Transaction rows query** (apply filter before `ORDER BY … LIMIT … OFFSET`)
5. **Category breakdown query**

Pass `start_date` and `end_date` back to the template context so the form inputs retain their values.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only
- Parameterised queries only — never string-interpolate SQL
- Passwords hashed with werkzeug (not relevant here, included for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `pathlib` for file system and path operations
- When no filter is active, behaviour is identical to the current unfiltered profile page
- Partial filters (only start or only end date) are handled gracefully
- The filter form submits via GET so the URL remains bookmarkable/shareable

## Definition of done

- [ ] A date range filter bar is visible on the profile page above the summary cards
- [ ] Selecting a start date and end date and clicking "Apply" reloads the page with `?start_date=…&end_date=…` in the URL
- [ ] After applying a filter, the start and end date inputs retain the selected values
- [ ] `Total Spent` reflects only transactions within the selected date range
- [ ] `Transaction Count` reflects only transactions within the selected date range
- [ ] `Top Category` reflects only transactions within the selected date range
- [ ] The transaction history list shows only transactions within the selected date range, sorted by date descending
- [ ] Pagination works correctly alongside date filtering (page numbers are correct for the filtered set)
- [ ] Clicking "Clear" navigates to `/profile` with no query params and shows all transactions
- [ ] When no filter is applied, the profile page behaves identically to before this change
- [ ] An active-filter label (e.g. "Showing 2026-01-01 → 2026-03-31") is displayed when a filter is in effect
- [ ] Page works correctly when the date range returns zero transactions (shows zeros, empty lists — no server error)
