import os
import json
from typing import List, Dict, Any
from config import STATE_DIR


def _ensure_dir():
    if not os.path.exists(STATE_DIR):
        os.makedirs(STATE_DIR)


def _snapshot_path():
    return os.path.join(STATE_DIR, "daily_snapshot.json")


def _processed_path():
    return os.path.join(STATE_DIR, "processed_events.json")


def load_snapshot():
    # type: () -> List[Dict]
    try:
        with open(_snapshot_path(), "r") as f:
            return json.load(f)
    except (IOError, ValueError):
        return []


def save_snapshot(events):
    # type: (List[Dict]) -> None
    _ensure_dir()
    serializable = []
    for ev in events:
        row = dict(ev)
        # datetime → ISO string so JSON can hold it
        if row.get("time_sgt") is not None and hasattr(row["time_sgt"], "isoformat"):
            row["time_sgt"] = row["time_sgt"].isoformat()
        if row.get("date") is not None and hasattr(row["date"], "isoformat"):
            row["date"] = row["date"].isoformat()
        serializable.append(row)
    with open(_snapshot_path(), "w") as f:
        json.dump(serializable, f, indent=2)


def load_processed():
    # type: () -> Dict[str, Any]
    try:
        with open(_processed_path(), "r") as f:
            return json.load(f)
    except (IOError, ValueError):
        return {}


def save_processed(data):
    # type: (Dict) -> None
    _ensure_dir()
    with open(_processed_path(), "w") as f:
        json.dump(data, f, indent=2)
