"""Dynamic Business Intelligence & Insights generator computed strictly from SQLite records."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date
from typing import Any

import pandas as pd

from backend.services.finance_engine import (
    build_category_breakdowns,
    build_monthly_series,
    compute_kpis,
    compute_revenue_forecast,
    get_business_settings,
    load_transactions_df,
)
from backend.utils.dates import resolve_date_range, resolve_previous_period
from backend.utils.formatting import format_currency, pct_change


def _insight(
    category: str,
    analytics_type: str,
    title: str,
    message: str,
    metric_value: str | None = None,
    severity: str = "info",
) -> dict[str, Any]:
    return {
        "category": category,  # positive | warning | optimization | growth | recommendation
        "analytics_type": analytics_type,  # Descriptive | Diagnostic | Comparative | Trend | Predictive
        "title": title,
        "message": message,
        "metric_value": metric_value,
        "severity": severity,  # success | warning | danger | info
    }


def generate_business_insights(
    conn: sqlite3.Connection,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Generate structured, data-grounded financial insights for the active filter."""
    ref = reference_date or date.today()
    settings = get_business_settings(conn)
    currency = settings["currency"]

    s_dt, e_dt, period_label = resolve_date_range(period, start_date, end_date, ref)
    ps_dt, pe_dt, prev_label = resolve_previous_period(period, s_dt, e_dt, ref)

    df_cur = load_transactions_df(conn, s_dt, e_dt)
    df_prev = load_transactions_df(conn, ps_dt, pe_dt) if (ps_dt and pe_dt) else pd.DataFrame()
    df_all = load_transactions_df(conn, None, None)

    if df_cur.empty:
        return {
            "settings": settings,
            "filter": {
                "period": (period or "this_year").lower(),
                "label": period_label,
                "start_date": s_dt.isoformat() if s_dt else None,
                "end_date": e_dt.isoformat() if e_dt else None,
            },
            "summary": {
                "total_insights": 1,
                "positive_count": 0,
                "warning_count": 1,
                "optimization_count": 0,
            },
            "insights": [
                _insight(
                    "warning",
                    "Descriptive",
                    "No Transactions Found in Selected Range",
                    (
                        f"No revenue or expense records exist for '{period_label}'. "
                        "Widen the date filter, add transactions, upload a CSV file, or restore demonstration data in Settings."
                    ),
                    metric_value="0 records",
                    severity="warning",
                )
            ],
            "is_empty": True,
        }

    kpis = compute_kpis(df_cur)
    prev_kpis = compute_kpis(df_prev)
    monthly = build_monthly_series(df_cur)
    all_monthly = build_monthly_series(df_all)
    rev_dist, exp_breakdown = build_category_breakdowns(df_cur)
    forecast = compute_revenue_forecast(df_all, horizon=3, reference_date=ref)

    insights: list[dict[str, Any]] = []

    # 1. Comparative Period Revenue & Profit Growth
    rev_pct = pct_change(kpis["total_revenue"], prev_kpis["total_revenue"])
    exp_pct = pct_change(kpis["total_expenses"], prev_kpis["total_expenses"])
    if rev_pct is not None:
        if rev_pct >= 5:
            insights.append(
                _insight(
                    "growth",
                    "Comparative",
                    f"Revenue Expanded by {rev_pct:.1f}%",
                    (
                        f"Total revenue for {period_label} reached {format_currency(kpis['total_revenue'], currency)}, "
                        f"increasing by {rev_pct:.1f}% compared with {prev_label} "
                        f"({format_currency(prev_kpis['total_revenue'], currency)})."
                    ),
                    metric_value=f"+{rev_pct:.1f}%",
                    severity="success",
                )
            )
        elif rev_pct <= -5:
            insights.append(
                _insight(
                    "warning",
                    "Comparative",
                    f"Revenue Contraction of {abs(rev_pct):.1f}%",
                    (
                        f"Revenue in {period_label} ({format_currency(kpis['total_revenue'], currency)}) "
                        f"is {abs(rev_pct):.1f}% below {prev_label} ({format_currency(prev_kpis['total_revenue'], currency)})."
                    ),
                    metric_value=f"{rev_pct:.1f}%",
                    severity="warning",
                )
            )
        else:
            insights.append(
                _insight(
                    "growth",
                    "Comparative",
                    "Steady Revenue Trajectory",
                    (
                        f"Revenue for {period_label} ({format_currency(kpis['total_revenue'], currency)}) "
                        f"remained stable ({rev_pct:+.1f}%) relative to {prev_label}."
                    ),
                    metric_value=f"{rev_pct:+.1f}%",
                    severity="info",
                )
            )

    # Check latest two completed calendar months for clean MoM revenue & profit signals
    cur_ym = ref.strftime("%Y-%m")
    cur_dom_total = calendar.monthrange(ref.year, ref.month)[1]
    completed_monthly = (
        all_monthly[:-1]
        if (all_monthly and all_monthly[-1]["period"] == cur_ym and ref.day < cur_dom_total and len(all_monthly) >= 3)
        else all_monthly
    )
    if len(completed_monthly) >= 2:
        m_last = completed_monthly[-1]
        m_prev = completed_monthly[-2]
        mom_rev = pct_change(m_last["revenue"], m_prev["revenue"])
        if mom_rev is not None and abs(mom_rev) >= 8:
            cat = "positive" if mom_rev > 0 else "warning"
            sev = "success" if mom_rev > 0 else "warning"
            direction = "increased" if mom_rev > 0 else "decreased"
            insights.append(
                _insight(
                    cat,
                    "Comparative",
                    f"Latest Completed Month ({m_last['label']}) Revenue {direction.title()}",
                    (
                        f"In {m_last['label']}, monthly revenue {direction} by {abs(mom_rev):.1f}% "
                        f"to {format_currency(m_last['revenue'], currency)} compared with "
                        f"{m_prev['label']} ({format_currency(m_prev['revenue'], currency)})."
                    ),
                    metric_value=f"{mom_rev:+.1f}%",
                    severity=sev,
                )
            )

    # 2. Consecutive Profit Decline / Growth Streak (Trend Analysis)
    if len(monthly) >= 3:
        profits = [m["net_profit"] for m in monthly]
        decline_streak = 0
        max_decline_end = None
        cur_streak = 0
        for i in range(1, len(profits)):
            if profits[i] < profits[i - 1]:
                cur_streak += 1
                if cur_streak >= decline_streak:
                    decline_streak = cur_streak
                    max_decline_end = monthly[i]["label"]
            else:
                cur_streak = 0
        if decline_streak >= 2:
            insights.append(
                _insight(
                    "warning",
                    "Trend",
                    f"Net Profit Declined for {decline_streak} Consecutive Months",
                    (
                        f"Monthly net profit experienced a {decline_streak}-month consecutive contraction "
                        f"ending in {max_decline_end}, signaling margin compression or rising operating costs."
                    ),
                    metric_value=f"{decline_streak} mo streak",
                    severity="danger",
                )
            )

    # 3. Loss-Making Months & Diagnostic Root Cause
    loss_months = [m for m in monthly if m["net_profit"] < 0]
    if loss_months:
        worst_loss = min(loss_months, key=lambda m: m["net_profit"])
        loss_df = df_cur[df_cur["month"] == worst_loss["period"]]
        loss_exp_df = loss_df[loss_df["transaction_type"] == "Expense"]
        top_driver_note = ""
        if not loss_exp_df.empty:
            top_cat_row = loss_exp_df.groupby("category")["amount"].sum().sort_values(ascending=False)
            top_cat = str(top_cat_row.index[0])
            top_amt = float(top_cat_row.iloc[0])
            top_driver_note = (
                f" Primary cost driver was {top_cat} at {format_currency(top_amt, currency)}."
            )
        month_names = ", ".join(m["label"] for m in loss_months[:3])
        insights.append(
            _insight(
                "warning",
                "Diagnostic",
                f"{len(loss_months)} Loss-Making Period(s) Identified",
                (
                    f"Operating losses occurred in {month_names}, with the sharpest deficit in "
                    f"{worst_loss['label']} ({format_currency(worst_loss['net_profit'], currency)})."
                    f"{top_driver_note}"
                ),
                metric_value=format_currency(worst_loss["net_profit"], currency),
                severity="danger",
            )
        )

    # 4. Cash Flow Health & Profit-vs-Cash Divergence
    neg_cash_months = [m for m in monthly if m["net_cash_flow"] < 0]
    if neg_cash_months:
        divergent = [m for m in neg_cash_months if m["net_profit"] > 0]
        worst_cf = min(neg_cash_months, key=lambda m: m["net_cash_flow"])
        if divergent:
            d_m = divergent[-1]
            insights.append(
                _insight(
                    "warning",
                    "Diagnostic",
                    f"Positive Profit but Negative Cash Flow in {d_m['label']}",
                    (
                        f"Although {d_m['label']} recorded an accounting net profit of "
                        f"{format_currency(d_m['net_profit'], currency)}, actual net cash flow was "
                        f"{format_currency(d_m['net_cash_flow'], currency)} due to cash-settled inventory outflows "
                        "and/or uncollected credit receivables."
                    ),
                    metric_value=format_currency(d_m["net_cash_flow"], currency),
                    severity="warning",
                )
            )
        else:
            months_list = ", ".join(m["label"] for m in neg_cash_months[:3])
            insights.append(
                _insight(
                    "warning",
                    "Descriptive",
                    f"Negative Cash Flow in {len(neg_cash_months)} Month(s)",
                    (
                        f"Cash outflows exceeded cash inflows during {months_list}, reaching "
                        f"{format_currency(worst_cf['net_cash_flow'], currency)} in {worst_cf['label']}."
                    ),
                    metric_value=format_currency(worst_cf["net_cash_flow"], currency),
                    severity="danger",
                )
            )
    elif kpis["cash_flow"] > 0:
        insights.append(
            _insight(
                "positive",
                "Descriptive",
                "Positive Net Cash Flow Position",
                (
                    f"Cash inflows ({format_currency(kpis['cash_inflow'], currency)}) exceeded cash outflows "
                    f"({format_currency(kpis['cash_outflow'], currency)}), generating "
                    f"{format_currency(kpis['cash_flow'], currency)} in net cash liquidity."
                ),
                metric_value=format_currency(kpis["cash_flow"], currency),
                severity="success",
            )
        )

    # 5. Expense Breakdown & Optimization Opportunities
    non_zero_exp = [e for e in exp_breakdown if e["amount"] > 0]
    if non_zero_exp and kpis["total_expenses"] > 0:
        top_exp = non_zero_exp[0]
        insights.append(
            _insight(
                "optimization",
                "Diagnostic",
                f"{top_exp['category']} is the Largest Expense Category",
                (
                    f"{top_exp['category']} accounts for {top_exp['percentage']:.1f}% "
                    f"({format_currency(top_exp['amount'], currency)}) of total operating expenses "
                    f"in {period_label}. A 5% efficiency gain in {top_exp['category']} would add "
                    f"{format_currency(top_exp['amount'] * 0.05, currency)} directly to net profit."
                ),
                metric_value=f"{top_exp['percentage']:.1f}%",
                severity="info",
            )
        )

        # Check Marketing / Fixed Overhead ratios dynamically
        mkt = next((e for e in non_zero_exp if e["category"].lower() == "marketing"), None)
        if mkt and mkt["percentage"] >= 8.0:
            insights.append(
                _insight(
                    "optimization",
                    "Descriptive",
                    f"Marketing Spend Represents {mkt['percentage']:.1f}% of Expenses",
                    (
                        f"Marketing expenditures totaled {format_currency(mkt['amount'], currency)} "
                        f"({mkt['percentage']:.1f}% of expenses). Evaluate campaign ROI by comparing "
                        "high-marketing months against same-month retail footfall."
                    ),
                    metric_value=f"{mkt['percentage']:.1f}%",
                    severity="info",
                )
            )

    if exp_pct is not None and exp_pct > 10 and (rev_pct is None or exp_pct > rev_pct + 5):
        insights.append(
            _insight(
                "warning",
                "Comparative",
                "Expenses Growing Faster Than Revenue",
                (
                    f"Operating expenses rose {exp_pct:.1f}% versus {prev_label}, outpacing revenue "
                    f"growth ({rev_pct:+.1f}% if measured). Tighter supplier credit terms or batch "
                    "purchasing controls are recommended."
                )
                if rev_pct is not None
                else (
                    f"Operating expenses rose {exp_pct:.1f}% versus {prev_label}, increasing cost pressure."
                ),
                metric_value=f"+{exp_pct:.1f}%",
                severity="warning",
            )
        )

    # 6. Top Revenue Category & Mix Observation
    if rev_dist:
        top_rev = rev_dist[0]
        insights.append(
            _insight(
                "growth",
                "Descriptive",
                f"{top_rev['category']} Drives {top_rev['percentage']:.1f}% of Revenue",
                (
                    f"{top_rev['category']} is the primary revenue engine at "
                    f"{format_currency(top_rev['amount'], currency)} across {top_rev['count']} sales entries. "
                    + (
                        f"Cross-selling higher-margin {rev_dist[1]['category']} ({rev_dist[1]['percentage']:.1f}%) "
                        "can reduce single-category reliance."
                        if len(rev_dist) > 1
                        else ""
                    )
                ),
                metric_value=f"{top_rev['percentage']:.1f}%",
                severity="info",
            )
        )

    # 7. Profit Margin Health & Profitability Recommendation
    if kpis["total_revenue"] > 0:
        pm = kpis["profit_margin"]
        er = kpis["expense_ratio"]
        if pm >= 20:
            insights.append(
                _insight(
                    "positive",
                    "Descriptive",
                    "Strong Operating Profit Margin",
                    (
                        f"The business achieved a {pm:.1f}% net profit margin (expense ratio {er:.1f}%), "
                        f"generating {format_currency(kpis['net_profit'], currency)} in net profit."
                    ),
                    metric_value=f"{pm:.1f}%",
                    severity="success",
                )
            )
        elif pm >= 10:
            insights.append(
                _insight(
                    "recommendation",
                    "Diagnostic",
                    "Healthy Margin with Room for Cost Optimization",
                    (
                        f"Net profit margin stands at {pm:.1f}% with an expense ratio of {er:.1f}%. "
                        f"Improving average transaction value above {format_currency(kpis['avg_transaction_value'], currency)} "
                        "via bundle offers can lift margins past 20%."
                    ),
                    metric_value=f"{pm:.1f}%",
                    severity="info",
                )
            )
        else:
            insights.append(
                _insight(
                    "recommendation",
                    "Diagnostic",
                    "Low Profit Margin — Cost & Pricing Review Needed",
                    (
                        f"Net profit margin is {pm:.1f}% (expense ratio {er:.1f}%). "
                        "Prioritize renegotiating bulk inventory discounts, trimming discretionary miscellaneous costs, "
                        "and focusing shelf space on higher-margin product categories."
                    ),
                    metric_value=f"{pm:.1f}%",
                    severity="warning" if pm >= 0 else "danger",
                )
            )

    # 8. Predictive Forecast Insight
    if forecast.get("can_forecast") and forecast.get("forecast"):
        stats = forecast["model_stats"]
        next_m = forecast["forecast"][0]
        slope_str = format_currency(abs(stats["monthly_slope"]), currency)
        trend_word = (
            f"upward at +{slope_str}/month"
            if stats["monthly_slope"] >= 0
            else f"downward at -{slope_str}/month"
        )
        insights.append(
            _insight(
                "recommendation",
                "Predictive",
                f"Projected Revenue for {next_m['label']}: {format_currency(next_m['forecast_revenue'], currency)}",
                (
                    f"Based on {stats['completed_months_analyzed']} completed months of history, "
                    f"revenue trend is {trend_word}. Estimated next-month revenue falls between "
                    f"{format_currency(next_m['lower_bound'], currency)} and "
                    f"{format_currency(next_m['upper_bound'], currency)} (statistical estimate, not guaranteed)."
                ),
                metric_value=format_currency(next_m["forecast_revenue"], currency),
                severity="success" if stats["monthly_slope"] >= 0 else "warning",
            )
        )

    return {
        "settings": settings,
        "filter": {
            "period": (period or "this_year").lower(),
            "label": period_label,
            "start_date": s_dt.isoformat() if s_dt else None,
            "end_date": e_dt.isoformat() if e_dt else None,
            "comparison_label": prev_label,
        },
        "summary": {
            "total_insights": len(insights),
            "positive_count": sum(1 for i in insights if i["category"] in ("positive", "growth")),
            "warning_count": sum(1 for i in insights if i["category"] == "warning"),
            "optimization_count": sum(1 for i in insights if i["category"] in ("optimization", "recommendation")),
        },
        "insights": insights,
        "is_empty": False,
    }
