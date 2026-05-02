import json
import os
import logging
import re
from pathlib import Path
from openai import OpenAI
from database.db import get_db, update_transaction_category

logger = logging.getLogger("categoriser")

CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "categories.json"

MERCHANT_KEYWORDS = {
    "cafe", "store", "mart", "hotel", "services", "shop", "foods",
    "kitchen", "bakery", "restaurant", "paytm", "razorpay", "easebuzz",
    "phonepe", "gpay", "upi", "pay", "pvt", "ltd", "solutions",
}


def is_likely_person(beneficiary: str) -> bool:
    if not beneficiary:
        return False
    b = beneficiary.strip()
    if re.search(r"[-./\d]", b):
        return False
    words = b.lower().split()
    # if any(w in MERCHANT_KEYWORDS for w in words):
    #     return False
    return len(words) >= 2


def _load_categories() -> dict[str, list[str]]:
    with open(CATEGORIES_PATH) as f:
        return json.load(f)


def _match_keyword(text: str, categories: dict) -> str | None:
    if not text:
        return None
    text_lower = text.lower()
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return category
    return None


def llm_categorise_transactions(txn_ids: list[int]) -> None:
    if not txn_ids:
        return

    categories = _load_categories()
    allowed = list(categories.keys())
    allowed_lower = {c.lower(): c for c in allowed}

    conn = get_db()
    placeholders = ",".join("?" * len(txn_ids))
    rows = conn.execute(
        f"SELECT id, txn_note, beneficiary, withdraw_amount FROM transactions "
        f"WHERE id IN ({placeholders}) AND category IS NULL AND withdraw_amount > 0",
        txn_ids,
    ).fetchall()
    conn.close()

    if not rows:
        return

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    for row in rows:
        if (row["txn_note"].strip().upper() == "PAYMENT FROM PHONE"
                and is_likely_person(row["beneficiary"])):
            logger.info("Pre-check skip: %s | %s", row["txn_note"], row["beneficiary"])
            continue

        prompt = (
            "You are a transaction categorization assistant.\n\n"

            f"Available categories: {', '.join(allowed)}\n\n"

            "RULE — return \"SKIP\" ONLY when ALL of the following are strictly true:\n"
            "  1. Transaction Note is EXACTLY \"PAYMENT FROM PHONE\" (no other variation counts)\n"
            "  2. Beneficiary is a plain human name with:\n"
            "     - no business words (CAFE, STORE, MART, HOTEL, SERVICES, SHOP, etc.)\n"
            
            "If ANY condition above is not met, you MUST return a category from the list — never SKIP.\n\n"

            "Positive example → SKIP:\n"
            "  Note: \"PAYMENT FROM PHONE\"  |  Beneficiary: \"RAHUL SHARMA\"\n\n"
            "  Note: \"PAYMENT FROM PHONE\"    |  Beneficiary: \"NAGAARJUN RAJAN KOND\"\n\n"
            "  Note: \"PAYMENT FROM PHONE\"    |  Beneficiary: \"GOLAM MOSTAFA MONDAL-7407126299\"\n\n"

            "Negative examples → NOT SKIP:\n"
            "  Note: \"PAYMENT FROM PHONE\"  |  Beneficiary: \"RSMANI CAFE-PAYTM\"     → food\n"
            "  Note: \"PAY\"                   |  Beneficiary: \"RIOZSTORE-EASEBUZZ\"    → shopping\n"
            "  Note: \"COCA COLA\"             |  Beneficiary: \"ANKIT PRASHANT THAKU-Q087497859\" -> food\n"

            "Return exactly one word: a category name from the list OR \"SKIP\".\n"
            "No explanation. No punctuation. No extra text.\n\n"

            f"Transaction Note: \"{row['txn_note']}\"\n"
            f"Beneficiary: \"{row['beneficiary']}\""
        )

        try:
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=20,
            )
            result = response.choices[0].message.content.strip().lower()
            logger.info("Input: %s | %s | %s -> %s", row["txn_note"], row["beneficiary"], row["withdraw_amount"], result)

            if result == "skip":
                note_matches = row["txn_note"].strip().upper() == "PAYMENT FROM PHONE"
                person_matches = is_likely_person(row["beneficiary"])
                if note_matches and person_matches:
                    continue
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

            canonical = allowed_lower.get(result)
            if canonical is None:
                continue

            update_transaction_category(row["id"], canonical)
        except Exception as e:
            logger.error("LLM categorization failed for txn %s: %s", row["id"], e)


def recategorise_all_transactions() -> int:
    categories = _load_categories()
    conn = get_db()
    rows = conn.execute(
        "SELECT id, txn_note, beneficiary FROM transactions WHERE withdraw_amount > 0"
    ).fetchall()
    conn.close()

    updated = 0
    for row in rows:
        category = (
            _match_keyword(row["txn_note"], categories)
            or _match_keyword(row["beneficiary"], categories)
        )
        if category:
            update_transaction_category(row["id"], category)
            updated += 1
    return updated


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

    llm_categorise_transactions(txn_ids)
