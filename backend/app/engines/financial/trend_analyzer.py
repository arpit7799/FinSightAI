# app/engines/financial/trend_analyzer.py
"""
Analyzes ratio trends across multiple years of filings for the same company.

Takes a list of (fiscal_year, ratios_dict) pairs and computes
year-over-year changes and overall trend direction.
"""


def calculate_yoy_change(current: float, previous: float) -> float | None:
    """Calculate year-over-year percentage change."""
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)


def get_trend_direction(values: list[float]) -> str:
    """
    Given a list of values over time (oldest first),
    determine if the trend is IMPROVING, DECLINING, or STABLE.
    """
    # Filter out None values
    clean = [v for v in values if v is not None]

    if len(clean) < 2:
        return "INSUFFICIENT_DATA"

    # Compare first half average to second half average
    mid = len(clean) // 2
    first_half_avg = sum(clean[:mid]) / mid
    second_half_avg = sum(clean[mid:]) / len(clean[mid:])

    change_pct = calculate_yoy_change(second_half_avg, first_half_avg)

    if change_pct is None:
        return "STABLE"
    elif change_pct > 5:
        return "IMPROVING"
    elif change_pct < -5:
        return "DECLINING"
    else:
        return "STABLE"


def analyze_trends(yearly_ratios: list[dict]) -> dict:
    """
    Analyze ratio trends across multiple years.

    Input:
        yearly_ratios — list of dicts, each with:
            {"fiscal_year": 2023, "ratios": [{"ratio_name": ..., "computed_value": ...}]}
        Sorted oldest to newest.

    Output:
        Dict of ratio_name -> trend info:
        {
            "Current Ratio": {
                "values": [1.8, 2.0, 2.3],
                "years": [2021, 2022, 2023],
                "trend": "IMPROVING",
                "yoy_change_pct": 15.0,   # most recent YoY
                "latest_value": 2.3,
            }
        }
    """
    if not yearly_ratios:
        return {}

    # Build a dict of ratio_name -> list of (year, value) pairs
    ratio_history = {}

    for year_data in yearly_ratios:
        year = year_data["fiscal_year"]
        for ratio in year_data.get("ratios", []):
            name = ratio["ratio_name"]
            value = ratio["computed_value"]

            if name not in ratio_history:
                ratio_history[name] = []
            ratio_history[name].append((year, value))

    # Now compute trend for each ratio
    result = {}
    for name, history in ratio_history.items():
        # Sort by year
        history.sort(key=lambda x: x[0])

        years = [h[0] for h in history]
        values = [h[1] for h in history]

        # Latest YoY change
        yoy = None
        if len(values) >= 2 and values[-1] is not None and values[-2] is not None:
            yoy = calculate_yoy_change(values[-1], values[-2])

        result[name] = {
            "values": values,
            "years": years,
            "trend": get_trend_direction(values),
            "yoy_change_pct": yoy,
            "latest_value": values[-1] if values else None,
        }

    return result