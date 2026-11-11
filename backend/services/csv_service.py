"""CSV upload validation, preview, duplicate detection, and atomic SQLite import."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime
from typing import Any


REQUIRED_COLUMNS = [
    "transaction_date",
    "description",
    "transaction_type",
    "category",
    "amount",
    "payment_method",
]
OPTIONAL_COLUMNS = ["notes"]

HEADER_ALIASES = {
    "date": "transaction_date",
    "tx_date": "transaction_date",
    "transaction_date": "transaction_date",
    "desc": "description",
    "description": "description",
    "title": "description",
    "type": "transaction_type",
    "transaction_type": "transaction_type",
    "category": "category",
    "amount": "amount",
    "value": "amount",
    "payment_method": "payment_method",
    "payment": "payment_method",
    "method": "payment_method",
    "notes": "notes",
    "note": "notes",
    "remarks": "notes",
}

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y")


def _parse_date(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _normalize_type(raw: str) -> str | None:
    val = raw.strip().lower()
    if val in ("revenue", "income", "sale", "sales", "credit_inflow"):
        return "Revenue"
    if val in ("expense", "cost", "spend", "outflow"):
        return "Expense"
    return None


def _row_fingerprint(row: dict[str, Any]) -> tuple[str, str, str, str, float, str]:
    return (
        str(row["transaction_date"]).strip(),
        str(row["description"]).strip().lower(),
        str(row["transaction_type"]).strip(),
        str(row["category"]).strip().lower(),
        round(float(row["amount"]), 2),
        str(row["payment_method"]).strip().lower(),
    )


def validate_and_preview_csv(
    csv_text: str,
    conn: sqlite3.Connection,
) -> dict[str, Any]:
    """Validate CSV columns, types, missing values, and duplicates without mutating DB."""
    if not csv_text or not csv_text.strip():
        return {
            "ok": False,
            "error": "Uploaded CSV file is empty.",
            "missing_columns": REQUIRED_COLUMNS,
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "valid_rows": [],
            "errors": [],
            "duplicates": [],
        }

    # Strip UTF-8 BOM if present
    cleaned_text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(cleaned_text))
    if not reader.fieldnames:
        return {
            "ok": False,
            "error": "CSV header row could not be read.",
            "missing_columns": REQUIRED_COLUMNS,
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "valid_rows": [],
            "errors": [],
            "duplicates": [],
        }

    normalized_headers: dict[str, str] = {}
    for col in reader.fieldnames:
        if col is None:
            continue
        key = col.strip().lower().replace(" ", "_")
        canonical = HEADER_ALIASES.get(key, key)
        normalized_headers[col] = canonical

    present_canonical = set(normalized_headers.values())
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in present_canonical]
    if missing_cols:
        return {
            "ok": False,
            "error": f"Missing required CSV column(s): {', '.join(missing_cols)}",
            "missing_columns": missing_cols,
            "detected_columns": list(present_canonical),
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "duplicate_count": 0,
            "valid_rows": [],
            "errors": [],
            "duplicates": [],
        }

    existing_fps = {
        _row_fingerprint(dict(r))
        for r in conn.execute(
            """
            SELECT transaction_date, description, transaction_type, category, amount, payment_method
            FROM transactions
            """
        ).fetchall()
    }
    seen_in_file: set[tuple[str, str, str, str, float, str]] = set()

    valid_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    total_rows = 0

    for line_num, raw_row in enumerate(reader, start=2):
        # Skip completely blank lines
        if all((v is None or str(v).strip() == "") for v in raw_row.values()):
            continue

        total_rows += 1
        mapped: dict[str, str] = {}
        for orig_col, val in raw_row.items():
            if orig_col is None:
                continue
            canon = normalized_headers.get(orig_col, orig_col.strip().lower())
            mapped[canon] = (val or "").strip()

        row_issues: list[str] = []

        # Missing required fields check
        for req in REQUIRED_COLUMNS:
            if not mapped.get(req):
                row_issues.append(f"Missing '{req}'")

        parsed_date = _parse_date(mapped.get("transaction_date", ""))
        if mapped.get("transaction_date") and not parsed_date:
            row_issues.append(f"Invalid date '{mapped.get('transaction_date')}' (use YYYY-MM-DD)")

        norm_type = _normalize_type(mapped.get("transaction_type", ""))
        if mapped.get("transaction_type") and not norm_type:
            row_issues.append(
                f"Invalid transaction_type '{mapped.get('transaction_type')}' (must be Revenue or Expense)"
            )

        raw_amt = mapped.get("amount", "").replace(",", "").replace("₹", "").replace("$", "").strip()
        parsed_amt: float | None = None
        if raw_amt:
            try:
                parsed_amt = float(raw_amt)
                if parsed_amt <= 0:
                    row_issues.append("Amount must be greater than zero")
            except ValueError:
                row_issues.append(f"Non-numeric amount '{mapped.get('amount')}'")

        if row_issues:
            errors.append(
                {
                    "row_number": line_num,
                    "raw": mapped,
                    "reason": "; ".join(row_issues),
                }
            )
            continue

        clean_row = {
            "row_number": line_num,
            "transaction_date": parsed_date,
            "description": mapped["description"],
            "transaction_type": norm_type,
            "category": mapped["category"],
            "amount": round(float(parsed_amt), 2),
            "payment_method": mapped["payment_method"],
            "notes": mapped.get("notes", ""),
        }

        fp = _row_fingerprint(clean_row)
        if fp in existing_fps:
            duplicates.append(
                {
                    "row_number": line_num,
                    "record": clean_row,
                    "reason": "Already exists in database",
                }
            )
            continue
        if fp in seen_in_file:
            duplicates.append(
                {
                    "row_number": line_num,
                    "record": clean_row,
                    "reason": "Duplicate row inside uploaded CSV",
                }
            )
            continue

        seen_in_file.add(fp)
        valid_rows.append(clean_row)

    return {
        "ok": True,
        "missing_columns": [],
        "total_rows": total_rows,
        "valid_count": len(valid_rows),
        "invalid_count": len(errors),
        "duplicate_count": len(duplicates),
        "valid_rows": valid_rows,
        "errors": errors,
        "duplicates": duplicates,
    }


def commit_csv_rows(conn: sqlite3.Connection, valid_rows: list[dict[str, Any]]) -> int:
    """Insert validated CSV rows into SQLite inside a single transaction."""
    if not valid_rows:
        return 0
    conn.executemany(
        """
        INSERT INTO transactions (
            transaction_date, description, transaction_type,
            category, amount, payment_method, notes
        ) VALUES (
            :transaction_date, :description, :transaction_type,
            :category, :amount, :payment_method, :notes
        )
        """,
        valid_rows,
    )
    conn.commit()
    return len(valid_rows)
