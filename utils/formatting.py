"""
Number, currency, and percent formatting helpers for display.
"""


def fmt_number(val, decimals=0) -> str:
    """Format a number with commas (e.g., 1,234,567)."""
    if val is None or str(val) == "nan":
        return "N/A"
    return f"{val:,.{decimals}f}"


def fmt_currency(val, decimals=0) -> str:
    """Format as USD (e.g., $1,234)."""
    if val is None or str(val) == "nan":
        return "N/A"
    return f"${val:,.{decimals}f}"


def fmt_pct(val, decimals=1) -> str:
    """Format as percentage (e.g., 3.2%)."""
    if val is None or str(val) == "nan":
        return "N/A"
    return f"{val:,.{decimals}f}%"
