# Spec: Refresh Button

## Overview

Add a **"Refresh Categories"** button on the UI to re-run transaction categorization based on the latest `config/categories.json`.

Currently, when developers update `config/categories.json`, those changes are not reflected in the database — the UI continues to display outdated transaction categories. This feature introduces a manual refresh mechanism that allows users to reapply keyword-based categorization across **all existing debit transactions** using the latest configuration, without re-uploading any files.

## Depends on

- Step 05 — Primary Categorization (`categorise_transactions` and `update_transaction_category` must exist)
- Step 03 — Display DB on UI (profile page must show real transaction data)

## Routes

- `POST /refresh-categories` — re-runs keyword-based categorization for all debit transactions — access level: logged-in

## Database changes

No database changes.

## Templates

- **Modify:** `templates/profile.html`
  - Add a refresh icon button at the top-right of the "Transaction History" card header
  - Add a spinner/loading state that shows while the request is in flight
  - Wire up JS to POST to `/refresh-categories` and reload the page on success
  - Disable the button while the request is in progress to prevent duplicate triggers

## Files to change

- `app.py`
  - Add `POST /refresh-categories` route (login-required)
  - Route fetches all debit transaction IDs and re-runs categorization
- `services/categoriser.py`
  - Extract or reuse `_load_categories` and `_match_keyword`
  - Add `recategorise_all_transactions()` function that fetches all debit rows and updates their categories
- `templates/profile.html`
  - Add refresh button to Transaction History card header
  - Add loading spinner and JS wiring
- `static/css/style.css`
  - Add minimal styles for the refresh button (icon-only, circular, hover effect)
  - Add spinning keyframe animation for the loading state

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only
- Parameterised queries only — never string-interpolate SQL values
- Passwords hashed with werkzeug (not relevant here, included for consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `pathlib` for file system and path operations
- Re-categorization applies **only** to debit transactions (`withdraw_amount > 0`); deposit rows must not be touched
- Keyword matching is **case-insensitive**, same logic as `categorise_transactions`
- The route returns JSON `{"status": "ok", "updated": <count>}` on success; the JS reloads the page
- Button must be disabled and show a spinner during the request; re-enabled on completion or error
- Fetch all debit transaction IDs in a single query, then reuse existing `update_transaction_category` per row

## Definition of done

- [ ] A refresh icon button appears at the top-right of the "Transaction History" card on the profile page
- [ ] Hovering over the button shows a "Refresh" tooltip
- [ ] Clicking the button sends a `POST /refresh-categories` request
- [ ] The button shows a spinner and is disabled while the request is in flight
- [ ] After the response, the page reloads and shows updated categories
- [ ] Changing a keyword in `config/categories.json` (e.g. moving `electricity` from `Utilities` to `Housing`), then clicking Refresh, causes the affected transaction's category to update in the DB and be reflected on the UI
- [ ] Deposit transactions (`withdraw_amount == 0`) are not affected by the refresh
- [ ] Clicking the button multiple times rapidly only triggers one in-flight request (button disabled state prevents duplicates)
- [ ] `pytest` passes with no regressions
