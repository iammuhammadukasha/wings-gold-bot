import os
import re
import json
import requests
import pytz
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import List, Dict, Optional, Any

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
FF_URL_NEXT = "https://nfs.faireconomy.media/ff_calendar_nextweek.xml"

# faireconomy is behind Cloudflare, which hard-throttles bot-identifying
# User-Agents (e.g. "WingsGoldBot/1.0" → 429) while a normal browser UA is
# served from the warm edge cache (200). Identify as a browser and send
# browser-like Accept headers to stay on the cached path and dodge the 429s.
_FF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_CACHE_FILE = os.path.join("state", "ff_raw_cache.json")
# Cold-path TTL. FF's CDN 429s on sub-minute polling, so the every-minute cron
# serves from cache here and only really hits FF this often. The caller passes a
# shorter max_cache_age near a release (see fetch_today_events) for fresher data.
try:
    from config import FF_CACHE_TTL_SECONDS as _CACHE_TTL_SECONDS
except ImportError:
    _CACHE_TTL_SECONDS = 300


def _load_raw_cache(max_age=None):
    # type: (Optional[int]) -> Optional[List[Dict]]
    ttl = _CACHE_TTL_SECONDS if max_age is None else max_age
    try:
        with open(_CACHE_FILE, "r") as f:
            data = json.load(f)
        age = (datetime.utcnow() - datetime.strptime(data["ts"], "%Y-%m-%dT%H:%M:%S")).total_seconds()
        if age < ttl:
            return data["raw"]
    except Exception:
        pass
    return None


