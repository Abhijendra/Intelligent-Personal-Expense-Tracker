# Spec: Miscellaneous Category

## Overview

Display **uncategorized withdrawal transactions** as a **"Miscellaneous"** category in the bar chart on the Profile page. Currently, withdrawal transactions with `category = NULL` are excluded from the bar chart, leading to incomplete visibility of total spending. This feature groups those transactions under a "Miscellaneous" label and appends them at the bottom of the chart — after all categorized entries — so users can see their full spend picture. "Miscellaneous" only appears when uncategorized withdrawals actually exist.

## Depends on

- Step 03 — Display DB on UI (profile page and category breakdown exist)
- Step 04 — Date Range Filter (categories respect the active date filter)
- Step 07 — Show All Categories (backend returns full sorted dataset; toggle between top-5 and all views)

## Routes

No new routes. The existing `GET /profile` route is modified to include uncategorized withdrawals.

## Database changes

No database changes. The `transactions` table already stores NULL in the `category` column for uncategorized rows.

## Templates

- **Modify:** `templates/profile.html`
  - No structural changes required; the "Miscellaneous" entry arrives in the existing `categories` list with a flag so the template can apply a distinct neutral color class.

## Files to change

- `app.py`
  - Rewrite the `cat_rows` query to use `COALESCE(category, 'Miscellaneous')` grouped by that expression, filtering only `withdraw_amount > 0` (debit transactions).
  - After fetching `cat_rows`, separate the "Miscellaneous" row (if present) from the rest, sort the rest descending by total, then append "Miscellaneous" at the end — regardless of its amount.
  - Keep `cat_where` (used for `top_category`) unchanged so "Miscellaneous" never appears as the top-spending category in the stats card.
  - Add a `"is_misc": True/False` flag to each entry in the `categories` list passed to the template.
- `templates/profile.html`
  - Apply a distinct CSS class (e.g. `bar-misc`) to bars where `category.is_misc` is true, so the bar renders in a neutral colour.
- `static/css/style.css`
  - Add `.bar-misc` colour rule using a CSS variable (e.g. `--color-misc`) defined at `:root`.

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only
- Passwords hashed with werkzeug (unchanged)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- The `top_category` stat must continue to exclude NULL/uncategorized rows; do not change `cat_where`
- "Miscellaneous" must always be the **last** entry in the `categories` list, regardless of its total amount
- "Miscellaneous" must **not** appear if there are zero uncategorized withdrawals (no empty-bar edge case)
- Both the top-5 view and the "show all categories" view (from step 07) must include "Miscellaneous" when it exists; the client-side toggle logic must treat it as just another entry

## Definition of done

- [ ] `/profile` loads and "Miscellaneous" bar appears at the bottom of the chart when uncategorized withdrawals exist
- [ ] "Miscellaneous" bar is absent when every withdrawal transaction has a non-null category
- [ ] "Miscellaneous" bar is always the last bar, even if its amount is larger than other categories
- [ ] The "Miscellaneous" bar uses a visually distinct neutral colour (e.g. grey) defined via a CSS variable
- [ ] The "Top Category" stat card never shows "Miscellaneous"
- [ ] In top-5 view, if "Miscellaneous" is within the top 5 by amount it still appears last (position is forced)
- [ ] In "show all categories" view, "Miscellaneous" appears last after all categorized bars
- [ ] Date-range filter still works correctly — "Miscellaneous" aggregation respects the active date range
- [ ] Deposit transactions (rows with `withdraw_amount = 0`) are excluded from the Miscellaneous aggregation
- [ ] No console errors on page load or category toggle
