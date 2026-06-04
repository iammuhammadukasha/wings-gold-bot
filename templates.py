from datetime import date as date_type
from typing import List, Dict, Any


def _fmt_date(d):
    # type: (date_type) -> str
    return d.strftime("%A, %d %B %Y")


def build_template_a(events, today):
    # type: (List[Dict], date_type) -> str
    event_lines = []
    for ev in events:
        impact_label = "High Volatility" if ev["impact"].lower() == "high" else "Medium Volatility"
        event_lines.append("• {} SGT - USD: {} ({})".format(
            ev["time_sgt_str"], ev["title"], impact_label
        ))

    lines = [
        "\U0001f6a8 WINGS GOLD CLUB — DAILY NEWS & IMPACT UPDATE \U0001f6a8",
        "",
        "Good afternoon traders. Checking the economic news calendar for today:",
        "",
        "HIGH-IMPACT USD NEWS TODAY (Singapore Time):",
    ] + event_lines + [
        "",
        "Watch the 2:00 PM - 3:00 PM SGT window for the London open to map out initial intraday bias.",
        "",
        "Trade setups will be posted in the VIP channel as usual. Stay disciplined.",
        "",
        "Wings Gold Club",
    ]
    return "\n".join(lines)


def build_template_b(today):
    # type: (date_type) -> str
    lines = [
        "\U0001f48e WINGS GOLD CLUB — DAILY NEWS UPDATE \U0001f48e",
        "",
        "Good afternoon traders. Checking the economic news calendar for today:",
        "",
        "\U0001f4c5 Date: {}".format(_fmt_date(today)),
        "• \U0001f7e2 No High or Medium Impact USD News Scheduled.",
        "",
        "Trade setups will be posted in the VIP channel as usual. Stay disciplined.",
        "",
        "Wings Gold Club",
    ]
    return "\n".join(lines)


def build_template_c(event_name, old_time, new_time):
    # type: (str, str, str) -> str
    lines = [
        "⚠️ WINGS GOLD CLUB — NEWS UPDATE NOTICE ⚠️",
        "",
        "Traders, note that the scheduled release time for today's USD economic event has been adjusted on Forex Factory.",
        "",
        "\U0001f4cb Event: {}".format(event_name),
        "❌ Old Time: {}".format(old_time),
        "✅ New Time: {}".format(new_time),
        "",
        "Adjust your trade management plans, alert triggers, and risk boundaries accordingly.",
        "",
        "Trade setups will be posted in the VIP channel as usual. Stay disciplined.",
        "",
        "Wings Gold Club",
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
        "⚠️ WARNING: The initial 5-10 minute price extensions are frequently driven by algorithmic spread-widening and stop-hunting. Do not chase the initial candlestick wick. Let the structure stabilise.",
        "",
        "Trade setups will be posted in the VIP channel as usual. Stay disciplined.",
        "",
        "Wings Gold Club",
    ]
    return "\n".join(lines)
