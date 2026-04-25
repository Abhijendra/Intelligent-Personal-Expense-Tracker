# CLAUDE.md

This document provides guidance for Claude Code when working within this repository.

---

## 🚀 Commands

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

> The application automatically initializes and seeds the SQLite database (`spendly.db`) on startup using `init_db()` and `seed_db()` within an `app_context` block in `app.py`.

---

## 📌 Project Overview

This is a **Flask + SQLite-based personal expense tracker** that enables users to manage expenses by uploading bank statement Excel files.

### Core Workflow

* User uploads a bank statement (`.xlsx`)
* The application:

  * Parses the file
  * Inserts transactions into the database
  * Categorizes each transaction

### Categorization Logic

1. **Primary method**: Keyword-based matching using `config/categories.json`
2. **Fallback**: LLM-based categorization using:

   * Beneficiary
   * Transaction note

If a new category is inferred via LLM:

* It is added to `categories.json`
* Future transactions avoid repeated LLM calls

### Additional Features

* Users can **view and edit `categories.json` directly from the UI**
* Updating a category triggers:

  * Re-categorization of relevant transactions
  * Update of the `category` column in the `transactions` table
  * Do not expose the raw `categories.json` file for direct editing. Instead, provide a well-designed UI that enables users to view and modify categories with a smooth and intuitive user experience.

---

## 🏗️ Architecture

* **Python Version**: 3.12
* **Environment**: Virtual environment at `.venv/`

### High-Level Flow

```
User → Uploads statement.xlsx
     → excel_parser.py parses file
     → Transactions inserted into DB
     → categoriser assigns categories
     → Last 15 transactions displayed on UI
```

### Category Update Flow

```
User → Edits categories.json via UI
     → Triggers re-categorization
     → Updates all transactions in DB
```

---

## 🔁 Request Flow

```
app.py → Route Handler → database/db.py → SQLite (app.db)
```

* All database operations use raw `sqlite3`
* Connections are managed via `get_db()` in `database/db.py`
* **No ORM is used**

### Database Schema

**Tables:**

* `users`
* `transactions`
  Fields:

  * `date`
  * `beneficiary`
  * `txn_note`
  * `withdrawal_amount`
  * `deposit_amount`
  * `category`

---

## 🧠 Services Layer (Planned)

The following modules are currently placeholders:

* `services/categoriser.py` → AI-based categorization
* `services/excel_parser.py` → Excel ingestion logic

### Configuration

* `config/categories.json`

  * Maps **category → list of keywords**
  * Used for rule-based categorization

---

## 🎨 Templates & Static Assets

* All templates extend: `templates/base.html`

  * Includes navbar (session-aware), footer, and global assets

**Static Files:**

* `static/css/style.css`
* `static/js/main.js`
* `static/css/landing.css` (used by landing page)

---

## 🚧 Work in Progress

* `/profile` route currently returns mock data → needs DB integration
* `/category/add` returns placeholder responses → planned for future category management

---

## 🔐 Demo Credentials

* **Email**: `demo@spendly.com`
* **Password**: `demo123`

> These credentials are automatically seeded if the `users` table is empty.

### Note

* No public registration feature will be implemented
* Developer-only backdoor registration may exist for internal use

---

## 🧹 Code Style Guidelines

* Write **modular and maintainable code**
* Prioritize **clarity and readability**
* Keep the codebase **beginner-friendly**

---

## 📚 Preferred Libraries

* Use `pathlib` for file system and path operations instead of `os`

---