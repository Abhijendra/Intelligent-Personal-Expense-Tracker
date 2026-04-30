from pathlib import Path
from datetime import datetime
import openpyxl


_DATE_FORMATS = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"]


def _normalise_date(raw: str) -> str:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # unknown format — store as-is


def find_header_row(ws) -> int:
    for row_idx in range(1, ws.max_row + 1):
        if ws.cell(row_idx, 1).value == "Date":
            return row_idx
    raise ValueError("Header row with 'Date' column not found in worksheet")


def parse_narration(narration) -> tuple[str, str]:
    if not narration:
        return "", ""
    narration = str(narration).strip()
    if narration.startswith("UPI-"):
        at_pos = narration.find("@")
        beneficiary = narration[4:at_pos] if at_pos != -1 else narration[4:]
        txn_note = narration.rsplit("-", 1)[-1].strip()
        return beneficiary, txn_note
    return narration, ""


def parse_file(file_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    header_row = find_header_row(ws)

    col_map = {}
    for col_idx in range(1, ws.max_column + 1):
        header = ws.cell(header_row, col_idx).value
        if header:
            col_map[str(header).strip()] = col_idx

    date_col = col_map.get("Date")
    narration_col = col_map.get("Narration")
    withdrawal_col = col_map.get("Withdrawal Amt.")
    deposit_col = col_map.get("Deposit Amt.")

    rows = []
    last_date_str = None
    for row_idx in range(header_row + 1, ws.max_row + 1):
        date_val = ws.cell(row_idx, date_col).value if date_col else None

        if date_val:
            if isinstance(date_val, datetime):
                candidate = date_val.strftime("%Y-%m-%d")
            else:
                raw = str(date_val).strip()
                candidate = _normalise_date(raw)

            # Skip masked values (e.g. '********' in redacted statements)
            if any(ch.isdigit() for ch in candidate):
                last_date_str = candidate

        # A row with no date but a valid narration continues the last date
        narration_check = ws.cell(row_idx, narration_col).value if narration_col else None
        if not last_date_str or not narration_check:
            continue

        date_str = last_date_str

        narration = narration_check
        beneficiary, txn_note = parse_narration(narration)

        withdraw_val = ws.cell(row_idx, withdrawal_col).value if withdrawal_col else None
        deposit_val = ws.cell(row_idx, deposit_col).value if deposit_col else None

        def to_float(val):
            try:
                return float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        withdraw_amount = to_float(withdraw_val)
        deposit_amount = to_float(deposit_val)

        # Skip rows with no actual money movement (e.g. summary/balance rows)
        if withdraw_amount == 0.0 and deposit_amount == 0.0:
            continue

        rows.append({
            "date": date_str,
            "beneficiary": beneficiary,
            "txn_note": txn_note,
            "withdraw_amount": withdraw_amount,
            "deposit_amount": deposit_amount,
            "category": None,
        })

    return rows
