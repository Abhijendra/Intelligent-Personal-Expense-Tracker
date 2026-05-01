import json
from pathlib import Path
from database.db import get_db, update_transaction_category

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
