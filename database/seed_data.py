"""Deterministic 12-month demonstration dataset generator for SMART MART RETAIL STORE."""

from __future__ import annotations

import calendar
import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Any


EXPENSE_CATEGORIES = [
    "Rent",
    "Salaries",
    "Marketing",
    "Inventory",
    "Utilities",
    "Transportation",
    "Miscellaneous",
]

REVENUE_CATEGORIES = [
    "Groceries & Staples",
    "Beverages & Snacks",
    "Personal Care & Home",
    "Electronics & Accessories",
    "Bulk & Wholesale Orders",
    "Home Delivery & Services",
]

CASH_PAYMENT_METHODS = {
    "Cash",
    "UPI",
    "Debit Card",
    "Bank Transfer",
    "Cheque",
    "Card",
    "Net Banking",
}

ACCRUAL_PAYMENT_METHODS = {
    "Credit (Receivable)",
    "Credit (Payable)",
    "Supplier Credit",
    "Credit",
}


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + delta
    return idx // 12, (idx % 12) + 1


def _clamp_day(year: int, month: int, day: int, max_day: int | None = None) -> date:
    last_dom = calendar.monthrange(year, month)[1]
    limit = min(last_dom, max_day) if max_day is not None else last_dom
    return date(year, month, min(max(1, day), limit))