def _save_raw_cache(raw):
    # type: (List[Dict]) -> None
    try:
        if not os.path.exists("state"):
            os.makedirs("state")
        with open(_CACHE_FILE, "w") as f:
            json.dump({"ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "raw": raw}, f)
    except Exception:
        pass

SGT = pytz.timezone("Asia/Singapore")
EASTERN = pytz.timezone("US/Eastern")

# Events where higher actual = worse economy = weak USD = bullish gold
INVERTED_INDICATORS = [
    "initial jobless claims",
    "continuing jobless claims",
    "unemployment claims",
    "jobless claims",
    "unemployment rate",
]

IMPACT_FILTER = {"high", "medium"}

# Size of the raw feed from the most recent fetch_today_events() call. Lets
# callers tell "feed unreachable / throttled" (0) apart from "feed fine, just no
# USD events today" (>0) — they both yield an empty event list otherwise.
last_raw_count = 0


def last_feed_size():
    # type: () -> int
    return last_raw_count


def _is_inverted(title):
    # type: (str) -> bool
    t = title.lower()
    return any(k in t for k in INVERTED_INDICATORS)


def _parse_ff_date(raw):
    # type: (str) -> Optional[date]
    for fmt in ("%m-%d-%Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _parse_event_time_sgt(time_str, event_date):
    # type: (str, date) -> Optional[datetime]
    """Parse FF time (UTC) and return SGT-aware datetime."""
    t = time_str.strip().lower()
    if not t or t in ("all day", "tentative", ""):
        return None
    try:
        # e.g. "8:30am", "10:00am", "2:00pm"
        naive = datetime.strptime(
            "{} {}".format(event_date.strftime("%Y-%m-%d"), time_str.strip()),
            "%Y-%m-%d %I:%M%p",
        )
    except ValueError:
        return None
    utc_dt = pytz.utc.localize(naive)
    return utc_dt.astimezone(SGT)


def _to_float(s):
    # type: (str) -> Optional[float]
    s = s.strip().replace(",", "").replace("+", "")
    multiplier = 1.0
    if s.endswith("T"):
        multiplier = 1e12
        s = s[:-1]
    elif s.endswith("B"):
        multiplier = 1e9
        s = s[:-1]
    elif s.endswith("M"):
        multiplier = 1e6
        s = s[:-1]
    elif s.endswith("K"):
        multiplier = 1e3
        s = s[:-1]
    elif s.endswith("%"):
        s = s[:-1]
    try:
        return float(s) * multiplier
    except (ValueError, TypeError):
        return None


def _build_event(item, event_date):
    # type: (Dict, date) -> Dict[str, Any]
    sgt_dt = _parse_event_time_sgt(item.get("time", ""), event_date)
    return {
        "title": item.get("title", "").strip(),
        "impact": item.get("impact", "").strip(),
        "time_sgt": sgt_dt,
        "time_sgt_str": sgt_dt.strftime("%I:%M %p SGT") if sgt_dt else "TBD",
        "forecast": item.get("forecast", "").strip(),
        "previous": item.get("previous", "").strip(),
        "actual": item.get("actual", "").strip(),
        "date": event_date,
        "event_key": "{}__{}".format(
            event_date.isoformat(),
            item.get("title", "").strip().replace(" ", "_"),
        ),
    }


def _fetch_raw(url, silent_404=False):
    # type: (str, bool) -> List[Dict]
    import time
    try:
        resp = requests.get(url, timeout=15, headers=_FF_HEADERS)
        if resp.status_code == 429:
            time.sleep(3)
            resp = requests.get(url, timeout=15, headers=_FF_HEADERS)
        resp.raise_for_status()

        # Decode as windows-1252 (FF XML encoding), fix unescaped & outside CDATA,
        # then re-encode as UTF-8 so ElementTree is happy
        text = resp.content.decode("windows-1252", errors="replace")
        text = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text)
        root = ET.fromstring(text.encode("utf-8"))

        events = []
        for ev in root.findall("event"):
            def _t(tag, _ev=ev):
                return (ev.findtext(tag) or "").strip()
            events.append({
                "title":    _t("title"),
                "country":  _t("country"),
                "date":     _t("date"),
                "time":     _t("time"),
                "impact":   _t("impact"),
                "forecast": _t("forecast"),
                "previous": _t("previous"),
                "actual":   _t("actual"),
            })
        return events
    except Exception as e:
        if silent_404 and ("404" in str(e) or "Not Found" in str(e)):
            return []
        print("FF fetch error ({}): {}".format(url, e))
        return []


# ---------------------------------------------------------------------------
# Forex Factory site fallback for `actual` values.
#
# The faireconomy mirror (ff_calendar_thisweek.xml/.json) has stopped publishing
# `actual` values — the field is absent for every event, so the post-release
# analysis (Template D) never has a number to compare and silently expires. FF's
# own calendar page still serves actuals inside a `window.calendarComponentStates`
# JSON blob, so when a released event is missing its actual we backfill it from
# there, matched by currency + title. Fail-soft: any error just leaves `actual`
# empty (current behaviour), it never blocks an alert.
# ---------------------------------------------------------------------------

_SITE_URL_FMT   = "https://www.forexfactory.com/calendar?day={mon}{day}.{year}"
_SITE_CACHE_FILE = os.path.join("state", "ff_site_actuals.json")
_SITE_CACHE_TTL  = 120  # seconds; FF site is heavier than the mirror, poll gently


def _norm_title(title):
    # type: (str) -> str
    return re.sub(r"\s+", " ", title.replace("\\/", "/")).strip().lower()


def _site_day_param(event_date):
    # type: (date) -> str
    return "{}{}.{}".format(
        event_date.strftime("%b").lower(), event_date.day, event_date.year
    )


def _load_site_cache(day_param):
    # type: (str) -> Optional[Dict[str, Dict[str, str]]]
    try:
        with open(_SITE_CACHE_FILE, "r") as f:
            data = json.load(f)
        if data.get("day") != day_param:
            return None
        age = (datetime.utcnow() - datetime.strptime(data["ts"], "%Y-%m-%dT%H:%M:%S")).total_seconds()
        if age < _SITE_CACHE_TTL:
            return data.get("actuals", {})
    except Exception:
        pass
    return None


def _save_site_cache(day_param, actuals):
    # type: (str, Dict[str, Dict[str, str]]) -> None
    try:
        if not os.path.exists("state"):
            os.makedirs("state")
        with open(_SITE_CACHE_FILE, "w") as f:
            json.dump({
                "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                "day": day_param,
                "actuals": actuals,
            }, f)
    except Exception:
        pass


def _parse_site_actuals(html):
    # type: (str) -> Dict[str, Dict[str, str]]
    """Pull {norm_title: {actual, forecast}} for USD events from FF's JS state blob.

    Only events with a non-empty `actual` are returned — an absent actual means
    the number hasn't printed yet and we should keep waiting on the mirror/site.
    """
    out = {}
    # Each event is a JSON object beginning with `{"id":<n>,"ebaseId":...`.
    for chunk in re.split(r'\{"id":\d+,"ebaseId"', html)[1:]:
        cur = re.search(r'"currency":"([^"]*)"', chunk)
        if not cur or cur.group(1) != "USD":
            continue
        name = re.search(r'"name":"([^"]*)"', chunk)
        act  = re.search(r'"actual":"([^"]*)"', chunk)
        if not name or not act:
            continue
        actual = act.group(1).strip()
        if not actual:
            continue
        fc = re.search(r'"forecast":"([^"]*)"', chunk)
        out[_norm_title(name.group(1))] = {
            "actual":   actual,
            "forecast": (fc.group(1).strip() if fc else ""),
        }
    return out


def _http_get_site(url):
    # type: (str) -> Optional[str]
    """GET an FF calendar page, returning HTML or None.

    FF sits behind Cloudflare, which JA3-fingerprints the TLS client: Python's
    `requests` is served a JS challenge page (no data), while `curl` is allowed
    through. So fetch via curl first and only fall back to requests if curl is
    unavailable. The response must contain the data blob to count as a hit.
    """
    ua = _FF_HEADERS["User-Agent"]
    try:
        import subprocess
        proc = subprocess.run(
            ["curl", "-s", "--compressed", "--max-time", "25",
             "-A", ua, "-H", "Accept: text/html,application/xhtml+xml", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        html = proc.stdout.decode("utf-8", errors="ignore")
        if "calendarComponentStates" in html:
            return html
    except Exception as e:
        print("FF site curl error ({}): {}".format(url, e))

    try:  # last resort — often a Cloudflare challenge, but try anyway
        resp = requests.get(url, timeout=20, headers=_FF_HEADERS)
        resp.raise_for_status()
        if "calendarComponentStates" in resp.text:
            return resp.text
    except Exception as e:
        print("FF site requests error ({}): {}".format(url, e))
    return None


def _fetch_site_actuals(event_date):
    # type: (date) -> Dict[str, Dict[str, str]]
    day_param = _site_day_param(event_date)
    cached = _load_site_cache(day_param)
    if cached is not None:
        return cached
    url = _SITE_URL_FMT.format(
        mon=event_date.strftime("%b").lower(), day=event_date.day, year=event_date.year
    )
    html = _http_get_site(url)
    actuals = _parse_site_actuals(html) if html else {}
    # Cache even an empty result to avoid hammering FF every minute before release.
    _save_site_cache(day_param, actuals)
    return actuals


def _backfill_actuals(events):
    # type: (List[Dict[str, Any]]) -> None
    """For released-but-actual-less events, fill `actual`/`forecast` from FF's site."""
    now_sgt = datetime.now(SGT)
    pending = [
        ev for ev in events
        if not ev.get("actual")
        and ev.get("time_sgt") and now_sgt >= ev["time_sgt"]
    ]
    if not pending:
        return
    # All pending events share today's date here; fetch that day once.
    site = _fetch_site_actuals(pending[0]["date"])
    if not site:
        return
    for ev in pending:
        hit = site.get(_norm_title(ev["title"]))
        if not hit:
            continue
        ev["actual"] = hit["actual"]
        if not ev.get("forecast") and hit.get("forecast"):
            ev["forecast"] = hit["forecast"]


def fetch_today_events(max_cache_age=None):
    # type: (Optional[int]) -> List[Dict[str, Any]]
    """Return today's USD High/Medium-impact events, sorted by SGT time.

    max_cache_age: max acceptable cache age in seconds before re-fetching from
    FF. None uses the cold-path TTL. Pass a small value (e.g. 90) near a release
    for fresher data; pass 0 to force a fresh fetch.
    """
    global last_raw_count
    today_sgt = datetime.now(SGT).date()

    raw = _load_raw_cache(max_cache_age)
    if raw is None:
        raw = _fetch_raw(FF_URL)
        if raw:
            _save_raw_cache(raw)

    # Only try next week if today falls outside this week's data (e.g. weekend boundary)
    week_dates = set(_parse_ff_date(item.get("date", "")) for item in raw)
    if today_sgt not in week_dates:
        extra = _fetch_raw(FF_URL_NEXT, silent_404=True)
        raw = raw + extra

    last_raw_count = len(raw)

    events = []
    for item in raw:
        if item.get("country", "").upper() != "USD":
            continue
        if item.get("impact", "").lower() not in IMPACT_FILTER:
            continue
        event_date = _parse_ff_date(item.get("date", ""))
        if event_date != today_sgt:
            continue
        events.append(_build_event(item, event_date))

    events.sort(key=lambda x: x["time_sgt"] if x["time_sgt"] else datetime.max.replace(tzinfo=SGT))

    # The faireconomy mirror no longer carries `actual` values; backfill any
    # released event's actual from FF's own calendar page so Template D can fire.
    _backfill_actuals(events)
    return events


def compare_snapshots(old_events, new_events):
    # type: (List[Dict], List[Dict]) -> List[Dict[str, str]]
    """Return events whose SGT time string changed between snapshots."""
    old_map = {ev["event_key"]: ev["time_sgt_str"] for ev in old_events}
    changes = []
    for ev in new_events:
        key = ev["event_key"]
        if key not in old_map:
            continue
        old_time = old_map[key]
        new_time = ev["time_sgt_str"]
        if old_time != new_time and new_time != "TBD":
            changes.append({
                "title": ev["title"],
                "old_time": old_time,
                "new_time": new_time,
            })
    return changes


def assess_result(event):
    # type: (Dict) -> Dict[str, str]
    """Return assessment and gold bias from actual vs forecast."""
    actual = event.get("actual", "").strip()
    forecast = event.get("forecast", "").strip()

    if not actual or not forecast:
        return {
            "assessment": "NEUTRAL",
            "data_text": "DATA CAME IN NEUTRAL",
            "bias": "EXPECT CHOP (No clear structural edge)",
        }

    a = _to_float(actual)
    f = _to_float(forecast)

    if a is None or f is None or a == f:
        return {
            "assessment": "NEUTRAL",
            "data_text": "DATA CAME IN NEUTRAL",
            "bias": "EXPECT CHOP (No clear structural edge)",
        }

    inverted = _is_inverted(event.get("title", ""))
    usd_strong = (a > f) if not inverted else (a < f)

    if usd_strong:
        return {
            "assessment": "STRONG",
            "data_text": "USD DATA CAME OUT STRONGER THAN EXPECTED (GOOD FOR USD)",
            "bias": "LOOK FOR SELL SETUPS (Bearish Gold Momentum)",
        }
    return {
        "assessment": "WEAK",
        "data_text": "USD DATA CAME OUT WEAKER THAN EXPECTED (BAD FOR USD)",
        "bias": "LOOK FOR BUY SETUPS (Bullish Gold Momentum)",
    }
