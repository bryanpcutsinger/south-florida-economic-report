"""
Narrative text generation and source citations.
Template-based descriptive paragraphs — no LLM calls.
"""
import pandas as pd

from utils.formatting import fmt_number, fmt_pct


def source_citation(name: str, url: str, frequency: str) -> str:
    """Return a source citation string for st.caption()."""
    return f"Source: [{name}]({url}) — {frequency}"


def narrate_employment_trends(
    county_name: str,
    start_year: int,
    end_year: int,
    start_empl: float,
    end_empl: float,
) -> str:
    """Describe employment level change over a multi-year period."""
    if start_empl is None or end_empl is None or start_empl == 0:
        return (
            f"Between {start_year} and {end_year}, employment data for "
            f"{county_name} is incomplete."
        )
    change_pct = (end_empl - start_empl) / start_empl * 100
    direction = "an increase" if change_pct >= 0 else "a decrease"
    return (
        f"Between {start_year} and {end_year}, employment in {county_name} "
        f"went from {fmt_number(start_empl)} to {fmt_number(end_empl)}, "
        f"{direction} of {fmt_pct(abs(change_pct))}."
    )


def narrate_wage_distribution(
    county_name: str,
    year: int,
    qtr: int,
    highest_industry: str,
    highest_wage: float,
    lowest_industry: str,
    lowest_wage: float,
    overall_avg: float,
) -> str:
    """Describe the wage range across industries."""
    from utils.formatting import fmt_currency

    text = (
        f"In {year} Q{qtr}, the highest-paying industry in {county_name} was "
        f"{highest_industry} (${highest_wage:,.0f}/year), "
        f"while the lowest was {lowest_industry} (${lowest_wage:,.0f}/year)."
    )
    if overall_avg is not None and pd.notna(overall_avg):
        text += f" The overall average was ${overall_avg:,.0f}."
    return text
