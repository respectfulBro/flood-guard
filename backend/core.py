"""Archived rainfall screening. Thresholds are research defaults, not flood calibration."""
import hashlib
import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

UTC = timezone.utc
HOUR = timedelta(hours=1)
ROOT = Path(__file__).resolve().parent.parent
MODEL = "ecmwf_ifs"
VERSION = "rainfall-screen-v1"
# Uncalibrated screening thresholds in mm: moderate, high. Never tune in place.
THRESHOLDS = {1: (10, 20), 3: (20, 40), 6: (30, 60), 24: (50, 100)}
LIVE_VERSION = "rainfall-screen-sensitive-v2"
# User prioritizes detection. This is an exploratory policy, not fitted flood probability.
SENSITIVE_THRESHOLDS = {n: (moderate / 4, high) for n, (moderate, high) in THRESHOLDS.items()}


def thresholds_for(version):
    if version == VERSION:
        return THRESHOLDS
    if version == LIVE_VERSION:
        return SENSITIVE_THRESHOLDS
    raise ValueError(f"Unknown screening version: {version}")


def rescreen(forecast, version):
    """Apply versioned rules to existing rainfall peaks without changing the input weather."""
    thresholds = thresholds_for(version)
    windows = []
    for window in forecast["windows"]:
        peaks = window["peaks_mm"]
        level = max(2 if peaks[str(n)] >= high else 1 if peaks[str(n)] >= moderate else 0
                    for n, (moderate, high) in thresholds.items())
        factors = [f"Peak {n}h accumulation {peaks[str(n)]:g} mm" for n in thresholds
                   if peaks[str(n)] >= thresholds[n][0]]
        windows.append({**window, "risk_tier": ["low", "moderate", "high"][level],
                        "factors": factors or ["No screening threshold exceeded"]})
    return {**forecast, "version": version, "thresholds_mm": thresholds, "windows": windows,
            "probability": None, "confidence": {"status": "unvalidated",
                "label": "Flood likelihood not yet measured",
                "reason": "Too few independently reviewed storms and no representative non-flood sample. "
                          "Rainfall intensity is not a probability of flooding."}}
AREAS = [
    {"id": "lekki", "name": "Lekki", "lat": 6.4474, "lng": 3.4723},
    {"id": "ikosi-ketu", "name": "Ikosi-Ketu", "lat": 6.6018, "lng": 3.3895},
]
# ponytail: representative points, not flood extents; add verified polygons when available.
for area in AREAS:
    area.update(country="Nigeria", region="Lagos State", coverage="Candidate research area; no validated flood coverage")


