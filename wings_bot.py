#!/usr/bin/env python3
"""
Wings Gold Club — Telegram automation bot.

Modes (invoked via cron):
  --morning-alert   Daily 12:00 PM SGT — Template A (news day) or B (quiet day)
  --watchdog        Every 15 min     — Template C on schedule changes
  --post-release    Every 1 min      — Template D after each event fires
"""
import argparse
import sys
import os
from datetime import datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import POST_RELEASE_DELAY_MIN, POST_RELEASE_TIMEOUT_MIN
from ff import fetch_today_events, compare_snapshots, assess_result
from notifier import send_message
from state import load_snapshot, save_snapshot, load_processed, save_processed
from templates import build_template_a, build_template_b, build_template_c, build_template_d

SGT = pytz.timezone("Asia/Singapore")


def _log(msg):
    ts = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S SGT")
    print("[{}] {}".format(ts, msg))


# ---------------------------------------------------------------------------
# Workflow 1 — Morning Alert (12:00 PM SGT)
# ---------------------------------------------------------------------------

def run_morning_alert():
    now_sgt = datetime.now(SGT)
    today = now_sgt.date()

    _log("Morning alert starting.")
    events = fetch_today_events()

    # Only show events that haven't occurred yet at time of posting
    remaining = [ev for ev in events if ev["time_sgt"] and ev["time_sgt"] > now_sgt]

    if remaining:
        msg = build_template_a(remaining, today)
        label = "Template A ({} events)".format(len(remaining))
    else:
        msg = build_template_b(today)
        label = "Template B (no upcoming events)"

    ok = send_message(msg)
    if ok:
        save_snapshot(events)
        _log("Morning alert sent — {}.".format(label))
    else:
        _log("ERROR: Morning alert failed to send.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Workflow 2 — Watchdog (every 15 min)
# ---------------------------------------------------------------------------

def run_watchdog():
    _log("Watchdog starting.")
    events = fetch_today_events()
    old_events = load_snapshot()

    if not events and old_events:
        _log("Watchdog: fetch returned empty but snapshot has {} items — FF may be down. Skipping.".format(len(old_events)))
        return

    changes = compare_snapshots(old_events, events)

    if changes:
        for ch in changes:
            msg = build_template_c(ch["title"], ch["old_time"], ch["new_time"])
            send_message(msg)
            _log("Schedule change sent: {} ({} → {}).".format(ch["title"], ch["old_time"], ch["new_time"]))
        save_snapshot(events)
    else:
        _log("Watchdog: no changes detected.")


# ---------------------------------------------------------------------------
# Workflow 3 — Post-Release (every 1 min)
# ---------------------------------------------------------------------------

def run_post_release():
    now_sgt = datetime.now(SGT)
    events = fetch_today_events()
    processed = load_processed()
    changed = False

    for ev in events:
        key = ev["event_key"]
        ev_time = ev["time_sgt"]

        if ev_time is None:
            continue

        state = processed.get(key, {})
        if state.get("status") in ("sent", "skipped"):
            continue

        minutes_since = (now_sgt - ev_time).total_seconds() / 60.0

        if minutes_since < POST_RELEASE_DELAY_MIN:
            continue

        if minutes_since > POST_RELEASE_TIMEOUT_MIN:
            processed[key] = {"status": "skipped", "reason": "timeout"}
            _log("Post-release: {} timed out — no actual value within {} min.".format(
                ev["title"], POST_RELEASE_TIMEOUT_MIN
            ))
            changed = True
            continue

        actual = ev.get("actual", "").strip()
        if not actual:
            attempts = state.get("attempts", 0) + 1
            processed[key] = {"status": "pending", "attempts": attempts}
            _log("Post-release: {} — actual not yet available (attempt {}).".format(ev["title"], attempts))
            changed = True
            continue

        result = assess_result(ev)
        msg = build_template_d(ev, result)
        ok = send_message(msg)

        if ok:
            processed[key] = {"status": "sent", "sent_at": now_sgt.isoformat()}
            _log("Post-release sent: {} — {}.".format(ev["title"], result["assessment"]))
        else:
            _log("ERROR: Failed to send post-release for {}.".format(ev["title"]))
        changed = True

    if changed:
        save_processed(processed)


# ---------------------------------------------------------------------------
# Test — send all four templates with sample data
# ---------------------------------------------------------------------------

def run_test_all():
    from datetime import date
    now_sgt = datetime.now(SGT)
    today = now_sgt.date()

    _log("Sending Template A (active news day)...")
    sample_events = [
        {
            "title": "JOLTs Job Openings",
            "impact": "High",
            "time_sgt_str": "10:00 PM SGT",
        },
        {
            "title": "ISM Manufacturing PMI",
            "impact": "Medium",
            "time_sgt_str": "11:00 PM SGT",
        },
    ]
    send_message(build_template_a(sample_events, today))

    _log("Sending Template B (no news day)...")
    send_message(build_template_b(today))

    _log("Sending Template C (schedule change)...")
    send_message(build_template_c("Non-Farm Payrolls", "08:30 PM SGT", "09:00 PM SGT"))

    _log("Sending Template D (post-release result)...")
    sample_event = {
        "title": "JOLTs Job Openings",
        "actual": "7.19M",
        "forecast": "7.48M",
        "previous": "7.48M",
    }
    result = {
        "data_text": "USD DATA CAME OUT WEAKER THAN EXPECTED (BAD FOR USD)",
        "bias": "LOOK FOR BUY SETUPS (Bullish Gold Momentum)",
    }
    send_message(build_template_d(sample_event, result))

    _log("All four templates sent.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Wings Gold Club Telegram Bot")
    parser.add_argument("--morning-alert", action="store_true",
                        help="Send daily morning alert (cron: 12:00 PM SGT = 04:00 UTC)")
    parser.add_argument("--watchdog", action="store_true",
                        help="Check for schedule changes (cron: every 15 min)")
    parser.add_argument("--post-release", action="store_true",
                        help="Send post-release analysis (cron: every 1 min)")
    parser.add_argument("--test-all", action="store_true",
                        help="Send all four templates with sample data for review")

    args = parser.parse_args()

    if args.morning_alert:
        run_morning_alert()
    elif args.watchdog:
        run_watchdog()
    elif args.post_release:
        run_post_release()
    elif args.test_all:
        run_test_all()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
