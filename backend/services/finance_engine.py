"""Core financial analytics, KPI, time-series, and forecasting engine powered by Pandas & NumPy."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from backend.utils.dates import (
    current_and_previous_month_bounds,
    resolve_date_range,
    resolve_previous_period,
)
from backend.utils.formatting import pct_change, safe_div
from database.seed_data import EXPENSE_CATEGORIES


NON_CASH_TOKENS = (
    "receivable",
    "payable",
    "deferred",
    "accrued",
    "supplier credit",
    "store credit",
    "on credit",
)


def is_cash_payment(payment_method: str | None) -> bool:
    """Distinguish cash-settled payment methods from deferred/credit accrual entries."""
    pm = str(payment_method or "").strip().lower()
    if pm == "credit":
        return False
    return not any(tok in pm for tok in NON_CASH_TOKENS)


def _clean_float(val: Any, decimals: int = 2) -> float:
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return 0.0
    return round(float(val), decimals)


def load_transactions_df(
    conn: sqlite3.Connection,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    """Load transactions from SQLite into a typed Pandas DataFrame."""
    query = """
        SELECT id, transaction_date, description, transaction_type,
               category, amount, payment_method, notes
        FROM transactions
        WHERE 1=1
    """
    params: list[Any] = []
    if start_date is not None:
        query += " AND transaction_date >= ?"
        params.append(start_date.isoformat())
    if end_date is not None:
        query += " AND transaction_date <= ?"
        params.append(end_date.isoformat())
    query += " ORDER BY transaction_date ASC, id ASC"

    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "transaction_date",
                "date_dt",
                "month",
                "description",
                "transaction_type",
                "category",
                "amount",
                "payment_method",
                "notes",
                "is_cash_settled",
            ]
        )

    df = pd.DataFrame(rows)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["date_dt"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).copy()
    df["month"] = df["date_dt"].dt.strftime("%Y-%m")
    df["is_cash_settled"] = df["payment_method"].apply(is_cash_payment)
    return df


def get_business_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, business_name, currency, is_demo_data, created_at FROM business_settings ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if not row:
        return {
            "id": 1,
            "business_name": "SMART MART RETAIL STORE",
            "currency": "INR",
            "is_demo_data": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return {
        "id": row["id"],
        "business_name": row["business_name"],
        "currency": row["currency"],
        "is_demo_data": bool(row["is_demo_data"]),
        "created_at": row["created_at"],
    }


def compute_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Compute core financial KPIs and cash-basis vs accrual metrics safely."""
    if df.empty:
        return {
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "net_profit": 0.0,
            "profit_margin": 0.0,
            "expense_ratio": 0.0,
            "total_sales_transactions": 0,
            "total_expense_transactions": 0,
            "total_transactions": 0,
            "cash_inflow": 0.0,
            "cash_outflow": 0.0,
            "cash_flow": 0.0,
            "accrual_receivables": 0.0,
            "accrual_payables": 0.0,
            "avg_transaction_value": 0.0,
            "median_transaction_value": 0.0,
            "std_transaction_value": 0.0,
        }

    rev_df = df[df["transaction_type"] == "Revenue"]
    exp_df = df[df["transaction_type"] == "Expense"]

    total_rev = float(rev_df["amount"].sum()) if not rev_df.empty else 0.0
    total_exp = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
    net_profit = total_rev - total_exp
    profit_margin = safe_div(net_profit, total_rev, 0.0) * 100.0
    expense_ratio = safe_div(total_exp, total_rev, 0.0) * 100.0

    cash_in = float(rev_df[rev_df["is_cash_settled"]]["amount"].sum()) if not rev_df.empty else 0.0
    cash_out = float(exp_df[exp_df["is_cash_settled"]]["amount"].sum()) if not exp_df.empty else 0.0
    cash_flow = cash_in - cash_out

    accrual_rec = float(rev_df[~rev_df["is_cash_settled"]]["amount"].sum()) if not rev_df.empty else 0.0
    accrual_pay = float(exp_df[~exp_df["is_cash_settled"]]["amount"].sum()) if not exp_df.empty else 0.0

    rev_amounts = rev_df["amount"].to_numpy(dtype=float) if not rev_df.empty else np.array([], dtype=float)
    avg_tx = float(np.mean(rev_amounts)) if rev_amounts.size > 0 else 0.0
    med_tx = float(np.median(rev_amounts)) if rev_amounts.size > 0 else 0.0
    std_tx = float(np.std(rev_amounts, ddof=0)) if rev_amounts.size > 0 else 0.0

    return {
        "total_revenue": _clean_float(total_rev),
        "total_expenses": _clean_float(total_exp),
        "net_profit": _clean_float(net_profit),
        "profit_margin": _clean_float(profit_margin),
        "expense_ratio": _clean_float(expense_ratio),
        "total_sales_transactions": int(len(rev_df)),
        "total_expense_transactions": int(len(exp_df)),
        "total_transactions": int(len(df)),
        "cash_inflow": _clean_float(cash_in),
        "cash_outflow": _clean_float(cash_out),
        "cash_flow": _clean_float(cash_flow),
        "accrual_receivables": _clean_float(accrual_rec),
        "accrual_payables": _clean_float(accrual_pay),
        "avg_transaction_value": _clean_float(avg_tx),
        "median_transaction_value": _clean_float(med_tx),
        "std_transaction_value": _clean_float(std_tx),
    }


