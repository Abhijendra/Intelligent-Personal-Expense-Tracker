# Spec: Show All Categories

## Overview

Currently the "Spending by Category" bar graph on the `/profile` page is hard-capped at the top 5 categories (via `LIMIT 5` in the SQL query). This feature adds a **"Show all categories"** checkbox above the chart that lets the user toggle between the default top-5 view and a full breakdown of every category in the current date range. All filtering happens on the frontend — the backend always returns the full sorted dataset — so the toggle is instant with no page reload. User preference is persisted in `localStorage` so the selection survives navigation and refresh.

## Depends on

- Step 03 — Display DB on UI (profile page and category breakdown exist)
- Step 04 — Date Range Filter (categories respect the active date filter)

## Routes

No new routes. The existing `GET /profile` route is modified to return all categories instead of limiting to 5.

## Database changes

No database changes.

## Templates

- **Modify:** `templates/profile.html`
  - Pass all categories to the template (backend change removes `LIMIT 5`)
  - Add a `show-all-categories` checkbox above the "Spending by Category" card header
  - Wrap the bar chart container in a horizontally-scrollable div for wide datasets
  - Add inline JS (or move to `main.js`) to filter the rendered rows and persist checkbox state to `localStorage`

## Files to change

- `app.py` — remove `LIMIT 5` from the `cat_rows` query; continue to sort `DESC` by total
- `templates/profile.html` — checkbox toggle UI + client-side show/hide logic
- `static/js/main.js` — add `initCategoryToggle()` function (called on DOMContentLoaded)
- `static/css/style.css` — add styles for checkbox, scrollable bar container, and overflow handling

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
- Filtering (top-5 vs all) must be done entirely on the frontend; do not add a new backend parameter or extra route
- Embed all category data in the rendered HTML (e.g. `data-index` attributes or a JS array); do not make an AJAX call for the toggle
- Store checkbox state in `localStorage` under the key `spendly_show_all_categories`
- The scrollable wrapper must only apply when the category count exceeds 5 (add a CSS class conditionally via JS)
- Color mapping (`.mock-bar-1` … `.mock-bar-N`) must remain consistent — do not re-index when hiding rows

## Definition of done

- [ ] `/profile` page loads with only the top 5 categories visible by default
- [ ] A "Show all categories" checkbox is visible above or near the "Spending by Category" header
- [ ] Checking the box reveals all categories sorted by total spend (descending) without a page reload
- [ ] Unchecking the box hides all but the top 5 without a page reload
- [ ] With more than 5 categories visible, the chart container scrolls horizontally (or adapts layout) without breaking the page
- [ ] Color assignment for bars is stable — the same category keeps the same color in both views
- [ ] The checkbox state is saved to `localStorage`; reloading the page restores the previous selection
- [ ] The date-range filter still works correctly in both the top-5 and all-categories views
- [ ] No console errors on load or toggle
