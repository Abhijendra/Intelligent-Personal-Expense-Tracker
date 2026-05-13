# Intelligent Personal Expense Tracker

A personal expense tracker built with Flask and SQLite. Upload your bank statement and Spendly automatically categorizes your transactions — using keyword rules first, then an OpenAI LLM as a fallback.

---

## Features

- Upload bank statements in `.xls` or `.xlsx` format
- Automatic transaction categorization (keyword-based + LLM fallback)
- Duplicate upload detection — re-uploading the same file is safe
- Dashboard with spend summary, category breakdown, and full transaction history
- Date range filtering
- Category management UI with one-click re-categorization
- User can edit categories according to them on UI.

---

## Getting Started

**Prerequisites**: Python 3.12, a virtual environment tool, and an OpenAI API key.

```bash
# Clone and set up
git clone <repo-url>
cd ai-expense-tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

```bash
# Run the app
python app.py
```

Open [http://localhost:5003](http://localhost:5003) and log in with:

| Email | Password |
|-------|----------|
| `demo@spendly.com` | `demo123` |

---

## How It Works

### Upload Flow

```
Upload .xls / .xlsx
  → Parse narration into beneficiary + transaction note
  → Insert rows (duplicates silently skipped)
  → Keyword match against config/categories.json
  → LLM categorization for unmatched transactions
```

### Categorization

1. **Keyword matching** — each category in `config/categories.json` has a list of keywords. If any keyword appears in the transaction note or beneficiary name, the category is assigned.
2. **LLM fallback** — uncategorized transactions are sent to OpenAI. Peer-to-peer transfers with transaction note "PAYMENT FROM PHONE" to a person's name or merchant are skipped automatically by LLM.

### Excel Format

The parser expects standard Indian bank statement columns:

| Column | Description |
|--------|-------------|
| `Date` | Transaction date |
| `Narration` | UPI narration or description |
| `Withdrawal Amt.` | Debit amount |
| `Deposit Amt.` | Credit amount |

UPI narrations (`UPI-<beneficiary>@...-<note>`) are automatically split into a beneficiary and a transaction note.

---

## Project Structure

```
├── app.py                    # Flask app and routes
├── config/
│   └── categories.json       # category → [keywords] mapping
├── database/
│   └── db.py                 # SQLite helpers (no ORM)
├── services/
│   ├── excel_parser.py       # .xlsx and .xls parsing
│   └── categoriser.py        # keyword + LLM categorization
├── templates/                # Jinja2 templates (extend base.html)
├── static/                   # CSS and JS
├── data/
│   ├── app.db                # SQLite database
│   └── uploads/              # Uploaded statement files
└── tests/
```

---

## Running Tests

```bash
source .venv/bin/activate
pytest
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Web framework | Flask |
| Database | SQLite (raw `sqlite3`) |
| Excel parsing | openpyxl, xlrd |
| LLM | OpenAI API |
| Auth | Werkzeug password hashing |
| Testing | pytest, pytest-flask |

Frontend credit: CampusX YouTube channel
