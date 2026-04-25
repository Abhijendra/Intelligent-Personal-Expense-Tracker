# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (port 5003)
source .venv/bin/activate && python app.py

# Run tests
source .venv/bin/activate && pytest

# Run a single test file
source .venv/bin/activate && pytest tests/test_foo.py

# Install dependencies
pip install -r requirements.txt
```

The app initialises and seeds the SQLite database (`spendly.db`) automatically on startup via `init_db()` / `seed_db()` inside an `app_context` block at module level in `app.py`.

## Architecture

**Spendly** is a Flask/SQLite expense tracker. Python 3.12, virtual env at `.venv/`.

### Request flow

`app.py` → route handler → `database/db.py` functions → `spendly.db`

All DB access goes through raw `sqlite3` connections returned by `get_db()` in `database/db.py`. There is no ORM. The schema has two tables: `users` and `expenses` (user_id FK, amount, category, date, description).

### Services layer (stubs)

`services/categoriser.py` and `services/excel_parser.py` are currently empty — these are the planned AI-categorisation and Excel-import components. `config/categories.json` defines the keyword→category mappings the categoriser will consume (keys are category names; values are keyword lists matched against transaction descriptions).

### Templates

All pages extend `templates/base.html`, which provides the navbar (session-aware), footer, and global CSS/JS includes (`static/css/style.css`, `static/js/main.js`). The landing page has its own stylesheet (`static/css/landing.css`).

### Work in progress

- The `/profile` route returns hardcoded mock data; it needs to be wired to the real DB.
- `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` return placeholder strings.
- The `/register` Flask route is commented out; `register()` exists as a bare function at the bottom of `app.py` for manual testing via `__main__`.

### Demo credentials

`demo@spendly.com` / `demo123` — seeded on first startup if the users table is empty.
