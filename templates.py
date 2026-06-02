from datetime import date as date_type
from typing import List, Dict, Any


def _fmt_date(d):
    # type: (date_type) -> str
    return d.strftime("%A, %d %B %Y")


def build_template_a(events, today):
    # type: (List[Dict], date_type) -> str
    lines = [
        "\U0001f6a8 WINGS GOLD CLUB — HIGH IMPACT NEWS ALERT \U0001f6a8",
        "",
        "Good afternoon, traders. Institutional money does not guess; it waits for data. Protect your capital and mark your calendars.",
        "",
        "Today’s High-Impact USD Economic Events (Singapore Time):",
        "",
        "\U0001f4c5 Date: {}".format(_fmt_date(today)),
    ]
    for ev in events:
        icon = "\U0001f534" if ev["impact"].lower() == "high" else "\U0001f7e0"
        lines.append("• ⏱️ {} — USD: {} {}".format(
            ev["time_sgt_str"], ev["title"], icon
        ))
    lines += [
        "",
        "\U0001f4a1 INTRADAY ANALYSIS & BIAS:",
        "Expect the morning Asian session to hold a tight compression. Do not chase the early breakout chop.",
        "",
        "Look for market manipulation sweeping the London session highs/lows roughly 15–30 minutes prior to the release timings above, as market makers trap retail liquidity.",
        "",
        "Detailed execution signals will drop live in the VIP channel post-release once the volatility clears. Manage your risk! \U0001f41c",
    ]
    return "\n".join(lines)


def build_template_b(today):
    # type: (date_type) -> str
    lines = [
        "\U0001f48e WINGS GOLD CLUB — MARKET UPDATE \U0001f48e",
        "",
        "Good afternoon, traders. Checking the macro calendar for today:",
        "",
        "\U0001f4c5 Date: {}".format(_fmt_date(today)),
        "• \U0001f7e2 No High or Medium Impact USD News Scheduled.",
        "",
        "\U0001f4a1 INTRADAY ANALYSIS & BIAS:",
        "With no major macro data drivers on the horizon today, technical price structures, clean trend continuations, and volume flows during the London (2 PM SGT) and New York (8 PM SGT) session opens will fully dictate XAUUSD directional movement.",
        "",
        "Trade setups will be posted in the VIP room normally. Stay disciplined. \U0001f41c",
    ]
    return "\n".join(lines)


def build_template_c(event_name, old_time, new_time):
    # type: (str, str, str) -> str
    lines = [
        "⚠️ WINGS GOLD CLUB — SCHEDULE UPDATE NOTICE ⚠️",
        "",
        "Traders, note that the scheduled release time for today’s USD economic event has been adjusted on Forex Factory.",
        "",
        "\U0001f4cb Event: {}".format(event_name),
        "❌ Old Time: {}".format(old_time),
        "✅ New Time: {}".format(new_time),
        "",
        "Adjust your trade management plans, alert triggers, and risk boundaries accordingly. Stay sharp!",
    ]
    return "\n".join(lines)


def build_template_d(event, result):
    # type: (Dict, Dict) -> str
    lines = [
        "\U0001f4ca WINGS GOLD CLUB — LIVE NEWS RESULTS ANALYSIS \U0001f4ca",
        "",
        "The USD economic data has officially crossed the wires. Here are the raw numbers and the immediate tactical bias breakdown:",
        "",
        "\U0001f4cb Event: {}".format(event["title"]),
        "• \U0001f7e2 Actual:   {}".format(event["actual"]),
        "• \U0001f7e1 Forecast: {}".format(event["forecast"] or "N/A"),
        "• ⚪ Previous: {}".format(event["previous"] or "N/A"),
        "",
        "\U0001f50d DATA ASSESSMENT:",
        result["data_text"],
        "",
        "\U0001f4c8 MARKET BIAS FOR GOLD (XAUUSD):",
        "\U0001f449 Directional Bias: {}".format(result["bias"]),
        "",
        "⚠️ WARNING: The initial 5–10 minute price extensions are frequently driven by algorithmic spread-widening and stop-hunting. Do not chase the initial candlestick wick. Let the structure stabilise.",
        "",
        "We are monitoring lower timeframe order flows right now. VIP entries will post shortly. \U0001f41c",
    ]
    return "\n".join(lines)
