#!/usr/bin/env python3
"""
Wings Gold Club — Telegram automation bot.

Modes (invoked via cron):
  --morning-alert   Daily 12:00 PM SGT — Template A (news day) or B (quiet day)
  --watch           Every 1 min      — schedule changes (Template C) AND
                                        post-release analysis (Template D) in
                                        a single FF fetch. Preferred.

Legacy modes (still work; superseded by --watch):
  --watchdog        Template C on schedule changes only
  --post-release    Template D post-release analysis only
"""
import argparse
import sys
import os
from datetime import datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Defensive import: the server keeps its own config.py (restored by deploy.sh
# after each git pull), which may predate these constants. Fall back to the
# new defaults so a stale server config can never crash the bot on import.
try:
    from config import POST_RELEASE_DELAY_MIN
except ImportError:
    POST_RELEASE_DELAY_MIN = 1
try:
    from config import POST_RELEASE_EXPIRE_MIN
except ImportError:
    POST_RELEASE_EXPIRE_MIN = 360
try:
    from config import MORNING_ALERT_HOUR_SGT
except ImportError:
    MORNING_ALERT_HOUR_SGT = 12
try:
    from config import FF_HOT_CACHE_TTL_SECONDS
except ImportError:
    FF_HOT_CACHE_TTL_SECONDS = 90
try:
    from config import HOT_WINDOW_MIN
except ImportError:
    HOT_WINDOW_MIN = 30

# Reserved key in processed_events.json tracking the last day the morning alert
# fired (so the every-minute --watch loop sends it exactly once per day).
_MORNING_ALERT_KEY = "__morning_alert_date__"
from ff import fetch_today_events, compare_snapshots, assess_result, last_feed_size
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

    # Safety net: post analysis for any event already released by 12pm. The
    # processed-state dedup means the --watch job won't double-send these.
    _process_post_release(events, now_sgt)


# ---------------------------------------------------------------------------
# Post-release analysis — shared helper
# ---------------------------------------------------------------------------

def _process_post_release(events, now_sgt):
    """Send Template D (actual-vs-forecast) for each released event exactly once.

    Terminal states in processed_events.json:
      sent     — analysis delivered
      expired  — no `actual` published within POST_RELEASE_EXPIRE_MIN

    Any other state (pending / unseen) is re-checked every run. Crucially, an
    `actual` is sent whenever it appears — even past the expire window and even
    after a prior send failure — so a late or briefly-missed value still gets
    posted instead of being dropped forever.
    """
    processed = load_processed()
    changed = False

    for ev in events:
        key = ev["event_key"]
        ev_time = ev["time_sgt"]
        if ev_time is None:
            continue

        state = processed.get(key, {})
        if state.get("status") in ("sent", "expired"):
            continue

        minutes_since = (now_sgt - ev_time).total_seconds() / 60.0
        if minutes_since < POST_RELEASE_DELAY_MIN:
            continue

        actual = ev.get("actual", "").strip()
        if actual:
            result = assess_result(ev)
            msg = build_template_d(ev, result)
            if send_message(msg):
                processed[key] = {
                    "status": "sent",
                    "sent_at": now_sgt.isoformat(),
                    "minutes_after_release": round(minutes_since),
                }
                _log("Post-release sent: {} — {} ({:.0f} min after release).".format(
                    ev["title"], result["assessment"], minutes_since))
            else:
                # Keep it pending so the next tick retries the send.
                processed[key] = {
                    "status": "pending",
                    "attempts": state.get("attempts", 0) + 1,
                    "last_error": "send_failed",
                }
                _log("ERROR: send failed for {} — will retry next tick.".format(ev["title"]))
            changed = True
            continue

        # No actual yet.
        if minutes_since > POST_RELEASE_EXPIRE_MIN:
            processed[key] = {"status": "expired", "reason": "no_actual"}
            _log("Post-release: {} expired — no actual within {} min.".format(
                ev["title"], POST_RELEASE_EXPIRE_MIN))
        else:
            attempts = state.get("attempts", 0) + 1
            processed[key] = {"status": "pending", "attempts": attempts}
            _log("Post-release: {} — actual pending (attempt {}).".format(ev["title"], attempts))
        changed = True

    if changed:
        save_processed(processed)


# ---------------------------------------------------------------------------
# Workflow 2 — Watch (every 1 min): schedule changes + post-release
# ---------------------------------------------------------------------------

def _maybe_morning_alert(now_sgt, events):
    """Fire the daily news summary once, at/after MORNING_ALERT_HOUR_SGT.

    Self-gated in SGT so it is unaffected by the server clock (US/Eastern) or
    DST. If the send fails it is retried on the next tick (the day is only
    marked done once delivery succeeds).
    """
    if now_sgt.hour < MORNING_ALERT_HOUR_SGT:
        return

    today = now_sgt.date()
    meta = load_processed()
    if meta.get(_MORNING_ALERT_KEY) == today.isoformat():
        return

    remaining = [ev for ev in events if ev["time_sgt"] and ev["time_sgt"] > now_sgt]
    if remaining:
        msg = build_template_a(remaining, today)
        label = "Template A ({} upcoming events)".format(len(remaining))
    else:
        msg = build_template_b(today)
        label = "Template B (no upcoming events)"

    if send_message(msg):
        meta[_MORNING_ALERT_KEY] = today.isoformat()
        save_processed(meta)
        if events:
            save_snapshot(events)
        _log("Morning alert sent — {}.".format(label))
    else:
        _log("ERROR: Morning alert failed to send — will retry next tick.")


def _in_hot_window(events, now_sgt):
    """True if any event is in its release window and still awaiting an actual.

    We tighten FF polling only here so we catch a fresh `actual` quickly at
    release time without 429-ing the CDN the rest of the day.
    """
    for ev in events:
        t = ev["time_sgt"]
        if t is None:
            continue
        minutes_since = (now_sgt - t).total_seconds() / 60.0
        if -2 <= minutes_since <= HOT_WINDOW_MIN and not ev.get("actual", "").strip():
            return True
    return False


def run_watch():
    now_sgt = datetime.now(SGT)
    _log("Watch tick.")
    events = fetch_today_events()

    # Near a release, re-fetch on the hot path so a new actual shows up fast.
    if events and _in_hot_window(events, now_sgt):
        fresh = fetch_today_events(max_cache_age=FF_HOT_CACHE_TTL_SECONDS)
        if fresh:
            events = fresh

    # 1) Daily morning alert, self-gated to 12:00 SGT (TZ/DST-safe).
    _maybe_morning_alert(now_sgt, events)

    old_events = load_snapshot()
    if not events:
        if last_feed_size() == 0:
            _log("Watch: FF feed unreachable/empty (likely throttled) — keeping snapshot of {} items, skipping.".format(len(old_events)))
        else:
            _log("Watch: feed OK ({} events this week), no USD high/medium events for today.".format(last_feed_size()))
        return

    # 2) Schedule-change detection → Template C. compare_snapshots only matches
    #    on event_key (which embeds the date), so a stale prior-day snapshot
    #    yields no false changes — it just re-baselines on save below.
    for ch in compare_snapshots(old_events, events):
        if send_message(build_template_c(ch["title"], ch["old_time"], ch["new_time"])):
            _log("Schedule change sent: {} ({} → {}).".format(ch["title"], ch["old_time"], ch["new_time"]))
    save_snapshot(events)

    # 3) Post-release analysis → Template D
    _process_post_release(events, now_sgt)


# ---------------------------------------------------------------------------
# Legacy modes — superseded by --watch, kept so existing crons keep working
# ---------------------------------------------------------------------------

def run_watchdog():
    _log("Watchdog starting (legacy mode — prefer --watch).")
    events = fetch_today_events()
    old_events = load_snapshot()

    if not events and old_events:
        _log("Watchdog: fetch returned empty but snapshot has {} items — FF may be down. Skipping.".format(len(old_events)))
        return

    changes = compare_snapshots(old_events, events)
    if changes:
        for ch in changes:
            send_message(build_template_c(ch["title"], ch["old_time"], ch["new_time"]))
            _log("Schedule change sent: {} ({} → {}).".format(ch["title"], ch["old_time"], ch["new_time"]))
        save_snapshot(events)
    else:
        _log("Watchdog: no changes detected.")


def run_post_release():
    _log("Post-release starting (legacy mode — prefer --watch).")
    _process_post_release(fetch_today_events(), datetime.now(SGT))


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
    parser.add_argument("--watch", action="store_true",
                        help="Schedule changes + post-release analysis (cron: every 1 min)")
    parser.add_argument("--watchdog", action="store_true",
                        help="[legacy] Schedule-change check only")
    parser.add_argument("--post-release", action="store_true",
                        help="[legacy] Post-release analysis only")
    parser.add_argument("--test-all", action="store_true",
                        help="Send all four templates with sample data for review")

    args = parser.parse_args()

    if args.morning_alert:
        run_morning_alert()
    elif args.watch:
        run_watch()
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
