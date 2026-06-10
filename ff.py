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

_CACHE_FILE = os.path.join("state", "ff_raw_cache.json")
_CACHE_TTL_SECONDS = 240  # 4 minutes — matches monitor project, avoids 429


def _load_raw_cache():
    # type: () -> Optional[List[Dict]]
    try:
        with open(_CACHE_FILE, "r") as f:
            data = json.load(f)
        age = (datetime.utcnow() - datetime.strptime(data["ts"], "%Y-%m-%dT%H:%M:%S")).total_seconds()
        if age < _CACHE_TTL_SECONDS:
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
    """Parse FF time (Eastern) and return SGT-aware datetime."""
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
    eastern_dt = EASTERN.localize(naive)
    return eastern_dt.astimezone(SGT)


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
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; WingsGoldBot/1.0)"},
        )
        if resp.status_code == 429:
            time.sleep(3)
            resp = requests.get(url, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0 (compatible; WingsGoldBot/1.0)"})
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


def fetch_today_events(force_fresh=False):
    # type: (bool) -> List[Dict[str, Any]]
    """Return today's USD High/Medium-impact events, sorted by SGT time."""
    today_sgt = datetime.now(SGT).date()

    raw = None
    if not force_fresh:
        raw = _load_raw_cache()
    if raw is None:
        raw = _fetch_raw(FF_URL)
        if raw:
            _save_raw_cache(raw)

    # Only try next week if today falls outside this week's data (e.g. weekend boundary)
    week_dates = set(_parse_ff_date(item.get("date", "")) for item in raw)
    if today_sgt not in week_dates:
        extra = _fetch_raw(FF_URL_NEXT, silent_404=True)
        raw = raw + extra

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