def build_kpi_comparison(
    current: dict[str, Any],
    previous: dict[str, Any],
    comparison_label: str,
) -> dict[str, Any]:
    """Attach period-over-period change percentages and directional indicators."""
    metrics = [
        ("total_revenue", "higher_is_better"),
        ("total_expenses", "lower_is_better"),
        ("net_profit", "higher_is_better"),
        ("profit_margin", "higher_is_better"),
        ("total_sales_transactions", "higher_is_better"),
        ("cash_flow", "higher_is_better"),
    ]
    cards: dict[str, Any] = {}
    for key, polarity in metrics:
        cur_val = current[key]
        prev_val = previous[key]
        if key == "profit_margin":
            # Percentage-point change when baseline margin is near zero; relative % if non-zero
            change_pct = pct_change(cur_val, prev_val)
            delta_abs = _clean_float(cur_val - prev_val)
        else:
            change_pct = pct_change(cur_val, prev_val)
            delta_abs = _clean_float(cur_val - prev_val)

        if delta_abs > 0:
            trend = "up"
            is_favorable = polarity == "higher_is_better"
        elif delta_abs < 0:
            trend = "down"
            is_favorable = polarity == "lower_is_better"
        else:
            trend = "flat"
            is_favorable = True

        cards[key] = {
            "value": cur_val,
            "previous_value": prev_val,
            "delta": delta_abs,
            "change_pct": change_pct,
            "trend": trend,
            "is_favorable": is_favorable,
            "comparison_label": comparison_label,
        }
    return cards


def _aggregate_bucket_series(df: pd.DataFrame, bucket_col: str, label_fn) -> list[dict[str, Any]]:
    if df.empty:
        return []

    buckets = sorted(df[bucket_col].unique())
    series: list[dict[str, Any]] = []
    for b in buckets:
        sub = df[df[bucket_col] == b]
        rev = float(sub[sub["transaction_type"] == "Revenue"]["amount"].sum())
        exp = float(sub[sub["transaction_type"] == "Expense"]["amount"].sum())
        net = rev - exp
        margin = safe_div(net, rev, 0.0) * 100.0
        cash_in = float(sub[(sub["transaction_type"] == "Revenue") & (sub["is_cash_settled"])]["amount"].sum())
        cash_out = float(sub[(sub["transaction_type"] == "Expense") & (sub["is_cash_settled"])]["amount"].sum())
        net_cash = cash_in - cash_out
        sales_count = int((sub["transaction_type"] == "Revenue").sum())

        series.append(
            {
                "period": str(b),
                "label": label_fn(str(b)),
                "revenue": _clean_float(rev),
                "expenses": _clean_float(exp),
                "net_profit": _clean_float(net),
                "profit_margin": _clean_float(margin),
                "cash_inflow": _clean_float(cash_in),
                "cash_outflow": _clean_float(cash_out),
                "net_cash_flow": _clean_float(net_cash),
                "sales_count": sales_count,
                "is_profitable": net >= 0,
                "is_negative_cash_flow": net_cash < 0,
            }
        )
    return series


