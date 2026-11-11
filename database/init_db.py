"""Database initialization and reset helpers for FINTRACK."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from database.seed_data import generate_demo_transactions, write_sample_csvs


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "fintrack.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SAMPLE_DIR = BASE_DIR / "sample_data"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database(
    db_path: Path | None = None,
    reset: bool = False,
    seed_demo: bool = True,
    reference_date: date | None = None,
) -> dict[str, int]:
    """Initialize SQLite schema and optionally populate demonstration dataset."""
    target = db_path or DB_PATH
    conn = get_connection(target)
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)

        # Ensure backward-compatible migration if an older DB lacked is_demo_data
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(business_settings)").fetchall()}
        if "is_demo_data" not in cols:
            conn.execute(
                "ALTER TABLE business_settings ADD COLUMN is_demo_data INTEGER NOT NULL DEFAULT 1"
            )

        if reset:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM business_settings")

        settings_count = conn.execute("SELECT COUNT(*) AS cnt FROM business_settings").fetchone()["cnt"]
        if settings_count == 0:
            conn.execute(
                """
                INSERT INTO business_settings (business_name, currency, is_demo_data)
                VALUES (?, ?, ?)
                """,
                ("SMART MART RETAIL STORE", "INR", 1 if seed_demo else 0),
            )

        tx_count = conn.execute("SELECT COUNT(*) AS cnt FROM transactions").fetchone()["cnt"]
        inserted = 0
        if seed_demo and tx_count == 0:
            demo_rows = generate_demo_transactions(reference_date=reference_date)
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
                demo_rows,
            )
            conn.execute("UPDATE business_settings SET is_demo_data = 1")
            inserted = len(demo_rows)

        conn.commit()
        total_tx = conn.execute("SELECT COUNT(*) AS cnt FROM transactions").fetchone()["cnt"]
    finally:
        conn.close()

    # Keep CSV artifacts aligned whenever demo DB is freshly initialized or reset
    if seed_demo:
        write_sample_csvs(SAMPLE_DIR, reference_date=reference_date)

    return {"inserted": inserted, "total_transactions": total_tx}


if __name__ == "__main__":
    result = init_database(reset=True, seed_demo=True)
    print(f"Database initialized at {DB_PATH} -> {result}")