def generate_demo_transactions(reference_date: date | None = None) -> list[dict[str, Any]]:
    """Generate 12+ months of realistic retail transactions ending on reference_date.

    Includes profitable peaks, two deliberate loss-making months, and months where
    accounting profit diverges from cash flow due to upfront inventory cash outflows
    and B2B credit receivables/payables.
    """
    ref = reference_date or date.today()
    rows: list[dict[str, Any]] = []

    # 12 completed historical months plus current MTD month (total spans >= 12 full months)
    # Month offset -12 .. 0 relative to ref's month
    # Seasonal profiles tuned for an Indian neighborhood retail mart (INR):
    # (rev_mult, inv_mult, mkt_mult, extra_expense, credit_rev, supplier_credit, label)
    monthly_profiles = {
        -12: (0.98, 0.95, 0.90, 0, 0, 0, "Late Autumn Baseline"),
        -11: (1.26, 1.18, 1.35, 8500, 22000, 0, "Year-End Festive Peak"),
        -10: (1.02, 0.96, 0.95, 4200, 0, 18000, "New Year Steady"),
        -9: (0.94, 0.90, 0.85, 3800, 0, 0, "Short Month Consolidation"),
        -8: (0.80, 1.24, 1.15, 36000, 62000, 0, "Off-Season Slowdown & Annual Restock"),  # Loss + neg cash flow
        -7: (1.06, 1.00, 1.00, 4500, 15000, 15000, "Spring & Summer Ramp-Up"),
        -6: (1.16, 1.05, 1.10, 5200, 0, 0, "Summer Peak Demand"),
        -5: (0.97, 0.98, 1.05, 11000, 18000, 0, "Early Monsoon & Fleet Service"),
        -4: (0.78, 1.16, 1.40, 42000, 48000, 0, "Peak Monsoon Dip & Store Repairs"),  # Loss + neg cash flow
        -3: (1.12, 1.32, 1.15, 7500, 88000, 0, "Pre-Festive Stocking & B2B Credit"),  # Profitable, negative cash flow
        -2: (1.22, 1.10, 1.25, 6500, 25000, 20000, "Festive Buildup"),
        -1: (1.46, 1.22, 1.45, 9500, 32000, 0, "Diwali Mega Retail Peak"),
        0: (1.18, 1.04, 1.10, 5000, 18000, 0, "Current Month Momentum"),
    }

    for offset in range(-12, 1):
        yr, mo = _add_months(ref.year, ref.month, offset)
        last_dom = calendar.monthrange(yr, mo)[1]
        is_current_month = offset == 0
        max_day = ref.day if is_current_month else last_dom

        min_day = 1

        rev_m, inv_m, mkt_m, extra_misc, credit_sale_amt, supplier_credit_amt, season_note = (
            monthly_profiles[offset]
        )

        def add_tx(
            day: int,
            desc: str,
            tx_type: str,
            cat: str,
            amt: float,
            method: str,
            notes: str = "",
        ) -> None:
            if day < min_day or day > max_day:
                return
            tx_date = _clamp_day(yr, mo, day, max_day)
            rows.append(
                {
                    "transaction_date": tx_date.isoformat(),
                    "description": desc,
                    "transaction_type": tx_type,
                    "category": cat,
                    "amount": round(float(amt), 2),
                    "payment_method": method,
                    "notes": notes,
                }
            )

        # --- REVENUE TRANSACTIONS ---
        # Week 1..4 retail POS batches across product categories
        weekly_sales = [
            (3, "Groceries & Staples - Week 1 POS Sales", "Groceries & Staples", 48500 * rev_m, "UPI", f"{season_note}"),
            (5, "Beverages & Snacks Counter Sales", "Beverages & Snacks", 22400 * rev_m, "Cash", "Walk-in retail"),
            (7, "Personal Care & Household Counter Sales", "Personal Care & Home", 26800 * rev_m, "Debit Card", "Weekend basket"),
            (10, "Groceries & Staples - Week 2 POS Sales", "Groceries & Staples", 52200 * rev_m, "UPI", "Regular household restock"),
            (12, "Home Delivery & Subscription Orders", "Home Delivery & Services", 18900 * rev_m, "UPI", "Local apartment deliveries"),
            (14, "Small Appliances & Accessories Sales", "Electronics & Accessories", 24600 * rev_m, "Debit Card", "Kitchen & home gadgets"),
            (17, "Groceries & Staples - Week 3 POS Sales", "Groceries & Staples", 54100 * rev_m, "Cash", "Mid-month retail"),
            (19, "Beverages, Dairy & Confectionery Batch", "Beverages & Snacks", 25600 * rev_m, "UPI", "High-margin impulse sales"),
            (22, "Personal Care & Cleaning Supplies Batch", "Personal Care & Home", 29400 * rev_m, "UPI", "Brand promotions"),
            (25, "Groceries & Staples - Week 4 POS Sales", "Groceries & Staples", 56800 * rev_m, "Cash", "Month-end pantry buying"),
            (27, "Corporate & Apartment Bulk Wholesale Order", "Bulk & Wholesale Orders", 44000 * rev_m, "Bank Transfer", "Bulk invoiced order"),
            (29, "Home Delivery & Express Fulfilment Fees", "Home Delivery & Services", 16200 * rev_m, "UPI", "Delivery & convenience"),
        ]
        for d, desc, cat, amt, method, note in weekly_sales:
            add_tx(d, desc, "Revenue", cat, amt, method, note)

        # Ensure Today / This Week has rich granular activity for current month
        if is_current_month:
            today_day = ref.day
            if today_day >= 6:
                add_tx(
                    6,
                    "Wedding Season & Festive Bulk Grocery Order",
                    "Revenue",
                    "Bulk & Wholesale Orders",
                    68000,
                    "Bank Transfer",
                    "Early-month institutional & event catering supply",
                )
            # Add transactions spanning the last 7 days up to exact reference_date
            recent_days = [
                (max(1, today_day - 6), "Morning Fresh Produce & Staples Sales", "Groceries & Staples", 19800, "UPI"),
                (max(1, today_day - 4), "Weekend Snacks & Beverage Rush", "Beverages & Snacks", 16400, "Cash"),
                (max(1, today_day - 2), "Personal Care & Cosmetics Counter", "Personal Care & Home", 14200, "Debit Card"),
                (max(1, today_day - 1), "Express Local Delivery Batch", "Home Delivery & Services", 11800, "UPI"),
                (today_day, "Today Retail POS Counter Settlement", "Groceries & Staples", 24600, "UPI"),
                (today_day, "Today Walk-in Cash Register Close", "Beverages & Snacks", 12900, "Cash"),
            ]
            for d, desc, cat, amt, method in recent_days:
                add_tx(d, desc, "Revenue", cat, amt, method, "Current week retail settlement")

            # Today / recent expenses
            add_tx(max(1, today_day - 3), "Fresh Dairy & Bakery Daily Stock", "Expense", "Inventory", 18500, "Bank Transfer", "Local vendor replenishment")
            add_tx(today_day, "Local Van Delivery Fuel & Dispatch", "Expense", "Transportation", 2450, "Cash", "Same-day delivery run")

        # B2B Credit Receivables (Revenue recorded on accrual basis, non-cash until collected)
        if credit_sale_amt > 0:
            c_day = min(18, max_day)
            add_tx(
                c_day,
                "B2B Institutional Grocery Supply (Net-30 Credit)",
                "Revenue",
                "Bulk & Wholesale Orders",
                credit_sale_amt,
                "Credit (Receivable)",
                "Accrual revenue; payment receivable next billing cycle",
            )

        # --- EXPENSE TRANSACTIONS ---
        # Fixed monthly overheads early in month
        add_tx(2, "Store Premises & Warehouse Monthly Rent", "Expense", "Rent", 58000, "Bank Transfer", "Commercial lease payment")
        add_tx(5, "Store Staff & Cashier Monthly Salaries", "Expense", "Salaries", 94000, "Bank Transfer", "Payroll for 6 staff members")
        add_tx(8, "Electricity, Cold Storage & Internet Bills", "Expense", "Utilities", 16800 + (abs(offset) % 3) * 1400, "UPI", "Commercial tariff + refrigeration")

        # Variable operating expenses
        add_tx(4, "Wholesale FMCG & Grain Inventory Procurement", "Expense", "Inventory", 92000 * inv_m, "Bank Transfer", "Primary distributor restock")
        add_tx(11, "Local Flyer, Digital & In-Store Promo Campaign", "Expense", "Marketing", 21500 * mkt_m, "UPI", "Seasonal promotional spend")
        add_tx(15, "Mid-Month Beverages & Personal Care Restock", "Expense", "Inventory", 64000 * inv_m, "Cheque", "Secondary vendor invoice")
        add_tx(18, "Inbound Freight & Local Delivery Logistics", "Expense", "Transportation", 13200 + (abs(offset) % 2) * 1800, "UPI", "Goods carrier & fuel")
        add_tx(23, "Packaging Bags, POS Rolls & Store Supplies", "Expense", "Miscellaneous", 7800, "Cash", "Consumables & stationery")

        if supplier_credit_amt > 0:
            add_tx(
                20,
                "Distributor Stock Purchase on 30-Day Credit",
                "Expense",
                "Inventory",
                supplier_credit_amt,
                "Credit (Payable)",
                "Accrued expense; cash settlement due next month",
            )

        if extra_misc > 0:
            e_day = min(21, max_day)
            if extra_misc >= 30000:
                add_tx(
                    e_day,
                    "Store Maintenance, Waterproofing & Compliance Audit",
                    "Expense",
                    "Miscellaneous",
                    extra_misc,
                    "Bank Transfer",
                    "One-time operational & facility expenditure",
                )
            else:
                add_tx(
                    e_day,
                    "Festive Display Setup & Extra Part-Time Helpers",
                    "Expense",
                    "Marketing",
                    extra_misc,
                    "Cash",
                    "Seasonal storefront merchandising",
                )

        # Late month inventory top-up on completed months
        if not is_current_month:
            add_tx(26, "Month-End Fast-Moving Inventory Top-Up", "Expense", "Inventory", 36000 * inv_m, "Bank Transfer", "Buffer stock")

    # Sort deterministically by date ascending, then Revenue before Expense
    rows.sort(key=lambda r: (r["transaction_date"], 0 if r["transaction_type"] == "Revenue" else 1, r["description"]))
    return rows