def _format_month_label(ym: str) -> str:
    try:
        dt = datetime.strptime(ym, "%Y-%m")
        return dt.strftime("%b %Y")
    except ValueError:
        return ym


def build_monthly_series(df: pd.DataFrame) -> list[dict[str, Any]]:
    return _aggregate_bucket_series(df, "month", _format_month_label)


def build_adaptive_series(
    df: pd.DataFrame,
    start_date: date | None,
    end_date: date | None,
) -> tuple[str, list[dict[str, Any]]]:
    """Use daily/weekly buckets for short ranges and monthly buckets for multi-month ranges."""
    if df.empty:
        return "monthly", []

    s = start_date or df["date_dt"].min().date()
    e = end_date or df["date_dt"].max().date()
    span_days = (e - s).days + 1

    if span_days <= 14:
        work = df.copy()
        work["bucket"] = work["date_dt"].dt.strftime("%Y-%m-%d")
        series = _aggregate_bucket_series(
            work,
            "bucket",
            lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%d %b"),
        )
        return "daily", series

    if span_days <= 45:
        work = df.copy()
        # Week starting Monday
        work["week_start"] = (work["date_dt"] - pd.to_timedelta(work["date_dt"].dt.weekday, unit="D")).dt.strftime(
            "%Y-%m-%d"
        )
        series = _aggregate_bucket_series(
            work,
            "week_start",
            lambda d: "Wk " + datetime.strptime(d, "%Y-%m-%d").strftime("%d %b"),
        )
        return "weekly", series

    return "monthly", build_monthly_series(df)


