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


def fmt_quarter_label(ts, projected: bool = False) -> str:
    """'2025 Q3' (or '2025 Q3 (projected)') from a mid-quarter timestamp.

    Mirrors the project's quarter-to-month convention (Q1→Feb, Q2→May,
    Q3→Aug, Q4→Nov) used to place quarterly points on the date axis.
    """
    q = {2: 1, 5: 2, 8: 3, 11: 4}[int(ts.month)]
    label = f"{int(ts.year)} Q{q}"
    return f"{label} (projected)" if projected else label
