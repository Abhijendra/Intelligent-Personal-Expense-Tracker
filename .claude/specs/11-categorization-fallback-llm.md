# Spec: Categorization Fallback LLM

## Overview

The primary keyword-based categorizer (`services/categoriser.py`) leaves transactions with `category = NULL` when no keyword in `config/categories.json` matches the `txn_note` or `beneficiary`. This step adds an LLM-powered fallback that runs immediately after primary categorization and classifies only those remaining debit transactions. The LLM is given the `txn_note`, `beneficiary`, and the dynamic list of valid category names (keys from `categories.json`) and must return exactly one category from that list. Validated results are persisted to `transactions.category`; anything unrecognized is left NULL.

## Depends on

- Step 05 — Primary Categorization (`categorise_transactions` must run first and leave unmatched rows as NULL)
- Step 10 — Duplicate Uploads Fix (`insert_transactions` returns `{"inserted", "skipped", "ids"}`)

## Routes

No new routes.

## Database changes

No database changes. The existing `category TEXT` column in `transactions` is already nullable.

## Templates

No template changes.

## Files to change

- `services/categoriser.py`
  - Add `llm_categorise_transactions(txn_ids)` — queries the DB for debit rows where `category IS NULL` from the given ID list, sends each to the OpenAI API, validates the response against the current category keys, and updates the DB.
  - Modify `categorise_transactions(txn_ids)` to call `llm_categorise_transactions(txn_ids)` after keyword matching completes.
- `requirements.txt`
  - Add `openai` package.

## Files to create

No new files.

## New dependencies

- `openai` — official OpenAI Python SDK (used for ChatCompletion API calls).

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only.
- Parameterised queries only — never string-interpolate SQL values.
- Passwords hashed with werkzeug (not relevant here, included for consistency).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Use `pathlib` for file system and path operations.
- LLM fallback runs **only after** `_match_keyword` has already been applied — never replace the keyword match.
- Only debit transactions (`withdraw_amount > 0`) with `category IS NULL` are sent to the LLM.
- The allowed category list must be derived **dynamically** from the keys of `categories.json` at call time — never hardcoded.
- Validate the LLM response: if the returned string is not in the allowed category list, do **not** write it to the DB (leave NULL).
- If the OpenAI API call raises an exception (network error, rate limit, etc.), log the error and leave the transaction as NULL — do not crash the upload flow.
- The OpenAI API key must be read from the environment variable `OPENAI_API_KEY` — never hardcoded.

## Prompt design

```text
You are a transaction categorization assistant.

Available categories: {comma-separated keys from categories.json}

Classify the following bank transaction into EXACTLY ONE of the available categories above.
Return only the category name — no explanation, no punctuation, no extra text.

Transaction Note: "{txn_note}"
Beneficiary: "{beneficiary}"
```

Use `model="gpt-4o-mini"`, `temperature=0`, and `max_tokens=20` to keep responses short and deterministic.

## Implementation sketch

```python
import os
import logging
from openai import OpenAI

logger = logging.getLogger("root")


def llm_categorise_transactions(txn_ids: list[int]) -> None:
    if not txn_ids:
        return

    categories = _load_categories()
    allowed = list(categories.keys())
    allowed_lower = {c.lower(): c for c in allowed}

    conn = get_db()
    placeholders = ",".join("?" * len(txn_ids))
    rows = conn.execute(
        f"SELECT id, txn_note, beneficiary FROM transactions "
        f"WHERE id IN ({placeholders}) AND category IS NULL AND withdraw_amount > 0",
        txn_ids,
    ).fetchall()
    conn.close()

    if not rows:
        return

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    for row in rows:
        prompt = (
            f"You are a transaction categorization assistant.\n\n"
            f"Available categories: {', '.join(allowed)}\n\n"
            f"Classify the following bank transaction into EXACTLY ONE of the available categories above.\n"
            f"Return only the category name — no explanation, no punctuation, no extra text.\n\n"
            f"Transaction Note: \"{row['txn_note']}\"\n"
            f"Beneficiary: \"{row['beneficiary']}\""
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=20,
            )
            result = response.choices[0].message.content.strip().lower()
            canonical = allowed_lower.get(result)
            if canonical:
                update_transaction_category(row["id"], canonical)
        except Exception as e:
            logger.error(f"LLM categorization failed for txn {row['id']}: {e}")
```

Then in `categorise_transactions`:

```python
def categorise_transactions(txn_ids: list[int]) -> None:
    if not txn_ids:
        return
    categories = _load_categories()
    conn = get_db()
    placeholders = ",".join("?" * len(txn_ids))
    rows = conn.execute(
        f"SELECT id, txn_note, beneficiary, withdraw_amount "
        f"FROM transactions WHERE id IN ({placeholders})",
        txn_ids,
    ).fetchall()
    conn.close()

    for row in rows:
        if row["withdraw_amount"] == 0.0:
            continue
        category = (
            _match_keyword(row["txn_note"], categories)
            or _match_keyword(row["beneficiary"], categories)
        )
        if category:
            update_transaction_category(row["id"], category)

    llm_categorise_transactions(txn_ids)  # fallback for remaining NULLs
```

## Definition of done

- [ ] Uploading a file with a transaction whose note/beneficiary matches no keyword leaves `category = NULL` before LLM runs, then the LLM assigns a valid category and the DB is updated.
- [ ] A transaction with `txn_note = "YOU ARE PAYING FOR"` and `beneficiary = "AMAZON INDIA-AMAZON"` is classified as `shopping` (or another valid category) after the LLM fallback.
- [ ] Transactions already categorized by the keyword method are **not** re-sent to the LLM.
- [ ] Credit transactions (`withdraw_amount = 0`) are never sent to the LLM.
- [ ] If the LLM returns a string not in the allowed category list, the transaction remains `NULL` in the DB.
- [ ] If the OpenAI API is unreachable or throws, the upload completes without error and the transaction remains `NULL`.
- [ ] The `OPENAI_API_KEY` environment variable is used; the key is never present in any source file.
- [ ] `pytest` passes with no regressions (mock the OpenAI client in tests).