def build_category_breakdowns(df: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return Revenue Distribution by category and Expense Breakdown by category."""
    if df.empty:
        return [], [
            {"category": cat, "amount": 0.0, "percentage": 0.0, "count": 0}
            for cat in EXPENSE_CATEGORIES
        ]

    rev_df = df[df["transaction_type"] == "Revenue"]
    total_rev = float(rev_df["amount"].sum()) if not rev_df.empty else 0.0
    rev_breakdown: list[dict[str, Any]] = []
    if not rev_df.empty:
        grouped = rev_df.groupby("category").agg(amount=("amount", "sum"), count=("id", "count")).reset_index()
        grouped = grouped.sort_values("amount", ascending=False)
        for _, row in grouped.iterrows():
            amt = float(row["amount"])
            rev_breakdown.append(
                {
                    "category": str(row["category"]),
                    "amount": _clean_float(amt),
                    "percentage": _clean_float(safe_div(amt, total_rev, 0.0) * 100.0),
                    "count": int(row["count"]),
                }
            )

    exp_df = df[df["transaction_type"] == "Expense"]
    total_exp = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
    exp_map: dict[str, dict[str, Any]] = {
        cat: {"category": cat, "amount": 0.0, "percentage": 0.0, "count": 0}
        for cat in EXPENSE_CATEGORIES
    }
    if not exp_df.empty:
        grouped = exp_df.groupby("category").agg(amount=("amount", "sum"), count=("id", "count")).reset_index()
        for _, row in grouped.iterrows():
            cat = str(row["category"])
            amt = float(row["amount"])
            exp_map[cat] = {
                "category": cat,
                "amount": _clean_float(amt),
                "percentage": _clean_float(safe_div(amt, total_exp, 0.0) * 100.0),
                "count": int(row["count"]),
            }

    exp_breakdown = sorted(exp_map.values(), key=lambda x: x["amount"], reverse=True)
    return rev_breakdown, exp_breakdown


def build_sales_performance(df: pd.DataFrame) -> dict[str, Any]:
    """Build Daily, Weekly, and Monthly sales trends and identify peak/low periods."""
    rev_df = df[df["transaction_type"] == "Revenue"].copy() if not df.empty else pd.DataFrame()
    if rev_df.empty:
        return {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "highlights": {"daily": None, "weekly": None, "monthly": None},
        }

    def summarize(series_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not series_rows:
            return None
        best = max(series_rows, key=lambda r: r["sales"])
        worst = min(series_rows, key=lambda r: r["sales"])
        avg_sales = float(np.mean([r["sales"] for r in series_rows]))
        return {
            "best": best,
            "worst": worst,
            "average": _clean_float(avg_sales),
        }

    # Daily
    rev_df["day_key"] = rev_df["date_dt"].dt.strftime("%Y-%m-%d")
    d_grp = rev_df.groupby("day_key").agg(sales=("amount", "sum"), transactions=("id", "count")).reset_index()
    d_grp = d_grp.sort_values("day_key")
    daily_rows = [
        {
            "period": row["day_key"],
            "label": datetime.strptime(row["day_key"], "%Y-%m-%d").strftime("%d %b %y"),
            "sales": _clean_float(row["sales"]),
            "transactions": int(row["transactions"]),
        }
        for _, row in d_grp.iterrows()
    ]

    # Weekly (Monday-based)
    rev_df["week_key"] = (
        rev_df["date_dt"] - pd.to_timedelta(rev_df["date_dt"].dt.weekday, unit="D")
    ).dt.strftime("%Y-%m-%d")
    w_grp = rev_df.groupby("week_key").agg(sales=("amount", "sum"), transactions=("id", "count")).reset_index()
    w_grp = w_grp.sort_values("week_key")
    weekly_rows = [
        {
            "period": row["week_key"],
            "label": "Wk " + datetime.strptime(row["week_key"], "%Y-%m-%d").strftime("%d %b"),
            "sales": _clean_float(row["sales"]),
            "transactions": int(row["transactions"]),
        }
        for _, row in w_grp.iterrows()
    ]

    # Monthly
    m_grp = rev_df.groupby("month").agg(sales=("amount", "sum"), transactions=("id", "count")).reset_index()
    m_grp = m_grp.sort_values("month")
    monthly_rows = [
        {
            "period": row["month"],
            "label": _format_month_label(row["month"]),
            "sales": _clean_float(row["sales"]),
            "transactions": int(row["transactions"]),
        }
        for _, row in m_grp.iterrows()
    ]

    return {
        "daily": daily_rows,
        "weekly": weekly_rows,
        "monthly": monthly_rows,
        "highlights": {
            "daily": summarize(daily_rows),
            "weekly": summarize(weekly_rows),
            "monthly": summarize(monthly_rows),
        },
    }


def compute_revenue_forecast(
    full_df: pd.DataFrame,
    horizon: int = 3,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Deterministic OLS linear regression + residual interval forecast for next 3 months."""
    ref = reference_date or date.today()
    if full_df.empty:
        return {
            "can_forecast": False,
            "reason": "No transaction records are available to generate a revenue forecast.",
            "disclaimer": "Forecasts are statistical estimates based on historical trends and are not guaranteed outcomes.",
            "historical": [],
            "forecast": [],
            "combined_series": [],
            "model_stats": None,
        }

    monthly = build_monthly_series(full_df)
    if not monthly:
        return {
            "can_forecast": False,
            "reason": "Insufficient monthly revenue history to fit a forecasting model.",
            "disclaimer": "Forecasts are statistical estimates based on historical trends and are not guaranteed outcomes.",
            "historical": [],
            "forecast": [],
            "combined_series": [],
            "model_stats": None,
        }

    current_ym = ref.strftime("%Y-%m")
    cur_dom_total = calendar.monthrange(ref.year, ref.month)[1]
    is_latest_partial = monthly[-1]["period"] == current_ym and ref.day < cur_dom_total

    # Exclude partial month-to-date bucket from regression fit so slope isn't artificially dragged down
    completed_months = monthly[:-1] if (is_latest_partial and len(monthly) > 2) else monthly

    if len(completed_months) < 2:
        return {
            "can_forecast": False,
            "reason": "At least 2 completed months of historical revenue are required for linear trend forecasting.",
            "disclaimer": "Forecasts are statistical estimates based on historical trends and are not guaranteed outcomes.",
            "historical": monthly,
            "forecast": [],
            "combined_series": [],
            "model_stats": None,
        }

    y = np.array([m["revenue"] for m in completed_months], dtype=float)
    x = np.arange(len(completed_months), dtype=float)

    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residuals = y - fitted
    std_err = float(np.sqrt(np.mean(residuals ** 2))) if len(residuals) > 0 else 0.0

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - safe_div(ss_res, ss_tot, 0.0) if ss_tot > 0 else 0.0

    last_completed_ym = completed_months[-1]["period"]
    last_yr, last_mo = map(int, last_completed_ym.split("-"))

    # If the latest month in monthly is partial MTD (e.g. Nov 1..11), forecast starts after current_ym
    # and we also compute full-month estimate for the partial month separately.
    start_offset = 2 if is_latest_partial else 1
    base_x = len(completed_months) - 1

    forecast_points: list[dict[str, Any]] = []
    for step in range(horizon):
        step_ahead = start_offset + step
        target_idx = (last_yr * 12 + (last_mo - 1)) + step_ahead
        f_yr, f_mo = target_idx // 12, (target_idx % 12) + 1
        f_ym = f"{f_yr:04d}-{f_mo:02d}"
        x_val = float(base_x + step_ahead)
        # Blend OLS trend with trailing 3-month baseline dampening for realistic small-business smoothing
        ols_pred = float(slope * x_val + intercept)
        recent_mean = float(np.mean(y[-min(3, len(y)):]))
        pred_rev = max(0.0, 0.75 * ols_pred + 0.25 * recent_mean)
        band = 1.28 * std_err * (1.0 + 0.1 * step)

        forecast_points.append(
            {
                "period": f_ym,
                "label": _format_month_label(f_ym),
                "forecast_revenue": _clean_float(pred_rev),
                "lower_bound": _clean_float(max(0.0, pred_rev - band)),
                "upper_bound": _clean_float(pred_rev + band),
                "ols_trend": _clean_float(max(0.0, ols_pred)),
            }
        )

    historical_out = [
        {
            "period": m["period"],
            "label": m["label"],
            "actual_revenue": m["revenue"],
            "trend_line": _clean_float(max(0.0, slope * idx + intercept)) if idx < len(completed_months) else None,
            "is_partial": (m["period"] == current_ym and is_latest_partial),
        }
        for idx, m in enumerate(monthly)
    ]

    combined_series = []
    for h in historical_out:
        combined_series.append(
            {
                "period": h["period"],
                "label": h["label"] + (" (MTD)" if h["is_partial"] else ""),
                "actual_revenue": h["actual_revenue"],
                "forecast_revenue": None,
                "lower_bound": None,
                "upper_bound": None,
                "trend_line": h["trend_line"],
                "is_forecast": False,
                "is_partial": h["is_partial"],
            }
        )
    for fp in forecast_points:
        combined_series.append(
            {
                "period": fp["period"],
                "label": fp["label"] + " (Est.)",
                "actual_revenue": None,
                "forecast_revenue": fp["forecast_revenue"],
                "lower_bound": fp["lower_bound"],
                "upper_bound": fp["upper_bound"],
                "trend_line": fp["ols_trend"],
                "is_forecast": True,
                "is_partial": False,
            }
        )

    return {
        "can_forecast": True,
        "method": "Ordinary Least Squares (OLS) Linear Trend + 3-Month Moving Average Smoothing",
        "disclaimer": (
            "Statistical Forecast Notice: Projections are deterministic estimates derived from historical "
            "completed monthly revenue using linear regression and trailing moving-average smoothing. "
            "Actual future results may vary due to seasonality, market shifts, and operational changes."
        ),
        "partial_month_excluded": current_ym if is_latest_partial else None,
        "historical": historical_out,
        "forecast": forecast_points,
        "combined_series": combined_series,
        "model_stats": {
            "completed_months_analyzed": len(completed_months),
            "monthly_slope": _clean_float(slope),
            "r_squared": _clean_float(max(0.0, min(1.0, r_squared)), 3),
            "residual_std_error": _clean_float(std_err),
            "avg_historical_revenue": _clean_float(float(np.mean(y))),
            "trend_direction": "upward" if slope > 500 else ("downward" if slope < -500 else "stable"),
        },
    }


def get_dashboard_payload(
    conn: sqlite3.Connection,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Assemble full Dashboard Overview payload with dynamic KPIs, comparisons, and charts."""
    ref = reference_date or date.today()
    s_dt, e_dt, period_label = resolve_date_range(period, start_date, end_date, ref)
    ps_dt, pe_dt, prev_label = resolve_previous_period(period, s_dt, e_dt, ref)

    df_cur = load_transactions_df(conn, s_dt, e_dt)
    df_prev = load_transactions_df(conn, ps_dt, pe_dt) if (ps_dt and pe_dt) else pd.DataFrame()

    cur_kpis = compute_kpis(df_cur)
    prev_kpis = compute_kpis(df_prev)
    kpi_cards = build_kpi_comparison(cur_kpis, prev_kpis, prev_label)

    # Always include explicit Current Month vs Previous Month snapshot (Section 3)
    (cm_s, cm_e), (pm_s, pm_e) = current_and_previous_month_bounds(ref)
    cm_kpis = compute_kpis(load_transactions_df(conn, cm_s, cm_e))
    pm_kpis = compute_kpis(load_transactions_df(conn, pm_s, pm_e))
    month_over_month = build_kpi_comparison(cm_kpis, pm_kpis, pm_s.strftime("%b %Y"))

    granularity, adaptive_series = build_adaptive_series(df_cur, s_dt, e_dt)
    monthly_series = build_monthly_series(df_cur)
    rev_dist, exp_breakdown = build_category_breakdowns(df_cur)
    sales_perf = build_sales_performance(df_cur)

    # Recent transactions inside filtered range
    recent_rows = []
    if not df_cur.empty:
        rec_df = df_cur.sort_values(["transaction_date", "id"], ascending=[False, False]).head(8)
        recent_rows = [
            {
                "id": int(r["id"]),
                "transaction_date": str(r["transaction_date"]),
                "description": str(r["description"]),
                "transaction_type": str(r["transaction_type"]),
                "category": str(r["category"]),
                "amount": _clean_float(r["amount"]),
                "payment_method": str(r["payment_method"]),
                "notes": str(r["notes"] or ""),
            }
            for _, r in rec_df.iterrows()
        ]

    settings = get_business_settings(conn)
    return {
        "settings": settings,
        "filter": {
            "period": (period or "this_year").lower(),
            "label": period_label,
            "start_date": s_dt.isoformat() if s_dt else None,
            "end_date": e_dt.isoformat() if e_dt else None,
            "comparison_label": prev_label,
            "current_month_label": cm_s.strftime("%b %Y (MTD)"),
            "previous_month_label": pm_s.strftime("%b %Y"),
        },
        "kpis": cur_kpis,
        "kpi_cards": kpi_cards,
        "month_comparison": {
            "current_month": cm_kpis,
            "previous_month": pm_kpis,
            "cards": month_over_month,
        },
        "charts": {
            "granularity": granularity,
            "revenue_vs_expenses": adaptive_series,
            "monthly_series": monthly_series,
            "revenue_distribution": rev_dist,
            "expense_breakdown": exp_breakdown,
            "cash_flow_series": adaptive_series,
            "sales_performance": sales_perf,
        },
        "recent_transactions": recent_rows,
        "is_empty": df_cur.empty,
    }


def get_analytics_payload(
    conn: sqlite3.Connection,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Assemble Business Performance Analysis (10 metrics) + Forecast + Visualizations."""
    ref = reference_date or date.today()
    s_dt, e_dt, period_label = resolve_date_range(period, start_date, end_date, ref)
    ps_dt, pe_dt, prev_label = resolve_previous_period(period, s_dt, e_dt, ref)

    df_cur = load_transactions_df(conn, s_dt, e_dt)
    df_prev = load_transactions_df(conn, ps_dt, pe_dt) if (ps_dt and pe_dt) else pd.DataFrame()
    df_all = load_transactions_df(conn, None, None)

    cur_kpis = compute_kpis(df_cur)
    prev_kpis = compute_kpis(df_prev)

    rev_growth = pct_change(cur_kpis["total_revenue"], prev_kpis["total_revenue"])
    exp_growth = pct_change(cur_kpis["total_expenses"], prev_kpis["total_expenses"])

    monthly_cur = build_monthly_series(df_cur)
    granularity, adaptive_series = build_adaptive_series(df_cur, s_dt, e_dt)
    rev_dist, exp_breakdown = build_category_breakdowns(df_cur)
    sales_perf = build_sales_performance(df_cur)
    forecast = compute_revenue_forecast(df_all, horizon=3, reference_date=ref)

    # Monthly MoM growth series for Pandas/NumPy trend inspection
    mom_rates = []
    for idx in range(1, len(monthly_cur)):
        prev_m = monthly_cur[idx - 1]
        cur_m = monthly_cur[idx]
        mom_rates.append(
            {
                "period": cur_m["period"],
                "label": cur_m["label"],
                "revenue_growth_pct": pct_change(cur_m["revenue"], prev_m["revenue"]),
                "expense_growth_pct": pct_change(cur_m["expenses"], prev_m["expenses"]),
            }
        )

    profit_cash_gap = _clean_float(cur_kpis["net_profit"] - cur_kpis["cash_flow"])

    return {
        "settings": get_business_settings(conn),
        "filter": {
            "period": (period or "this_year").lower(),
            "label": period_label,
            "start_date": s_dt.isoformat() if s_dt else None,
            "end_date": e_dt.isoformat() if e_dt else None,
            "comparison_label": prev_label,
        },
        "performance_metrics": {
            "gross_revenue": cur_kpis["total_revenue"],
            "total_expenses": cur_kpis["total_expenses"],
            "net_profit": cur_kpis["net_profit"],
            "profit_margin": cur_kpis["profit_margin"],
            "expense_ratio": cur_kpis["expense_ratio"],
            "revenue_growth_rate": rev_growth,
            "expense_growth_rate": exp_growth,
            "avg_transaction_value": cur_kpis["avg_transaction_value"],
            "median_transaction_value": cur_kpis["median_transaction_value"],
            "std_transaction_value": cur_kpis["std_transaction_value"],
            "cash_inflow": cur_kpis["cash_inflow"],
            "cash_outflow": cur_kpis["cash_outflow"],
            "net_cash_flow": cur_kpis["cash_flow"],
            "accrual_receivables": cur_kpis["accrual_receivables"],
            "accrual_payables": cur_kpis["accrual_payables"],
            "profit_vs_cash_variance": profit_cash_gap,
            "operating_expense_breakdown": exp_breakdown,
            "monthly_cash_flow": monthly_cur,
        },
        "charts": {
            "granularity": granularity,
            "adaptive_series": adaptive_series,
            "monthly_series": monthly_cur,
            "mom_growth_series": mom_rates,
            "revenue_distribution": rev_dist,
            "expense_breakdown": exp_breakdown,
            "sales_performance": sales_perf,
        },
        "forecast": forecast,
        "is_empty": df_cur.empty,
    }
