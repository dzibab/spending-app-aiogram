import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests


_exchange_rate_cache = {}


def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Fetch exchange rate from from_currency to to_currency using exchangerate.host API.
    Caches the result for 24 hours.
    Returns the rate as float.
    """
    if from_currency == to_currency:
        return 1.0

    key = (from_currency, to_currency)
    now = datetime.now(tz=timezone.utc)
    ttl = timedelta(hours=24)

    # Check cache
    cached = _exchange_rate_cache.get(key)
    if cached:
        rate, timestamp = cached
        if now - timestamp < ttl:
            return rate

    url = "https://api.exchangerate.host/convert"
    api_key = os.getenv("EXCHANGE_API_KEY")
    params = {
        "from": from_currency,
        "to": to_currency,
        "amount": 1,
    }
    if api_key:
        params["access_key"] = api_key
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = float(data.get("result", 1.0))
    except (requests.RequestException, ValueError, KeyError):
        rate = 1.0

    # Update cache
    _exchange_rate_cache[key] = (rate, now)
    return rate


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert amount from from_currency to to_currency using exchangerate.host API.
    Uses a cached exchange rate for efficiency.
    """
    if from_currency == to_currency:
        return amount
    rate = get_exchange_rate(from_currency, to_currency)
    return amount * rate


def aggregate_expenses_by_category(
    expenses: list[dict], user_currency: str
) -> tuple[dict, float]:
    """
    Aggregates expenses by category and returns (category_totals, total_sum), all in user_currency.
    Uses convert_currency for conversion.
    """
    category_totals = defaultdict(float)
    total_sum = 0.0
    for exp in expenses:
        amount = exp["amount"]
        from_currency = exp["currency"]
        category = exp["category"]
        converted = convert_currency(amount, from_currency, user_currency)
        category_totals[category] += converted
        total_sum += converted
    return dict(category_totals), total_sum


def format_stats_message(
    period: str, category_totals: dict, total_sum: float, user_currency: str
) -> str:
    """
    Format the stats for Telegram message output.
    """
    period_map = {
        "week": "Last 7 days",
        "month": "Current Month",
        "year": "Current Year",
    }
    period_str = period_map.get(period, period.capitalize())
    lines = [f"\U0001f4ca <b>Stats for {period_str}</b>", ""]
    if not category_totals:
        lines.append("No expenses found for this period.")
    else:
        lines.append(f"<b>By Category ({user_currency}):</b>")
        for cat, amt in sorted(category_totals.items(), key=lambda x: -x[1]):
            lines.append(f"• {cat}: <b>{amt:.2f}</b>")
        lines.append("")
        lines.append(f"<b>Total:</b> <b>{total_sum:.2f} {user_currency}</b>")
    return "\n".join(lines)
