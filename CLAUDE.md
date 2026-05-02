# CLAUDE.md

This document provides guidance for Claude Code when working within this repository.

---

## Commands

```bash
# Run the app (port 5003)
source .venv/bin/activate && python app.py

# Run all tests
source .venv/bin/activate && pytest

# Run a specific test file
source .venv/bin/activate && pytest tests/test_foo.py

# Install dependencies
pip install -r requirements.txt
```

> The application automatically initializes the SQLite database (`data/app.db`) on startup via `init_db()` inside an `app_context` block in `app.py`. `seed_db()` is currently commented out.

---

## Project Overview

**Spendly** is a Flask + SQLite personal expense tracker. Users upload bank statement Excel files to track and categorize spending.

### Core Workflow

1. User uploads a bank statement (`.xls` or `.xlsx`)
2. `excel_parser.py` parses the file into rows
3. Rows are inserted into the `transactions` table (duplicates skipped via `UNIQUE` constraint)
4. `categoriser.py` assigns categories using keyword matching, then LLM fallback

### Categorization Logic

1. **Primary**: keyword matching against `config/categories.json` (category → list of keywords)
2. **Fallback**: LLM via OpenAI API — uses `txn_note` + `beneficiary` to infer category
   - Returns `SKIP` for peer-to-peer transfers (e.g. "PAYMENT FROM PHONE" to a human name)
   - Includes retry logic if an invalid SKIP is returned
   - Inferred categories must already exist in `categories.json` (no new categories are added at runtime)

### Category Management

- Users can view and edit `categories.json` via the UI (not direct file exposure)
- Editing a category triggers re-categorization of all transactions via `/refresh-categories`

---

## Architecture

- **Python**: 3.12
- **Environment**: `.venv/`
- **Database**: SQLite at `data/app.db` (raw `sqlite3`, no ORM)
- **LLM**: OpenAI API (`OPENAI_API_KEY`, `OPENAI_MODEL` env vars via `.env`)

### File Structure

```
app.py                        # Flask app, routes, startup
config/categories.json        # category → [keywords] mapping
database/
  db.py                       # get_db, init_db, seed_db, insert_transactions, update_transaction_category
services/
  excel_parser.py             # parse_file() — supports .xlsx (openpyxl) and .xls (xlrd)
  categoriser.py              # categorise_transactions(), recategorise_all_transactions(), llm_categorise_transactions()
templates/
  base.html                   # base layout with navbar and footer
  landing.html, login.html, profile.html, privacy.html, terms.html
static/
  css/style.css, css/landing.css
  js/main.js
data/
  app.db                      # SQLite database
  uploads/                    # uploaded Excel files
tests/
  conftest.py
  test_categoriser.py
```

### Request Flow

```
app.py → Route Handler → database/db.py → SQLite (data/app.db)
```

### Database Schema

**`users`**

| Column        | Type    |
|---------------|---------|
| id            | INTEGER PK AUTOINCREMENT |
| name          | TEXT    |
| email         | TEXT UNIQUE |
| password_hash | TEXT    |
| created_at    | TEXT    |

**`transactions`**

| Column         | Type    |
|----------------|---------|
| id             | INTEGER PK AUTOINCREMENT |
| date           | TEXT    |
| beneficiary    | TEXT    |
| txn_note       | TEXT    |
| withdraw_amount| REAL    |
| deposit_amount | REAL    |
| category       | TEXT    |

Duplicate detection: `UNIQUE(date, beneficiary, txn_note, withdraw_amount, deposit_amount)`

> Note: The column is `withdraw_amount` (not `withdrawal_amount` as in earlier docs).

---

## Routes

| Method | Path                  | Auth | Description                                  |
|--------|-----------------------|------|----------------------------------------------|
| GET    | `/`                   | No   | Landing page                                 |
| GET    | `/login`              | No   | Login form                                   |
| POST   | `/login`              | No   | Authenticate user                            |
| GET    | `/logout`             | Yes  | Clear session, redirect to landing           |
| GET    | `/profile`            | Yes  | Dashboard: stats, transactions, categories   |
| POST   | `/upload`             | Yes  | Upload `.xls`/`.xlsx`, parse, insert, categorize |
| POST   | `/refresh-categories` | Yes  | Re-run keyword categorization on all transactions |
| GET    | `/terms`              | No   | Terms of service                             |
| GET    | `/privacy`            | No   | Privacy policy                               |
| GET    | `/category/add`       | Yes  | Placeholder — not yet implemented            |

### Profile Page Features

- Summary stats: total spent, transaction count, top category
- Date range filter (`start_date`, `end_date` query params)
- Full transaction list (all matching transactions, newest first)
- Category breakdown with spend percentages; `Miscellaneous` always shown last

---

## Auth & Users

- `login_required` decorator redirects unauthenticated users to `/login`
- No public registration; users are created via the `register()` helper in `app.py`
- A hardcoded developer user (`abhijendra.work@outlook.com`) is registered on startup (silently ignored if already exists)
- Demo credentials (seeded when `users` table is empty — currently `seed_db()` is commented out):
  - **Email**: `demo@spendly.com`
  - **Password**: `demo123`

---

## Excel Parsing

`services/excel_parser.py` → `parse_file(path)` dispatches to:

- `_parse_xlsx()` — uses `openpyxl`
- `_parse_xls()` — uses `xlrd`

Both parsers:
- Locate the header row by scanning for a `"Date"` cell in column 1
- Parse `Narration` field: UPI narrations (`UPI-<beneficiary>@...-<note>`) are split into `beneficiary` + `txn_note`
- Skip rows with zero withdrawal and zero deposit
- Normalize dates to `YYYY-MM-DD`

---

## Code Style Guidelines

- Write modular and maintainable code
- Prioritize clarity and readability; keep the codebase beginner-friendly
- Use `pathlib` for all file system and path operations (not `os`)
- No ORM — use raw `sqlite3` throughout
- Templates all extend `templates/base.html`

---

## Dependencies

See `requirements.txt`:

- `flask`, `werkzeug` — web framework and security
- `openpyxl`, `xlrd>=2.0` — Excel parsing
- `openai` — LLM categorization fallback
- `python-dotenv` — `.env` loading
- `pytest`, `pytest-flask` — testing

---

## Work in Progress

- `/category/add` returns a placeholder string — category add/edit UI is not yet implemented
