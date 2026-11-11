"""Currency formatting and safe arithmetic helpers."""

from __future__ import annotations


CURRENCY_CONFIG = {
    "INR": {"symbol": "₹", "name": "Indian Rupee (INR)", "code": "INR"},
    "USD": {"symbol": "$", "name": "US Dollar (USD)", "code": "USD"},
    "EUR": {"symbol": "€", "name": "Euro (EUR)", "code": "EUR"},
    "GBP": {"symbol": "£", "name": "British Pound (GBP)", "code": "GBP"},
}


def get_currency_symbol(currency_code: str | None) -> str:
    code = (currency_code or "INR").upper()
    return CURRENCY_CONFIG.get(code, CURRENCY_CONFIG["INR"])["symbol"]


def format_indian_number(value: float, decimals: int = 0) -> str:
    """Format a number using the Indian numbering system (xx,xx,xxx)."""
    neg = value < 0
    abs_val = abs(float(value))
    formatted = f"{abs_val:.{decimals}f}"
    if "." in formatted:
        int_part, dec_part = formatted.split(".")
        dec_suffix = f".{dec_part}"
    else:
        int_part = formatted
        dec_suffix = ""

    if len(int_part) <= 3:
        grouped = int_part
    else:
        last_three = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        grouped = ",".join(reversed(groups)) + "," + last_three

    prefix = "-" if neg else ""
    return f"{prefix}{grouped}{dec_suffix}"


def format_currency(value: float, currency_code: str = "INR", decimals: int = 0) -> str:
    symbol = get_currency_symbol(currency_code)
    code = (currency_code or "INR").upper()
    neg = value < 0
    abs_val = abs(float(value))
    if code == "INR":
        num_str = format_indian_number(abs_val, decimals=decimals)
    else:
        num_str = f"{abs_val:,.{decimals}f}"
    return f"-{symbol}{num_str}" if neg else f"{symbol}{num_str}"


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator is None or abs(float(denominator)) < 1e-9:
        return default
    return float(numerator) / float(denominator)


def pct_change(current: float, previous: float) -> float | None:
    """Compute percentage change safely; returns None if previous baseline is zero."""
    if previous is None or abs(float(previous)) < 1e-9:
        return None
    return round(((float(current) - float(previous)) / abs(float(previous))) * 100.0, 2)
