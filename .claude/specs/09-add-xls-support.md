# Spec: Add XLS File Support

## Overview

Currently the application only accepts `.xlsx` uploads. Legacy Excel files (`.xls`) are still widely produced by older banking portals and accounting software. This step extends the upload pipeline to accept both formats, routing each through an appropriate parsing engine while producing identical output — a list of transaction dicts — that the rest of the system consumes unchanged.

## Depends on

- Step 02 (Excel Parsing) — `services/excel_parser.py` and the `/upload` route must already exist.

## Routes

No new routes.  
The existing `POST /upload` route is modified to accept both extensions.

## Database changes

No database changes.

## Templates

- **Modify:** `templates/profile.html` — update any file-input hint text or accept attribute from `.xlsx` to `.xls, .xlsx`.

## Files to change

- `app.py` — relax the extension check and update the flash error message.
- `services/excel_parser.py` — add an `.xls` parsing path using `xlrd`; keep the existing `openpyxl` path for `.xlsx`.
- `requirements.txt` — add `xlrd>=2.0`.

## Files to create

No new files.

## New dependencies

- `xlrd>=2.0` — the only actively-maintained `xlrd` release; supports `.xls` (BIFF format) only (intentionally dropped `.xlsx` support in 2.x, which is fine — `openpyxl` still handles `.xlsx`).

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only.
- Passwords hashed with werkzeug.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Do **not** introduce `pandas` as a dependency; use `xlrd` directly for `.xls` and keep `openpyxl` for `.xlsx`.
- Both code paths must return `list[dict]` with the same keys: `date`, `beneficiary`, `txn_note`, `withdraw_amount`, `deposit_amount`, `category`.
- `xlrd` uses 0-based row/column indexing; `openpyxl` uses 1-based — be explicit about which is in use.
- Wrap both parsing paths in a `try/except` that raises a descriptive `ValueError` on corrupt or malformed files; let the `/upload` route catch it and `flash` a user-friendly error.
- The existing `_normalise_date`, `parse_narration`, and `find_header_row` helpers should be reused or adapted — avoid duplicating logic.

## Definition of done

- [ ] Uploading a valid `.xls` bank statement imports transactions successfully and the success flash message shows the correct count.
- [ ] Uploading a valid `.xlsx` bank statement still works unchanged.
- [ ] Uploading a file with neither `.xls` nor `.xlsx` extension shows the error: "Please upload a valid Excel file (.xls or .xlsx)."
- [ ] Uploading a file named `bad.xls` that contains garbage bytes shows a user-friendly error flash (not a 500).
- [ ] The file-input in the UI accepts both `.xls` and `.xlsx` (the `accept` attribute reflects both).
- [ ] `xlrd` is listed in `requirements.txt` and `pip install -r requirements.txt` completes without conflict.
- [ ] All existing tests pass (`pytest`).
