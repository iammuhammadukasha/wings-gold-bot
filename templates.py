from datetime import date as date_type
from typing import List, Dict, Any


def _fmt_date(d):
    # type: (date_type) -> str
    return d.strftime("%A, %d %B %Y")


def build_template_a(events, today):
    # type: (List[Dict], date_type) -> str
    # Build event list lines
    event_lines = []
    for ev in events:
        impact_label = "High Volatility" if ev["impact"].lower() == "high" else "Medium Volatility"
        icon = "\U0001f534" if ev["impact"].lower() == "high" else "\U0001f7e0"
        event_lines.append("• {} {} SGT – USD: {} ({})".format(
            icon, ev["time_sgt_str"], ev["title"], impact_label
        ))

    # Reference the first (or only) high-impact event in the body text
    primary = next((e for e in events if e["impact"].lower() == "high"), events[0])
    primary_ref = "{} at {}".format(primary["title"], primary["time_sgt_str"])

    lines = [
        "\U0001f3c6 WINGS GOLD CLUB – DAILY MACRO UPDATE \U0001f3c6",
        "",
        "Good afternoon, traders. Institutional money does not guess; it waits for data. If you do not know the economic calendar today, you are the liquidity.",
        "",
        "\U0001f534 HIGH-IMPACT USD NEWS TODAY (Singapore Time):",
    ] + event_lines + [
        "",
        "\U0001f4c9 THE GAME PLAN FOR XAUUSD:",
        "The morning Asian session is likely to be a low-volume accumulation zone. Do not chase the early breakouts or you will get chopped up.",
        "",
        "Keep your eyes locked on the 2:00 PM – 3:00 PM SGT window for the London open to map out your initial intraday bias.",
        "",
        "With {} dropping today, expect the market to manipulate the London highs or lows right before the release to trap retail traders.".format(primary_ref),
        "",
        "We will be looking for execution setups inside the VIP channel once the true direction prints. Protect your capital and manage your risk. \U0001f41c",
        "",
        "Let’s hunt.",
        "",
        "Wings Gold Club",
    ]
    return "\n".join(lines)


def build_template_b(today):
    # type: (date_type) -> str
    lines = [
        "\U0001f3c6 WINGS GOLD CLUB – DAILY MACRO UPDATE \U0001f3c6",
        "",
        "Good afternoon, traders. Checking the macro calendar for today:",
        "",
        "\U0001f4c5 Date: {}".format(_fmt_date(today)),
        "• \U0001f7e2 No High or Medium Impact USD News Scheduled.",
        "",
        "\U0001f4c9 THE GAME PLAN FOR XAUUSD:",
        "With no major macro data drivers today, technical price structures, clean trend continuations, and volume flows during the London (2:00 PM – 3:00 PM SGT) and New York (8:00 PM – 9:00 PM SGT) session opens will fully dictate XAUUSD directional movement.",
        "",
        "Trade setups will be posted in the VIP channel as usual. Stay disciplined. \U0001f41c",
        "",
        "Let's hunt.",
        "",
        "Wings Gold Club",
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
