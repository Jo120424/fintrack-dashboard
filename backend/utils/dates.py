"""Date range resolution and period comparison utilities."""

from __future__ import annotations

import calendar
from datetime import date, timedelta


VALID_PERIODS = {
    "today",
    "this_week",
    "this_month",
    "last_month",
    "last_3_months",
    "last_6_months",
    "this_year",
    "all",
    "custom",
}


def _subtract_months(ref: date, months: int) -> date:
    idx = (ref.year * 12 + (ref.month - 1)) - months
    yr = idx // 12
    mo = (idx % 12) + 1
    dom = min(ref.day, calendar.monthrange(yr, mo)[1])
    return date(yr, mo, dom)


def resolve_date_range(
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    reference_date: date | None = None,
) -> tuple[date | None, date | None, str]:
    """Resolve a global filter preset or custom range into inclusive (start, end) dates."""
    ref = reference_date or date.today()
    key = (period or "this_year").strip().lower()
    if key not in VALID_PERIODS:
        raise ValueError(f"Unsupported period filter '{period}'.")

    if key == "today":
        return ref, ref, "Today"
    if key == "this_week":
        # Monday as start of business week
        start = ref - timedelta(days=ref.weekday())
        return start, ref, "This Week"
    if key == "this_month":
        return date(ref.year, ref.month, 1), ref, "This Month"
    if key == "last_month":
        prev_idx = (ref.year * 12 + (ref.month - 1)) - 1
        yr, mo = prev_idx // 12, (prev_idx % 12) + 1
        last_dom = calendar.monthrange(yr, mo)[1]
        return date(yr, mo, 1), date(yr, mo, last_dom), "Last Month"
    if key == "last_3_months":
        start_idx = (ref.year * 12 + (ref.month - 1)) - 2
        yr, mo = start_idx // 12, (start_idx % 12) + 1
        return date(yr, mo, 1), ref, "Last 3 Months"
    if key == "last_6_months":
        start_idx = (ref.year * 12 + (ref.month - 1)) - 5
        yr, mo = start_idx // 12, (start_idx % 12) + 1
        return date(yr, mo, 1), ref, "Last 6 Months"
    if key == "this_year":
        return date(ref.year, 1, 1), ref, "This Year"
    if key == "all":
        return None, None, "All Data"

    # Custom date range
    if not start_date or not end_date:
        raise ValueError("Both start_date and end_date are required for custom date range.")
    try:
        s_dt = date.fromisoformat(start_date.strip())
        e_dt = date.fromisoformat(end_date.strip())
    except ValueError as exc:
        raise ValueError("Custom dates must be formatted as YYYY-MM-DD.") from exc
    if s_dt > e_dt:
        raise ValueError("start_date cannot be after end_date.")
    return s_dt, e_dt, f"{s_dt.isoformat()} to {e_dt.isoformat()}"


def resolve_previous_period(
    period: str | None,
    start: date | None,
    end: date | None,
    reference_date: date | None = None,
) -> tuple[date | None, date | None, str]:
    """Compute the immediate comparison period for period-over-period KPI deltas."""
    ref = reference_date or date.today()
    key = (period or "this_year").strip().lower()

    if start is None or end is None:
        return None, None, "No Prior Period"

    if key == "today":
        prev = start - timedelta(days=1)
        return prev, prev, "Yesterday"
    if key == "this_week":
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=6)
        return prev_start, prev_end, "Previous Week"
    if key == "this_month":
        prev_idx = (start.year * 12 + (start.month - 1)) - 1
        yr, mo = prev_idx // 12, (prev_idx % 12) + 1
        return date(yr, mo, 1), date(yr, mo, calendar.monthrange(yr, mo)[1]), "Last Month"
    if key == "last_month":
        prev_idx = (start.year * 12 + (start.month - 1)) - 1
        yr, mo = prev_idx // 12, (prev_idx % 12) + 1
        return date(yr, mo, 1), date(yr, mo, calendar.monthrange(yr, mo)[1]), "Prior Month"
    if key == "this_year":
        try:
            prev_start = date(start.year - 1, 1, 1)
            prev_end = date(end.year - 1, end.month, min(end.day, calendar.monthrange(end.year - 1, end.month)[1]))
        except ValueError:
            prev_start = date(start.year - 1, 1, 1)
            prev_end = date(end.year - 1, 12, 31)
        return prev_start, prev_end, "Prior Year YTD"

    # Generic equal-duration preceding window for last_3_months, last_6_months, custom
    span_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span_days - 1)
    return prev_start, prev_end, "Previous Period"


def current_and_previous_month_bounds(reference_date: date | None = None) -> tuple[tuple[date, date], tuple[date, date]]:
    """Return (current_month_start, reference_date) and (prev_month_start, prev_month_end)."""
    ref = reference_date or date.today()
    cur_start = date(ref.year, ref.month, 1)
    prev_idx = (ref.year * 12 + (ref.month - 1)) - 1
    p_yr, p_mo = prev_idx // 12, (prev_idx % 12) + 1
    prev_start = date(p_yr, p_mo, 1)
    prev_end = date(p_yr, p_mo, calendar.monthrange(p_yr, p_mo)[1])
    return (cur_start, ref), (prev_start, prev_end)
