# Spec: Excel Parsing

## Overview

Parse an Excel file and insert the extracted data into the `transactions` table.

The file `excel_parser.py` is currently empty. A sample input Excel file is available at `data/sample_jan26_expense.xlsx`. When a user uploads an Excel file, it is stored in the `data/uploads` directory. The parser should read the uploaded Excel file, extract relevant data, and insert the processed records into the `transactions` table.

### Excel Columns

The input Excel file contains the following columns:

- `date`
- `narration`
- `withdrawal_amount`
- `deposit_amount`

### Parsing Logic

**1. Transaction Note (`txn_note`)**
- Split the `narration` string using `-` (hyphen)
- Extract the **last segment** as `txn_note`
- Example: `UPI-AMAZON PAY GROCERIES-AMAZONPAYGROCERY@RAPL-RATN000RAPL-192258258145-YOU ARE PAYING FOR` → `txn_note`: `YOU ARE PAYING FOR`

**2. Beneficiary Extraction**
- Extract the substring between `UPI-` and `@`
- This represents the **beneficiary name**
- Example: `UPI-AMAZON PAY GROCERIES-AMAZONPAYGROCERY@RAPL-...` → `beneficiary`: `AMAZON PAY GROCERIES-AMAZONPAYGROCERY`

**3. Category**
- Keep the `category` field **empty string** while inserting into the database

## Depends on

- Step 01 — Database initialisation (`init_db` and `transactions` table must exist)

## Routes

- `POST /upload` — accepts a multipart form upload of an `.xlsx` file, calls the parser, and redirects to `/profile` — logged-in only

## Database changes

No new tables or columns. The existing `transactions` table already has all required fields:
- `date` TEXT NOT NULL
- `beneficiary` TEXT NOT NULL
- `txn_note` TEXT
- `withdraw_amount` REAL NOT NULL 
- `deposit_amount` REAL NOT NULL
- `category` TEXT NOT NULL

> **Important:** The DB column is `withdraw_amount` (not `withdrawal_amount`). The Excel file uses `withdrawal_amount` — map accordingly during insertion.

## Templates

- **Modify:** `templates/profile.html` — add an upload form (file input + submit button) that POSTs to `/upload`

## Files to change

- `services/excel_parser.py` — implement all parsing and DB insertion logic
- `app.py` — add the `POST /upload` route
- `templates/profile.html` — add file upload form
- `database/db.py` — add `insert_transactions(rows)` helper function

## Files to create

No new files (uploads go to the existing `data/uploads/` directory).

## New dependencies

- `openpyxl` — for reading `.xlsx` files (add to `requirements.txt`)

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only
- Parameterised queries only — never string-interpolate SQL
- Passwords hashed with werkzeug (not relevant here, included for completeness)
- Use CSS variables — never hardcode hex values in templates
- All templates extend `base.html`
- Use `pathlib` for all file system and path operations — never `os.path`
- Modular functions: separate functions for reading the file, extracting fields from a row, and inserting into the DB
- Validate that the uploaded file has a `.xlsx` extension before processing; return a flash error if not
- Save the uploaded file to `data/uploads/` before parsing
- Handle missing or malformed `narration` values gracefully (e.g. non-UPI rows): set `beneficiary` to the raw narration and `txn_note` to an empty string
- `category` must be inserted as an empty string `""` (the column is `NOT NULL`)

## Definition of done

- [ ] Uploading `data/sample_jan26_expense.xlsx` via the profile page succeeds without an error
- [ ] Uploaded file is saved to `data/uploads/`
- [ ] Rows from the Excel file appear in the `transactions` table (verify with `sqlite3 data/app.db "SELECT * FROM transactions LIMIT 5"`)
- [ ] `txn_note` for a UPI narration contains only the last hyphen-separated segment
- [ ] `beneficiary` for a UPI narration contains the substring between `UPI-` and `@`
- [ ] Non-UPI rows do not crash the parser
- [ ] Uploading a non-`.xlsx` file shows an error and does not insert any rows
- [ ] After upload, the user is redirected to `/profile`
- [ ] All inserted rows have `category` set to `""`
