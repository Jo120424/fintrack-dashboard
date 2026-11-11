"""Financial report builder, CSV exporter, and ReportLab PDF summary generator."""

from __future__ import annotations

import calendar
import csv
import io
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.services.finance_engine import (
    build_adaptive_series,
    build_category_breakdowns,
    build_monthly_series,
    compute_kpis,
    get_business_settings,
    load_transactions_df,
)
from backend.utils.dates import resolve_date_range
from backend.utils.formatting import format_currency, get_currency_symbol, pct_change


BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def _register_pdf_font() -> tuple[str, str, bool]:
    """Register a Unicode-capable system font for ₹ symbol; fall back gracefully to Helvetica."""
    candidates = [
        ("SegoeUI", "SegoeUI-Bold", Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
        ("ArialUni", "ArialUni-Bold", Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        ("DejaVuSans", "DejaVuSans-Bold", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    for reg_name, bold_name, reg_path, bold_path in candidates:
        if reg_path.exists():
            try:
                if reg_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(reg_name, str(reg_path)))
                if bold_path.exists() and bold_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
                else:
                    bold_name = reg_name
                return reg_name, bold_name, True
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold", False


def _pdf_money(value: float, currency_code: str, unicode_ok: bool) -> str:
    text = format_currency(value, currency_code, decimals=2)
    if not unicode_ok and currency_code.upper() == "INR":
        return text.replace("₹", "INR ")
    return text


def resolve_report_period(
    report_type: str | None,
    period_key: str | None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> tuple[date, date, str, str]:
    """Resolve monthly (YYYY-MM), quarterly (YYYY-Qn), annual (YYYY), or custom report bounds."""
    ref = reference_date or date.today()
    rtype = (report_type or "monthly").strip().lower()

    if rtype == "custom" and start_date and end_date:
        s_dt, e_dt, label = resolve_date_range("custom", start_date, end_date, ref)
        return s_dt, e_dt, f"Custom ({label})", f"custom_{s_dt.isoformat()}_{e_dt.isoformat()}"

    if rtype == "monthly":
        key = (period_key or ref.strftime("%Y-%m")).strip()
        try:
            yr, mo = map(int, key.split("-"))
            last_dom = calendar.monthrange(yr, mo)[1]
            s_dt = date(yr, mo, 1)
            e_dt = date(yr, mo, last_dom)
            return s_dt, e_dt, f"Monthly Report — {s_dt.strftime('%B %Y')}", f"monthly_{key}"
        except ValueError as exc:
            raise ValueError("Monthly report period_key must be YYYY-MM.") from exc

    if rtype == "quarterly":
        default_q = f"{ref.year}-Q{((ref.month - 1) // 3) + 1}"
        key = (period_key or default_q).strip().upper()
        try:
            yr_str, q_str = key.split("-Q")
            yr = int(yr_str)
            q = int(q_str)
            if q not in (1, 2, 3, 4):
                raise ValueError
            start_mo = (q - 1) * 3 + 1
            end_mo = q * 3
            s_dt = date(yr, start_mo, 1)
            e_dt = date(yr, end_mo, calendar.monthrange(yr, end_mo)[1])
            return s_dt, e_dt, f"Quarterly Report — Q{q} {yr}", f"quarterly_{yr}_Q{q}"
        except ValueError as exc:
            raise ValueError("Quarterly report period_key must be YYYY-Qn (e.g., 2026-Q3).") from exc

    if rtype == "annual":
        key = (period_key or str(ref.year)).strip()
        try:
            yr = int(key)
            s_dt = date(yr, 1, 1)
            e_dt = date(yr, 12, 31)
            return s_dt, e_dt, f"Annual Report — FY {yr}", f"annual_{yr}"
        except ValueError as exc:
            raise ValueError("Annual report period_key must be YYYY.") from exc

    raise ValueError(f"Unsupported report_type '{report_type}'.")


def get_available_report_periods(conn: sqlite3.Connection, reference_date: date | None = None) -> dict[str, list[dict[str, str]]]:
    ref = reference_date or date.today()
    rows = conn.execute(
        "SELECT DISTINCT substr(transaction_date, 1, 7) AS ym FROM transactions ORDER BY ym DESC"
    ).fetchall()
    months = []
    quarters_seen: dict[str, dict[str, str]] = {}
    years_seen: dict[str, dict[str, str]] = {}

    for r in rows:
        ym = r["ym"]
        try:
            yr, mo = map(int, ym.split("-"))
        except ValueError:
            continue
        dt = date(yr, mo, 1)
        months.append({"value": ym, "label": dt.strftime("%B %Y")})

        q = ((mo - 1) // 3) + 1
        q_key = f"{yr}-Q{q}"
        if q_key not in quarters_seen:
            quarters_seen[q_key] = {"value": q_key, "label": f"Q{q} {yr}"}

        y_key = str(yr)
        if y_key not in years_seen:
            years_seen[y_key] = {"value": y_key, "label": f"Calendar Year {yr}"}

    if not months:
        cur_ym = ref.strftime("%Y-%m")
        months = [{"value": cur_ym, "label": ref.strftime("%B %Y")}]
        q = ((ref.month - 1) // 3) + 1
        quarters_seen = {f"{ref.year}-Q{q}": {"value": f"{ref.year}-Q{q}", "label": f"Q{q} {ref.year}"}}
        years_seen = {str(ref.year): {"value": str(ref.year), "label": f"Calendar Year {ref.year}"}}

    return {
        "months": months,
        "quarters": list(quarters_seen.values()),
        "years": list(years_seen.values()),
    }


def _build_report_observations(
    kpis: dict[str, Any],
    prev_kpis: dict[str, Any],
    rev_dist: list[dict[str, Any]],
    exp_breakdown: list[dict[str, Any]],
    currency: str,
    period_title: str,
    chart_series: list[dict[str, Any]],
) -> list[str]:
    if kpis["total_transactions"] == 0:
        return [f"No recorded financial transactions exist for {period_title}."]

    obs: list[str] = []
    rev_chg = pct_change(kpis["total_revenue"], prev_kpis["total_revenue"])
    rev_note = (
        f" ({rev_chg:+.1f}% vs prior equivalent period)"
        if rev_chg is not None
        else ""
    )
    obs.append(
        f"Gross revenue totaled {format_currency(kpis['total_revenue'], currency)} across "
        f"{kpis['total_sales_transactions']} sales transactions{rev_note}."
    )
    obs.append(
        f"Total operating expenses stood at {format_currency(kpis['total_expenses'], currency)}, "
        f"resulting in an expense ratio of {kpis['expense_ratio']:.1f}%."
    )

    profit_status = "net profit" if kpis["net_profit"] >= 0 else "net operating loss"
    obs.append(
        f"The business generated a {profit_status} of {format_currency(kpis['net_profit'], currency)} "
        f"with a {kpis['profit_margin']:.1f}% profit margin."
    )

    cf_status = "positive" if kpis["cash_flow"] >= 0 else "negative"
    obs.append(
        f"Cash-settled liquidity showed {cf_status} net cash flow of "
        f"{format_currency(kpis['cash_flow'], currency)} "
        f"(inflows {format_currency(kpis['cash_inflow'], currency)} vs outflows "
        f"{format_currency(kpis['cash_outflow'], currency)})."
    )

    if rev_dist:
        obs.append(
            f"Top revenue stream was {rev_dist[0]['category']}, contributing "
            f"{rev_dist[0]['percentage']:.1f}% ({format_currency(rev_dist[0]['amount'], currency)})."
        )

    non_zero_exp = [e for e in exp_breakdown if e["amount"] > 0]
    if non_zero_exp:
        obs.append(
            f"Largest expense category was {non_zero_exp[0]['category']} at "
            f"{format_currency(non_zero_exp[0]['amount'], currency)} "
            f"({non_zero_exp[0]['percentage']:.1f}% of total expenses)."
        )

    loss_buckets = [b for b in chart_series if b["net_profit"] < 0]
    if loss_buckets:
        obs.append(
            f"{len(loss_buckets)} sub-period(s) recorded operating losses, led by "
            f"{min(loss_buckets, key=lambda b: b['net_profit'])['label']}."
        )

    return obs


def generate_report_data(
    conn: sqlite3.Connection,
    report_type: str | None = "monthly",
    period_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> dict[str, Any]:
    ref = reference_date or date.today()
    settings = get_business_settings(conn)
    currency = settings["currency"]

    s_dt, e_dt, report_title, file_slug = resolve_report_period(
        report_type, period_key, start_date, end_date, ref
    )

    span_days = (e_dt - s_dt).days + 1
    prev_end = date.fromordinal(s_dt.toordinal() - 1)
    prev_start = date.fromordinal(prev_end.toordinal() - span_days + 1)

    df = load_transactions_df(conn, s_dt, e_dt)
    df_prev = load_transactions_df(conn, prev_start, prev_end)

    kpis = compute_kpis(df)
    prev_kpis = compute_kpis(df_prev)
    rev_dist, exp_breakdown = build_category_breakdowns(df)
    granularity, adaptive_series = build_adaptive_series(df, s_dt, e_dt)
    monthly_series = build_monthly_series(df)

    chart_series = monthly_series if (report_type or "monthly").lower() in ("quarterly", "annual") else adaptive_series
    observations = _build_report_observations(
        kpis, prev_kpis, rev_dist, exp_breakdown, currency, report_title, chart_series
    )

    tx_records = []
    if not df.empty:
        for _, r in df.sort_values(["transaction_date", "id"], ascending=[False, False]).head(100).iterrows():
            tx_records.append(
                {
                    "id": int(r["id"]),
                    "transaction_date": str(r["transaction_date"]),
                    "description": str(r["description"]),
                    "transaction_type": str(r["transaction_type"]),
                    "category": str(r["category"]),
                    "amount": round(float(r["amount"]), 2),
                    "payment_method": str(r["payment_method"]),
                    "notes": str(r["notes"] or ""),
                }
            )

    return {
        "settings": settings,
        "available_periods": get_available_report_periods(conn, ref),
        "report_meta": {
            "report_type": (report_type or "monthly").lower(),
            "period_key": period_key,
            "title": report_title,
            "file_slug": file_slug,
            "start_date": s_dt.isoformat(),
            "end_date": e_dt.isoformat(),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "summary": kpis,
        "previous_summary": prev_kpis,
        "revenue_by_category": rev_dist,
        "expense_by_category": exp_breakdown,
        "granularity": granularity if (report_type or "monthly").lower() == "monthly" else "monthly",
        "chart_series": chart_series,
        "observations": observations,
        "transactions": tx_records,
        "is_empty": df.empty,
    }


def export_transactions_csv(
    conn: sqlite3.Connection,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    transaction_type: str | None = None,
    category: str | None = None,
    search: str | None = None,
) -> str:
    """Export filtered SQLite transactions to a clean UTF-8 CSV string."""
    s_dt, e_dt, _ = resolve_date_range(period or "all", start_date, end_date)
    query = """
        SELECT id, transaction_date, description, transaction_type,
               category, amount, payment_method, notes
        FROM transactions
        WHERE 1=1
    """
    params: list[Any] = []
    if s_dt is not None:
        query += " AND transaction_date >= ?"
        params.append(s_dt.isoformat())
    if e_dt is not None:
        query += " AND transaction_date <= ?"
        params.append(e_dt.isoformat())
    if transaction_type and transaction_type.lower() != "all":
        query += " AND transaction_type = ?"
        params.append(transaction_type)
    if category and category.lower() != "all":
        query += " AND category = ?"
        params.append(category)
    if search and search.strip():
        like = f"%{search.strip()}%"
        query += " AND (description LIKE ? OR category LIKE ? OR notes LIKE ? OR payment_method LIKE ?)"
        params.extend([like, like, like, like])
    query += " ORDER BY transaction_date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "transaction_date",
            "description",
            "transaction_type",
            "category",
            "amount",
            "payment_method",
            "notes",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["transaction_date"],
                r["description"],
                r["transaction_type"],
                r["category"],
                f"{float(r['amount']):.2f}",
                r["payment_method"],
                r["notes"] or "",
            ]
        )
    return output.getvalue()


def _build_pdf_bar_chart(series: list[dict[str, Any]], font_name: str) -> Drawing:
    drawing = Drawing(480, 175)
    if not series:
        drawing.add(String(140, 85, "No period chart data available.", fontName=font_name, fontSize=10))
        return drawing

    subset = series[-12:]
    revs = [float(item["revenue"]) for item in subset]
    exps = [float(item["expenses"]) for item in subset]
    labels = [item["label"][:10] for item in subset]
    max_val = max(revs + exps + [100.0])

    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 35
    chart.height = 112
    chart.width = 415
    chart.data = [revs, exps]
    chart.strokeColor = colors.HexColor("#E2E8F0")
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max_val * 1.15
    chart.valueAxis.valueStep = max(1, round((max_val * 1.15) / 4, -2))
    chart.valueAxis.labels.fontName = font_name
    chart.valueAxis.labels.fontSize = 7
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = font_name
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 25 if len(labels) > 6 else 0
    chart.categoryAxis.labels.boxAnchor = "ne" if len(labels) > 6 else "n"
    chart.groupSpacing = 8
    chart.barSpacing = 2
    chart.bars[0].fillColor = colors.HexColor("#059669")
    chart.bars[1].fillColor = colors.HexColor("#D97706")

    legend = Legend()
    legend.x = 180
    legend.y = 162
    legend.fontName = font_name
    legend.fontSize = 8
    legend.dx = 8
    legend.dy = 8
    legend.alignment = "right"
    legend.columnMaximum = 1
    legend.colorNamePairs = [
        (colors.HexColor("#059669"), "Revenue"),
        (colors.HexColor("#D97706"), "Expenses"),
    ]

    drawing.add(chart)
    drawing.add(legend)
    return drawing


def generate_pdf_report(
    conn: sqlite3.Connection,
    report_type: str | None = "monthly",
    period_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    save_to_disk: bool = True,
) -> tuple[bytes, str]:
    """Render a polished PDF financial summary report with charts and insights."""
    report = generate_report_data(conn, report_type, period_key, start_date, end_date)
    settings = report["settings"]
    currency = settings["currency"]
    meta = report["report_meta"]
    summary = report["summary"]

    font_reg, font_bold, unicode_ok = _register_pdf_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FintrackTitle",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=16,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "FintrackSubtitle",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "FintrackSection",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=11,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "FintrackBody",
        parent=styles["Normal"],
        fontName=font_reg,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=3,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"FINTRACK - {meta['title']}",
    )

    story: list[Any] = []
    demo_tag = " | DEMONSTRATION DATA" if settings.get("is_demo_data") else ""
    story.append(Paragraph(f"FINTRACK — {settings['business_name']}", title_style))
    story.append(
        Paragraph(
            f"{meta['title']} ({meta['start_date']} to {meta['end_date']}) • Generated {meta['generated_at']}{demo_tag}",
            subtitle_style,
        )
    )

    # Executive Summary Table
    story.append(Paragraph("1. Financial Executive Summary", section_style))
    kpi_rows = [
        ["Metric", "Value", "Metric", "Value"],
        [
            "Gross Revenue",
            _pdf_money(summary["total_revenue"], currency, unicode_ok),
            "Cash Inflow",
            _pdf_money(summary["cash_inflow"], currency, unicode_ok),
        ],
        [
            "Total Expenses",
            _pdf_money(summary["total_expenses"], currency, unicode_ok),
            "Cash Outflow",
            _pdf_money(summary["cash_outflow"], currency, unicode_ok),
        ],
        [
            "Net Profit",
            _pdf_money(summary["net_profit"], currency, unicode_ok),
            "Net Cash Flow",
            _pdf_money(summary["cash_flow"], currency, unicode_ok),
        ],
        [
            "Profit Margin",
            f"{summary['profit_margin']:.2f}%",
            "Expense Ratio",
            f"{summary['expense_ratio']:.2f}%",
        ],
        [
            "Sales Transactions",
            str(summary["total_sales_transactions"]),
            "Avg Sale Value",
            _pdf_money(summary["avg_transaction_value"], currency, unicode_ok),
        ],
    ]
    kpi_table = Table(kpi_rows, colWidths=[40 * mm, 48 * mm, 40 * mm, 48 * mm])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font_reg),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
            ]
        )
    )
    story.append(kpi_table)

    # Revenue vs Expense Chart
    story.append(Paragraph("2. Revenue vs. Expenses Trend", section_style))
    story.append(_build_pdf_bar_chart(report["chart_series"], font_reg))

    # Category Breakdowns
    story.append(Paragraph("3. Revenue & Expense Category Breakdown", section_style))
    rev_rows = [["Revenue Category", "Transactions", "Amount", "Share"]]
    for item in report["revenue_by_category"]:
        rev_rows.append(
            [
                item["category"],
                str(item["count"]),
                _pdf_money(item["amount"], currency, unicode_ok),
                f"{item['percentage']:.1f}%",
            ]
        )
    if len(rev_rows) == 1:
        rev_rows.append(["No revenue entries", "0", _pdf_money(0, currency, unicode_ok), "0.0%"])

    exp_rows = [["Expense Category", "Transactions", "Amount", "Share"]]
    for item in report["expense_by_category"]:
        if item["amount"] > 0 or item["count"] > 0:
            exp_rows.append(
                [
                    item["category"],
                    str(item["count"]),
                    _pdf_money(item["amount"], currency, unicode_ok),
                    f"{item['percentage']:.1f}%",
                ]
            )
    if len(exp_rows) == 1:
        exp_rows.append(["No expense entries", "0", _pdf_money(0, currency, unicode_ok), "0.0%"])

    cat_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), font_bold),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 0), (-1, -1), 8.2),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("PADDING", (0, 0), (-1, -1), 4.5),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]
    )
    rev_tbl = Table(rev_rows, colWidths=[72 * mm, 28 * mm, 48 * mm, 28 * mm])
    rev_tbl.setStyle(cat_style)
    story.append(rev_tbl)
    story.append(Spacer(1, 5 * mm))

    exp_tbl = Table(exp_rows, colWidths=[72 * mm, 28 * mm, 48 * mm, 28 * mm])
    exp_tbl.setStyle(cat_style)
    story.append(exp_tbl)

    # Observations
    story.append(Paragraph("4. Business Performance Observations", section_style))
    for obs in report["observations"]:
        clean_obs = obs if unicode_ok else obs.replace("₹", "INR ")
        story.append(Paragraph(f"• {clean_obs}", body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"fintrack_{meta['file_slug']}.pdf"
    if save_to_disk:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / filename).write_bytes(pdf_bytes)

    return pdf_bytes, filename