def write_sample_csvs(sample_dir: Path, reference_date: date | None = None) -> tuple[Path, Path]:
    """Write the 12-month demo dataset CSV and a clean CSV import template."""
    sample_dir.mkdir(parents=True, exist_ok=True)
    rows = generate_demo_transactions(reference_date=reference_date)

    dataset_path = sample_dir / "smart_mart_sample_data.csv"
    fieldnames = [
        "transaction_date",
        "description",
        "transaction_type",
        "category",
        "amount",
        "payment_method",
        "notes",
    ]
    with dataset_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    ref = reference_date or date.today()
    template_path = sample_dir / "csv_import_template.csv"
    template_rows = [
        {
            "transaction_date": ref.isoformat(),
            "description": "Weekend Retail Counter Sales",
            "transaction_type": "Revenue",
            "category": "Groceries & Staples",
            "amount": "24500.00",
            "payment_method": "UPI",
            "notes": "Sample revenue entry",
        },
        {
            "transaction_date": (ref - timedelta(days=1)).isoformat(),
            "description": "Electricity & Cold Storage Bill",
            "transaction_type": "Expense",
            "category": "Utilities",
            "amount": "8200.00",
            "payment_method": "Bank Transfer",
            "notes": "Sample expense entry",
        },
    ]
    with template_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(template_rows)

    return dataset_path, template_path
