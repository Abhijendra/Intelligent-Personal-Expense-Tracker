# Spec: Fix LLM Categorization

## Overview

The LLM fallback categorizer introduced in Step 11 incorrectly returns `SKIP` for merchant
transactions. The prompt uses a loose natural-language rule that the model over-generalizes:
it skips transactions whose transaction note resembles `"PAYMENT FROM PHONEPE"` (e.g., just
`"PAY"` or `"PAYMENT FROM PHONE"`) and whose beneficiary looks vaguely person-like (e.g.,
`"RSMANI CAFE-PAYTM"`). This fix adds deterministic backend guards so the LLM is never solely
responsible for enforcing the skip rule. A pre-check using `is_likely_person()` gates the LLM
call; the prompt is tightened with exact-match wording and negative examples; and a
post-validation step rejects any `SKIP` response that does not satisfy both conditions.

## Depends on

- Step 11 — Categorization Fallback LLM (`llm_categorise_transactions` must already exist in `services/categoriser.py`)

## Routes

No new routes.

## Database changes

No database changes.

## Templates

No template changes.

## Files to change

- `services/categoriser.py`
  - Add `is_likely_person(beneficiary: str) -> bool` — returns `True` only when the name
    contains no business/merchant keywords, no payment-gateway suffixes, and no special
    characters (`-`, `.`, `/`, digits).
  - In `llm_categorise_transactions`: add a pre-check before calling the LLM:
    if `txn_note.strip() == "PAYMENT FROM PHONEPE"` **and** `is_likely_person(beneficiary)`
    → skip without calling the API.
  - Replace the current prompt with a stricter version that defines exact-match conditions
    and includes negative examples (see below).
  - Add post-validation: if the LLM returns `SKIP`, re-verify both conditions in Python;
    if either fails, discard `SKIP` and call the LLM again with a prompt that explicitly
    forbids `SKIP`.

- `tests/test_categoriser.py`
  - Add unit tests for `is_likely_person`.
  - Add tests for the pre-check and post-validation logic (mock the OpenAI client).

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` only.
- Parameterised queries only — never string-interpolate SQL values.
- Passwords hashed with werkzeug (not relevant here, included for consistency).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Use `pathlib` for file system operations.
- `is_likely_person` must be a pure function with no I/O — keep it unit-testable.
- The pre-check must use an **exact** case-insensitive string comparison:
  `txn_note.strip().upper() == "PAYMENT FROM PHONEPE"`.
- Merchant keyword list for `is_likely_person` must include at minimum:
  `CAFE`, `STORE`, `MART`, `HOTEL`, `SERVICES`, `SHOP`, `FOODS`, `KITCHEN`, `BAKERY`,
  `RESTAURANT`, `PAYTM`, `RAZORPAY`, `EASEBUZZ`, `PHONEPE`, `GPAY`, `UPI`.
- Any beneficiary containing `-`, `.`, `/`, or digits is treated as a merchant (not a person).
- Post-validation must never silently accept an invalid `SKIP` — it must re-call the LLM
  with a follow-up prompt that explicitly says "Do NOT return SKIP".
- Do not change the keyword-based `_match_keyword` path.

## Revised prompt design

```text
You are a transaction categorization assistant.

Available categories: {comma-separated keys from categories.json}

RULE — return "SKIP" ONLY when ALL of the following are strictly true:
  1. Transaction Note is EXACTLY "PAYMENT FROM PHONEPE" (no other variation counts)
  2. Beneficiary is a plain human name with:
     - no business words (CAFE, STORE, MART, HOTEL, SERVICES, SHOP, etc.)
     - no payment gateway names (PAYTM, RAZORPAY, EASEBUZZ, PHONEPE, GPAY, etc.)
     - no special characters (-, ., /)
     - no digits

If ANY condition above is not met, you MUST return a category from the list — never SKIP.

Positive example  → SKIP:
  Note: "PAYMENT FROM PHONEPE"  |  Beneficiary: "RAHUL SHARMA"

Negative examples → NOT SKIP:
  Note: "PAYMENT FROM PHONE"    |  Beneficiary: "NAGAARJUN RAJAN KOND"  → (classify normally)
  Note: "PAYMENT FROM PHONEPE"  |  Beneficiary: "RSMANI CAFE-PAYTM"     → food
  Note: "PAY"                   |  Beneficiary: "RIOZSTORE-EASEBUZZ"    → shopping

Return exactly one word: a category name from the list OR "SKIP".
No explanation. No punctuation. No extra text.

Transaction Note: "{txn_note}"
Beneficiary: "{beneficiary}"
```

## `is_likely_person` sketch

```python
import re

MERCHANT_KEYWORDS = {
    "cafe", "store", "mart", "hotel", "services", "shop", "foods",
    "kitchen", "bakery", "restaurant", "paytm", "razorpay", "easebuzz",
    "phonepe", "gpay", "upi", "pay", "pvt", "ltd", "solutions",
}

def is_likely_person(beneficiary: str) -> bool:
    if not beneficiary:
        return False
    b = beneficiary.strip()
    # any special character or digit → merchant
    if re.search(r"[-./\d]", b):
        return False
    words = b.lower().split()
    # any known merchant keyword → not a person
    if any(w in MERCHANT_KEYWORDS for w in words):
        return False
    # must have at least 2 words (first + last name)
    return len(words) >= 2
```

## Post-validation sketch

```python
if result == "skip":
    # Re-validate in Python — do not trust LLM alone
    note_matches = row["txn_note"].strip().upper() == "PAYMENT FROM PHONEPE"
    person_matches = is_likely_person(row["beneficiary"])
    if note_matches and person_matches:
        continue  # valid skip
    # Invalid skip — re-call LLM forbidding SKIP
    retry_prompt = prompt + "\n\nIMPORTANT: Do NOT return SKIP. Return a category."
    try:
        retry_resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL"),
            messages=[{"role": "user", "content": retry_prompt}],
            temperature=0,
            max_tokens=20,
        )
        result = retry_resp.choices[0].message.content.strip().lower()
    except Exception as e:
        logger.error("LLM retry failed for txn %s: %s", row["id"], e)
        continue
```

## Definition of done

- [ ] `is_likely_person("RAHUL SHARMA")` returns `True`.
- [ ] `is_likely_person("RSMANI CAFE-PAYTM")` returns `False`.
- [ ] `is_likely_person("RIOZSTORE-EASEBUZZ")` returns `False`.
- [ ] `is_likely_person("NAGAARJUN RAJAN KOND")` returns `True`.
- [ ] A transaction with `txn_note="PAYMENT FROM PHONE"` and `beneficiary="NAGAARJUN RAJAN KOND"` is categorized (not skipped) after the fix.
- [ ] A transaction with `txn_note="PAYMENT FROM PHONEPE"` and `beneficiary="RSMANI CAFE-PAYTM"` is categorized as `food` (not skipped).
- [ ] A transaction with `txn_note="PAY"` and `beneficiary="RIOZSTORE-EASEBUZZ"` is categorized as `shopping` (not skipped).
- [ ] A transaction with `txn_note="PAYMENT FROM PHONEPE"` and `beneficiary="RAHUL SHARMA"` is correctly skipped (no DB update).
- [ ] `pytest` passes with no regressions (OpenAI client mocked in all tests).
