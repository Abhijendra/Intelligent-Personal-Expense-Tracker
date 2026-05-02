from unittest.mock import MagicMock, patch, call

from services.categoriser import llm_categorise_transactions


def _insert_txn(conn, *, txn_note="", beneficiary="TEST", withdraw=100.0, category=None):
    cur = conn.execute(
        "INSERT INTO transactions (date, beneficiary, txn_note, withdraw_amount, deposit_amount, category) "
        "VALUES ('2026-01-01', ?, ?, ?, 0.0, ?)",
        (beneficiary, txn_note, withdraw, category),
    )
    conn.commit()
    return cur.lastrowid


def _make_llm_response(text):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def test_llm_sets_valid_category(db_conn):
    txn_id = _insert_txn(db_conn, txn_note="YOU ARE PAYING FOR", beneficiary="AMAZON INDIA-AMAZON")

    with patch("services.categoriser.get_db", return_value=db_conn), \
         patch("services.categoriser.OpenAI") as mock_openai, \
         patch("services.categoriser.update_transaction_category") as mock_update:
        mock_openai.return_value.chat.completions.create.return_value = _make_llm_response("shopping")
        llm_categorise_transactions([txn_id])

    mock_update.assert_called_once_with(txn_id, "shopping")


def test_llm_skips_already_categorized(db_conn):
    txn_id = _insert_txn(db_conn, txn_note="zomato order", category="food")

    with patch("services.categoriser.get_db", return_value=db_conn), \
         patch("services.categoriser.OpenAI") as mock_openai, \
         patch("services.categoriser.update_transaction_category") as mock_update:
        llm_categorise_transactions([txn_id])

    mock_openai.return_value.chat.completions.create.assert_not_called()
    mock_update.assert_not_called()


def test_llm_skips_credit_transactions(db_conn):
    txn_id = _insert_txn(db_conn, txn_note="salary credit", withdraw=0.0)

    with patch("services.categoriser.get_db", return_value=db_conn), \
         patch("services.categoriser.OpenAI") as mock_openai, \
         patch("services.categoriser.update_transaction_category") as mock_update:
        llm_categorise_transactions([txn_id])

    mock_openai.return_value.chat.completions.create.assert_not_called()
    mock_update.assert_not_called()


def test_llm_ignores_invalid_response(db_conn):
    txn_id = _insert_txn(db_conn, txn_note="mystery payment")

    with patch("services.categoriser.get_db", return_value=db_conn), \
         patch("services.categoriser.OpenAI") as mock_openai, \
         patch("services.categoriser.update_transaction_category") as mock_update:
        mock_openai.return_value.chat.completions.create.return_value = _make_llm_response("luxury_yachts")
        llm_categorise_transactions([txn_id])

    mock_update.assert_not_called()


def test_llm_handles_api_error(db_conn):
    txn_id = _insert_txn(db_conn, txn_note="unknown merchant")

    with patch("services.categoriser.get_db", return_value=db_conn), \
         patch("services.categoriser.OpenAI") as mock_openai, \
         patch("services.categoriser.update_transaction_category") as mock_update:
        mock_openai.return_value.chat.completions.create.side_effect = Exception("network error")
        llm_categorise_transactions([txn_id])  # must not raise

    mock_update.assert_not_called()
