"""FINTRACK – Small Business Financial Intelligence Flask REST API."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

# Ensure project root is importable whether launched via `python backend/app.py` or `flask`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.csv_service import commit_csv_rows, validate_and_preview_csv
from backend.services.finance_engine import (
    get_analytics_payload,
    get_business_settings,
    get_dashboard_payload,
)
from backend.services.insights_engine import generate_business_insights
from backend.services.report_service import (
    export_transactions_csv,
    generate_pdf_report,
    generate_report_data,
)
from backend.utils.dates import resolve_date_range
from backend.utils.formatting import CURRENCY_CONFIG
from database.init_db import DB_PATH, SAMPLE_DIR, get_connection, init_database
from database.seed_data import EXPENSE_CATEGORIES, REVENUE_CATEGORIES, write_sample_csvs


def create_app(db_path: Path | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    active_db_path = db_path or DB_PATH

    if not active_db_path.exists():
        init_database(db_path=active_db_path, reset=False, seed_demo=True)
    else:
        # Ensure schema/migrations & settings exist without overwriting existing rows
        init_database(db_path=active_db_path, reset=False, seed_demo=False)

    def db_conn():
        return get_connection(active_db_path)

    def _validate_transaction_payload(payload: dict) -> tuple[dict | None, str | None]:
        if not isinstance(payload, dict):
            return None, "Request body must be a JSON object."

        tx_date = str(payload.get("transaction_date", "")).strip()
        description = str(payload.get("description", "")).strip()
        tx_type = str(payload.get("transaction_type", "")).strip()
        category = str(payload.get("category", "")).strip()
        payment_method = str(payload.get("payment_method", "")).strip()
        notes = str(payload.get("notes", "") or "").strip()

        if not tx_date:
            return None, "Transaction date is required."
        try:
            date.fromisoformat(tx_date)
        except ValueError:
            return None, "Transaction date must use YYYY-MM-DD format."

        if not description:
            return None, "Description is required."
        if len(description) > 200:
            return None, "Description cannot exceed 200 characters."

        if tx_type not in ("Revenue", "Expense"):
            return None, "Transaction type must be 'Revenue' or 'Expense'."

        if not category:
            return None, "Category is required."

        if not payment_method:
            return None, "Payment method is required."

        try:
            amount = float(payload.get("amount"))
        except (TypeError, ValueError):
            return None, "Amount must be a valid positive number."
        if amount <= 0:
            return None, "Amount must be greater than zero."

        return {
            "transaction_date": tx_date,
            "description": description,
            "transaction_type": tx_type,
            "category": category,
            "amount": round(amount, 2),
            "payment_method": payment_method,
            "notes": notes,
        }, None

    @app.errorhandler(ValueError)
    def handle_value_error(err: ValueError):
        return jsonify({"error": str(err)}), 400

    @app.errorhandler(404)
    def handle_not_found(_err):
        return jsonify({"error": "Requested API endpoint was not found."}), 404

    @app.errorhandler(500)
    def handle_internal_error(err):
        return jsonify({"error": f"Internal server error: {err}"}), 500

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "FINTRACK API", "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.get("/api/dashboard")
    def dashboard():
        period = request.args.get("period", "this_year")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        conn = db_conn()
        try:
            payload = get_dashboard_payload(conn, period=period, start_date=start_date, end_date=end_date)
            return jsonify(payload)
        finally:
            conn.close()

    @app.get("/api/transactions")
    def list_transactions():
        period = request.args.get("period", "all")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        search = request.args.get("search", "").strip()
        tx_type = request.args.get("transaction_type", "all").strip()
        category = request.args.get("category", "all").strip()
        payment_method = request.args.get("payment_method", "all").strip()
        sort_by = request.args.get("sort_by", "transaction_date")
        sort_order = request.args.get("sort_order", "desc").lower()

        try:
            page = max(1, int(request.args.get("page", 1)))
            per_page = min(500, max(1, int(request.args.get("per_page", 25))))
        except ValueError:
            return jsonify({"error": "Invalid pagination parameters."}), 400

        allowed_sort = {
            "id": "id",
            "transaction_date": "transaction_date",
            "amount": "amount",
            "category": "category",
            "transaction_type": "transaction_type",
        }
        sort_col = allowed_sort.get(sort_by, "transaction_date")
        order_sql = "ASC" if sort_order == "asc" else "DESC"

        s_dt, e_dt, period_label = resolve_date_range(period, start_date, end_date)

        where_clauses = ["1=1"]
        params: list = []
        if s_dt is not None:
            where_clauses.append("transaction_date >= ?")
            params.append(s_dt.isoformat())
        if e_dt is not None:
            where_clauses.append("transaction_date <= ?")
            params.append(e_dt.isoformat())
        if tx_type and tx_type.lower() != "all":
            where_clauses.append("transaction_type = ?")
            params.append(tx_type)
        if category and category.lower() != "all":
            where_clauses.append("category = ?")
            params.append(category)
        if payment_method and payment_method.lower() != "all":
            where_clauses.append("payment_method = ?")
            params.append(payment_method)
        if search:
            like = f"%{search}%"
            where_clauses.append(
                "(description LIKE ? OR category LIKE ? OR notes LIKE ? OR payment_method LIKE ? OR CAST(id AS TEXT) = ?)"
            )
            params.extend([like, like, like, like, search])

        where_sql = " AND ".join(where_clauses)
        conn = db_conn()
        try:
            total_count = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM transactions WHERE {where_sql}",
                params,
            ).fetchone()["cnt"]

            agg = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(CASE WHEN transaction_type = 'Revenue' THEN amount ELSE 0 END), 0) AS total_revenue,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Expense' THEN amount ELSE 0 END), 0) AS total_expenses
                FROM transactions
                WHERE {where_sql}
                """,
                params,
            ).fetchone()

            offset = (page - 1) * per_page
            rows = conn.execute(
                f"""
                SELECT id, transaction_date, description, transaction_type,
                       category, amount, payment_method, notes
                FROM transactions
                WHERE {where_sql}
                ORDER BY {sort_col} {order_sql}, id {order_sql}
                LIMIT ? OFFSET ?
                """,
                params + [per_page, offset],
            ).fetchall()

            categories_in_db = [
                r["category"]
                for r in conn.execute("SELECT DISTINCT category FROM transactions ORDER BY category ASC").fetchall()
            ]
            methods_in_db = [
                r["payment_method"]
                for r in conn.execute(
                    "SELECT DISTINCT payment_method FROM transactions ORDER BY payment_method ASC"
                ).fetchall()
            ]

            return jsonify(
                {
                    "transactions": [dict(r) for r in rows],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total_count": total_count,
                        "total_pages": max(1, (total_count + per_page - 1) // per_page),
                    },
                    "totals": {
                        "revenue": round(float(agg["total_revenue"]), 2),
                        "expenses": round(float(agg["total_expenses"]), 2),
                        "net": round(float(agg["total_revenue"]) - float(agg["total_expenses"]), 2),
                    },
                    "filter": {
                        "period": period,
                        "label": period_label,
                    },
                    "metadata": {
                        "revenue_categories": REVENUE_CATEGORIES,
                        "expense_categories": EXPENSE_CATEGORIES,
                        "all_categories": sorted(set(REVENUE_CATEGORIES + EXPENSE_CATEGORIES + categories_in_db)),
                        "payment_methods": sorted(
                            set(
                                [
                                    "Cash",
                                    "UPI",
                                    "Debit Card",
                                    "Bank Transfer",
                                    "Cheque",
                                    "Credit (Receivable)",
                                    "Credit (Payable)",
                                ]
                                + methods_in_db
                            )
                        ),
                    },
                }
            )
        finally:
            conn.close()

    @app.post("/api/transactions")
    def create_transaction():
        data, err = _validate_transaction_payload(request.get_json(silent=True))
        if err:
            return jsonify({"error": err}), 400

        conn = db_conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO transactions (
                    transaction_date, description, transaction_type,
                    category, amount, payment_method, notes
                ) VALUES (
                    :transaction_date, :description, :transaction_type,
                    :category, :amount, :payment_method, :notes
                )
                """,
                data,
            )
            conn.commit()
            created = conn.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return jsonify({"message": "Transaction added successfully.", "transaction": dict(created)}), 201
        finally:
            conn.close()

    @app.put("/api/transactions/<int:tx_id>")
    def update_transaction(tx_id: int):
        data, err = _validate_transaction_payload(request.get_json(silent=True))
        if err:
            return jsonify({"error": err}), 400

        conn = db_conn()
        try:
            existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            if not existing:
                return jsonify({"error": f"Transaction #{tx_id} not found."}), 404

            conn.execute(
                """
                UPDATE transactions
                SET transaction_date = :transaction_date,
                    description = :description,
                    transaction_type = :transaction_type,
                    category = :category,
                    amount = :amount,
                    payment_method = :payment_method,
                    notes = :notes
                WHERE id = :id
                """,
                {**data, "id": tx_id},
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            return jsonify({"message": "Transaction updated successfully.", "transaction": dict(updated)})
        finally:
            conn.close()

    @app.delete("/api/transactions/<int:tx_id>")
    def delete_transaction(tx_id: int):
        conn = db_conn()
        try:
            existing = conn.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            if not existing:
                return jsonify({"error": f"Transaction #{tx_id} not found."}), 404
            conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
            conn.commit()
            return jsonify({"message": f"Transaction #{tx_id} deleted successfully.", "id": tx_id})
        finally:
            conn.close()

    @app.post("/api/upload")
    def upload_csv():
        action = "preview"
        replace_existing = False
        csv_text = ""

        if "file" in request.files:
            uploaded = request.files["file"]
            action = request.form.get("action", "preview").strip().lower()
            replace_existing = request.form.get("replace_existing", "false").lower() == "true"
            try:
                csv_text = uploaded.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                return jsonify({"error": "CSV file must be UTF-8 encoded."}), 400
        else:
            body = request.get_json(silent=True) or {}
            action = str(body.get("action", "preview")).strip().lower()
            replace_existing = bool(body.get("replace_existing", False))
            csv_text = str(body.get("csv_text", ""))

        if action not in ("preview", "import"):
            return jsonify({"error": "Action must be 'preview' or 'import'."}), 400

        conn = db_conn()
        try:
            if replace_existing and action == "import":
                # Validate against empty state when user explicitly chooses replace mode
                conn.execute("DELETE FROM transactions")
                conn.execute("UPDATE business_settings SET is_demo_data = 0")

            preview = validate_and_preview_csv(csv_text, conn)
            if not preview["ok"]:
                conn.rollback()
                return jsonify(preview), 400

            if action == "preview":
                return jsonify(preview)

            inserted = commit_csv_rows(conn, preview["valid_rows"])
            if inserted > 0:
                if replace_existing:
                    conn.execute("UPDATE business_settings SET is_demo_data = 0")
                    conn.commit()
            return jsonify(
                {
                    "ok": True,
                    "action": "import",
                    "inserted_count": inserted,
                    "skipped_invalid_count": preview["invalid_count"],
                    "skipped_duplicate_count": preview["duplicate_count"],
                    "errors": preview["errors"],
                    "duplicates": preview["duplicates"],
                    "message": (
                        f"Imported {inserted} transaction(s). "
                        f"Skipped {preview['duplicate_count']} duplicate(s) and {preview['invalid_count']} invalid row(s)."
                    ),
                }
            )
        finally:
            conn.close()

    @app.get("/api/upload/template")
    def download_csv_template():
        _, template_path = write_sample_csvs(SAMPLE_DIR)
        csv_content = template_path.read_text(encoding="utf-8")
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=fintrack_import_template.csv"},
        )

    @app.get("/api/analytics")
    def analytics():
        period = request.args.get("period", "this_year")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        conn = db_conn()
        try:
            return jsonify(
                get_analytics_payload(conn, period=period, start_date=start_date, end_date=end_date)
            )
        finally:
            conn.close()

    @app.get("/api/insights")
    def insights():
        period = request.args.get("period", "this_year")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        conn = db_conn()
        try:
            return jsonify(
                generate_business_insights(conn, period=period, start_date=start_date, end_date=end_date)
            )
        finally:
            conn.close()

    @app.get("/api/reports")
    def reports():
        report_type = request.args.get("report_type", "monthly")
        period_key = request.args.get("period_key")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        conn = db_conn()
        try:
            return jsonify(
                generate_report_data(
                    conn,
                    report_type=report_type,
                    period_key=period_key,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        finally:
            conn.close()

    @app.get("/api/export/csv")
    def export_csv():
        report_type = request.args.get("report_type")
        period_key = request.args.get("period_key")
        period = request.args.get("period", "all")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        tx_type = request.args.get("transaction_type")
        category = request.args.get("category")
        search = request.args.get("search")

        conn = db_conn()
        try:
            if report_type:
                from backend.services.report_service import resolve_report_period

                s_dt, e_dt, _, slug = resolve_report_period(report_type, period_key, start_date, end_date)
                csv_data = export_transactions_csv(
                    conn,
                    period="custom",
                    start_date=s_dt.isoformat(),
                    end_date=e_dt.isoformat(),
                )
                filename = f"fintrack_{slug}_transactions.csv"
            else:
                csv_data = export_transactions_csv(
                    conn,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    transaction_type=tx_type,
                    category=category,
                    search=search,
                )
                filename = "fintrack_transactions_export.csv"

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        finally:
            conn.close()

    @app.get("/api/export/pdf")
    def export_pdf():
        report_type = request.args.get("report_type", "monthly")
        period_key = request.args.get("period_key")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        conn = db_conn()
        try:
            pdf_bytes, filename = generate_pdf_report(
                conn,
                report_type=report_type,
                period_key=period_key,
                start_date=start_date,
                end_date=end_date,
                save_to_disk=True,
            )
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        finally:
            conn.close()

    @app.get("/api/settings")
    def get_settings():
        conn = db_conn()
        try:
            settings = get_business_settings(conn)
            stats = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_transactions,
                    MIN(transaction_date) AS earliest_date,
                    MAX(transaction_date) AS latest_date,
                    COUNT(DISTINCT substr(transaction_date, 1, 7)) AS months_covered
                FROM transactions
                """
            ).fetchone()
            return jsonify(
                {
                    "settings": settings,
                    "supported_currencies": list(CURRENCY_CONFIG.values()),
                    "dataset_info": {
                        "total_transactions": int(stats["total_transactions"]),
                        "earliest_date": stats["earliest_date"],
                        "latest_date": stats["latest_date"],
                        "months_covered": int(stats["months_covered"]),
                        "database_path": str(active_db_path),
                    },
                }
            )
        finally:
            conn.close()

    @app.put("/api/settings")
    def update_settings():
        body = request.get_json(silent=True) or {}
        business_name = str(body.get("business_name", "")).strip()
        currency = str(body.get("currency", "INR")).strip().upper()

        if not business_name:
            return jsonify({"error": "Business name cannot be empty."}), 400
        if len(business_name) > 120:
            return jsonify({"error": "Business name cannot exceed 120 characters."}), 400
        if currency not in CURRENCY_CONFIG:
            return jsonify({"error": f"Unsupported currency '{currency}'."}), 400

        conn = db_conn()
        try:
            row = conn.execute("SELECT id FROM business_settings ORDER BY id ASC LIMIT 1").fetchone()
            if row:
                conn.execute(
                    "UPDATE business_settings SET business_name = ?, currency = ? WHERE id = ?",
                    (business_name, currency, row["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO business_settings (business_name, currency, is_demo_data) VALUES (?, ?, 1)",
                    (business_name, currency),
                )
            conn.commit()
            return jsonify(
                {
                    "message": "Business settings saved successfully.",
                    "settings": get_business_settings(conn),
                }
            )
        finally:
            conn.close()

    @app.post("/api/settings/reset-demo")
    def reset_demo_data():
        result = init_database(db_path=active_db_path, reset=True, seed_demo=True)
        conn = db_conn()
        try:
            return jsonify(
                {
                    "message": (
                        f"Demonstration dataset restored for SMART MART RETAIL STORE "
                        f"({result['total_transactions']} transactions across 12+ months)."
                    ),
                    "settings": get_business_settings(conn),
                    "total_transactions": result["total_transactions"],
                }
            )
        finally:
            conn.close()

    @app.post("/api/settings/clear-data")
    def clear_all_data():
        conn = db_conn()
        try:
            conn.execute("DELETE FROM transactions")
            conn.execute("UPDATE business_settings SET is_demo_data = 0")
            conn.commit()
            return jsonify({"message": "All transactions cleared from database.", "total_transactions": 0})
        finally:
            conn.close()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=False)
