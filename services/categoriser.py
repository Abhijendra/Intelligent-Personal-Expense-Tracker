import json
import os
import logging
from pathlib import Path
from openai import OpenAI
from database.db import get_db, update_transaction_category

logger = logging.getLogger("categoriser")

CATEGORIES_PATH = Path(__file__).parent.parent / "config" / "categories.json"


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
        prompt = (
            "You are a transaction categorization assistant.\n\n"

            f"Available categories: {', '.join(allowed)}\n\n"

            "STRICT RULE:\n"
            "If BOTH conditions are true:\n"
            "- Transaction Note is exactly 'PAYMENT FROM PHONEPE'\n"
            "- Beneficiary appears to be a person's name (not a business)\n"
            "Then return exactly: SKIP\n\n"

            "Otherwise:\n"
            "Classify the transaction into EXACTLY ONE of the available categories.\n"
            "Return only ONE word from the category list OR 'SKIP'.\n"
            "Do not return anything else.\n\n"

            "Examples:\n"
            "- mango, coffee, capsicum -> food\n"
            "- cylinder delivery, wifi, electricity -> utilities\n"
            "- medicines, gym, hospital -> health\n"
            "- spa, salon, haircut -> personal_care\n\n"

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
            logger.info(f"Input: {row['txn_note']} | {row['beneficiary']} | {row['withdraw_amount']} -> {result}")

            if result == "skip":
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