def now_utc():
    return datetime.now(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def dt(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(UTC)


@contextmanager
def database(path=None):
    path = Path(path or os.environ.get("FLOODGUARD_DB", ROOT / "data/pilot.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inputs (
            id TEXT PRIMARY KEY, area_id TEXT NOT NULL, fetched_at TEXT NOT NULL,
            source_run_at TEXT NOT NULL, source_url TEXT NOT NULL, payload TEXT NOT NULL,
            metadata TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY, area_id TEXT NOT NULL, issued_at TEXT NOT NULL,
            issue_hour TEXT NOT NULL, input_id TEXT NOT NULL REFERENCES inputs(id),
            version TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(area_id, issue_hour, version)
        );
        CREATE TABLE IF NOT EXISTS ingestion (
            id INTEGER PRIMARY KEY, checked_at TEXT NOT NULL, area_id TEXT NOT NULL,
            success INTEGER NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY, area_id TEXT NOT NULL, start_at TEXT NOT NULL,
            end_at TEXT NOT NULL, flooded INTEGER NOT NULL, cause TEXT NOT NULL,
            description TEXT NOT NULL, source_url TEXT, submitted_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', storm_id TEXT, reviewer TEXT,
            review_note TEXT, reviewed_at TEXT, split TEXT NOT NULL DEFAULT 'prospective'
        );
        CREATE INDEX IF NOT EXISTS forecast_area_time ON forecasts(area_id, issued_at);
    """)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def rainfall_series(payload):
    if payload.get("utc_offset_seconds") != 0 or payload.get("hourly_units", {}).get("precipitation") != "mm":
        raise ValueError("Expected UTC hourly rainfall in millimetres")
    hourly = payload.get("hourly", {})
    times, values = hourly.get("time", []), hourly.get("precipitation", [])
    if not times or len(times) != len(values):
        raise ValueError("Missing or mismatched hourly rainfall")
    series = {}
    previous = None
    for stamp, value in zip(times, values):
        time = dt(stamp if stamp.endswith("Z") or "+" in stamp else stamp + "Z")
        if time.minute or time.second or time.microsecond or (previous and time != previous + HOUR):
            raise ValueError("Rainfall timestamps must be consecutive whole hours")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Missing or invalid rainfall measurement")
        series[time] = value
        previous = time
    return series


def predict(payload, issued_at, version=VERSION):
    series = rainfall_series(payload)
    start = issued_at.replace(minute=0, second=0, microsecond=0)
    if start < issued_at:
        start += HOUR
    windows = []
    for offset in range(0, 24, 6):
        begin = start + offset * HOUR
        ends = [begin + n * HOUR for n in range(1, 7)]
        try:
            peaks = {str(n): round(max(sum(series[t - k * HOUR] for k in range(n)) for t in ends), 2)
                     for n in THRESHOLDS}
            total = round(sum(series[t] for t in ends), 2)
        except KeyError as exc:
            raise ValueError("Insufficient rainfall coverage for 24-hour forecast and antecedent period") from exc
        windows.append({"start_at": iso(begin), "end_at": iso(begin + 6 * HOUR),
                        "rainfall_mm": total, "peaks_mm": peaks})
    return rescreen({"issued_at": iso(issued_at),
            "valid_from": windows[0]["start_at"], "valid_until": windows[-1]["end_at"],
            "windows": windows, "probability": None, "validation": "uncalibrated",
            "basis": "Forecast rainfall, including modelled antecedent rainfall; no local gauges or drainage model"}, version)


def fetch_json(url):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def ingest(path=None, fetch=fetch_json, clock=now_utc):
    """Each area's receipt is atomic; bad inputs never overwrite a good forecast."""
    outcomes = []
    for area in AREAS:
        stamp = clock()
        try:
            meta_url = f"https://api.open-meteo.com/data/{MODEL}/static/meta.json"
            meta = fetch(meta_url)
            run_at = datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC)
            available = datetime.fromtimestamp(meta["last_run_availability_time"], UTC)
            if not timedelta(0) <= stamp - run_at <= 18 * HOUR:
                raise ValueError("Source run is future-dated or older than 18 hours")
            if stamp - available < timedelta(minutes=10):
                raise ValueError("Source update is still propagating; retry next check")
            url = "https://api.open-meteo.com/v1/forecast?" + urlencode({
                "latitude": area["lat"], "longitude": area["lng"], "hourly": "precipitation",
                "models": MODEL, "past_days": 3, "forecast_days": 3, "timezone": "UTC"})
            payload = fetch(url)
            after = fetch(meta_url)
            if after["last_run_initialisation_time"] != meta["last_run_initialisation_time"]:
                raise ValueError("Source run changed during fetch; retry next check")
            stamp = clock()  # A forecast cannot be issued before its inputs arrived.
            raw = json.dumps(payload, sort_keys=True, allow_nan=False)
            key = hashlib.sha256((area["id"] + iso(stamp) + raw).encode()).hexdigest()
            with database(path) as conn:
                conn.execute("INSERT OR IGNORE INTO inputs VALUES (?,?,?,?,?,?,?)",
                             (key, area["id"], iso(stamp), iso(run_at), url, raw, json.dumps(meta)))
            forecast = predict(payload, stamp, LIVE_VERSION)
            forecast.update(source="Open-Meteo / ECMWF IFS", source_run_at=iso(run_at),
                            source_run_note="Model metadata at retrieval; not an exact run archive",
                            fetched_at=iso(stamp), grid_lat=payload["latitude"], grid_lng=payload["longitude"],
                            source_url=url)
            with database(path) as conn:
                conn.execute("INSERT OR IGNORE INTO forecasts(area_id,issued_at,issue_hour,input_id,version,payload) VALUES (?,?,?,?,?,?)",
                             (area["id"], iso(stamp), iso(stamp.replace(minute=0, second=0, microsecond=0)),
                              key, forecast["version"], json.dumps(forecast)))
                conn.execute("INSERT INTO ingestion(checked_at,area_id,success) VALUES (?,?,1)", (iso(stamp), area["id"]))
            outcomes.append({"area_id": area["id"], "success": True})
        except (ValueError, KeyError, TypeError, OSError) as exc:
            with database(path) as conn:
                conn.execute("INSERT INTO ingestion(checked_at,area_id,success,error) VALUES (?,?,0,?)",
                             (iso(stamp), area["id"], str(exc)[:500]))
            outcomes.append({"area_id": area["id"], "success": False, "error": str(exc)})
    return outcomes


def list_areas(path=None, now=None):
    now = now or now_utc()
    result = []
    with database(path) as conn:
        for area in AREAS:
            row = conn.execute("SELECT payload FROM forecasts WHERE area_id=? ORDER BY issued_at DESC,id DESC LIMIT 1", (area["id"],)).fetchone()
            check = conn.execute("SELECT checked_at,success,error FROM ingestion WHERE area_id=? ORDER BY id DESC LIMIT 1", (area["id"],)).fetchone()
            forecast = json.loads(row[0]) if row else None
            state = "unavailable"
            if forecast:
                state = "fresh"
                if (not timedelta(0) <= now - dt(forecast["fetched_at"]) <= 2 * HOUR
                        or not timedelta(0) <= now - dt(forecast["source_run_at"]) <= 18 * HOUR
                        or now >= dt(forecast["valid_until"])):
                    state = "stale"
            active = [w for w in forecast["windows"] if dt(w["end_at"]) > now] if forecast else []
            rank = {"low": 0, "moderate": 1, "high": 2}
            tier = max((w["risk_tier"] for w in active), key=rank.get, default="unavailable") if state == "fresh" else state
            result.append({**area, "risk_tier": tier, "data_status": state,
                           "forecast": forecast, "last_check": dict(check) if check else None})
    return result
