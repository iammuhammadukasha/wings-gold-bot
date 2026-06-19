from datetime import date as date_type
from typing import List, Dict, Any


def _fmt_date(d):
    # type: (date_type) -> str
    return d.strftime("%A, %d %B %Y")


def build_template_a(events, today):
    # type: (List[Dict], date_type) -> str
    event_lines = []
    for ev in events:
        icon = "\U0001f534" if ev["impact"].lower() == "high" else "\U0001f7e0"
        event_lines.append("{} {} — {}".format(icon, ev["time_sgt_str"], ev["title"]))

    lines = [
        "\U0001f6a8 WINGS GOLD CLUB — DAILY NEWS & IMPACT UPDATE \U0001f6a8",
        "",
        "Good afternoon traders. Checking the economic news calendar for today:",
        "",
        "\U0001f4cc USD HIGH-IMPACT NEWS TODAY (Singapore Time):",
        "",
    ] + event_lines + [
        "",
        "\U0001f534 = High Impact   \U0001f7e0 = Medium Impact",
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


def _lead_label(minutes_before):
    # type: (int) -> str
    """Human phrasing for a lead time, e.g. 60 -> '1 HOUR', 15 -> '15 MIN'."""
    if minutes_before >= 60 and minutes_before % 60 == 0:
        hrs = minutes_before // 60
        return "{} HOUR".format(hrs) if hrs == 1 else "{} HOURS".format(hrs)
    return "{} MIN".format(minutes_before)


def _lead_phrase(minutes_before):
    # type: (int) -> str
    if minutes_before >= 60 and minutes_before % 60 == 0:
        hrs = minutes_before // 60
        return "~1 hour" if hrs == 1 else "~{} hours".format(hrs)
    return "~{} minutes".format(minutes_before)


def build_template_reminder(event, minutes_before):
    # type: (Dict, int) -> str
    """Pre-release countdown reminder for a scheduled USD event.

    Fired at each configured lead time (default T-60 and T-15). Copy hardens as
    the release nears: the final (<=15 min) reminder is an urgent stand-aside
    warning, earlier ones are a heads-up to start managing risk.
    """
    is_high = event.get("impact", "").lower() == "high"
    impact_icon = "\U0001f534" if is_high else "\U0001f7e0"
    final = minutes_before <= 15

    if final:
        header = "\U0001f6a8 WINGS GOLD CLUB — NEWS COUNTDOWN ({}) \U0001f6a8".format(
            _lead_label(minutes_before))
        intro = "Final warning — {} drops in {}.".format(
            event["title"], _lead_phrase(minutes_before))
        action = (
            "Spreads will widen and volatility will spike at the print. Lock in "
            "management on any open trades now, then stand aside through the "
            "release and let the structure form before re-engaging."
        )
    else:
        header = "⏰ WINGS GOLD CLUB — NEWS COUNTDOWN ({}) ⏰".format(
            _lead_label(minutes_before))
        intro = "Heads up traders — a USD economic release is coming up in {}.".format(
            _lead_phrase(minutes_before))
        action = (
            "Start trimming exposure and tightening risk ahead of the release. "
            "Avoid opening fresh positions into the news window."
        )

    lines = [
        header,
        "",
        intro,
        "",
        "\U0001f4cb Event: {}".format(event["title"]),
        "\U0001f550 Release: {}".format(event.get("time_sgt_str", "TBD")),
        "{} Impact: {}".format(impact_icon, "High" if is_high else "Medium"),
        "• \U0001f7e1 Forecast: {}".format(event.get("forecast") or "N/A"),
        "• ⚪ Previous: {}".format(event.get("previous") or "N/A"),
        "",
        action,
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
