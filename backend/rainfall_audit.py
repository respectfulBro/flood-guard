"""NOAA station observations for diagnosis only; never used as forecast inputs or flood labels."""
import csv
import hashlib
import io
import math
from datetime import timedelta
from pathlib import Path

from . import backtest as bt
from .core import AREAS, dt, iso, now_utc

STATION = "65201099999"
DOCUMENTATION = "https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt"


def precipitation(row):
    flag = row.get("PRCP_ATTRIBUTES", "").strip()
    try:
        inches = float(row["PRCP"])
    except (KeyError, ValueError, TypeError):
        inches = float("nan")
    if not math.isfinite(inches) or inches < 0 or inches >= 99.99 or flag not in "ABCDEFG" or not flag:
        return {"reported_mm": None, "quality": "missing_or_incomplete", "flag": flag}
    return {"reported_mm": round(inches * 25.4, 2),
            "quality": "24h_report" if flag in "DFG" else "partial_period", "flag": flag}


def distance_km(lat, lng, area):
    a, b = math.radians(lat), math.radians(area["lat"])
    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(area["lng"]-lng)/2)**2
    return round(6371 * 2 * math.asin(math.sqrt(h)), 1)


def run(files, root=None):
    place = bt.paths(root)
    _, events = bt.load_events(root)
    rows, sources = {}, []
    cache = place["base"] / "cache" / "rainfall"
    cache.mkdir(parents=True, exist_ok=True)
    for name in files:
        raw = Path(name).read_bytes()
        parsed = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if not parsed or any(r.get("STATION") != STATION for r in parsed):
            raise ValueError("Expected NOAA GSOD observations for Lagos/Ikeja station 65201099999")
        years = {dt(r["DATE"] + "T00:00:00Z").year for r in parsed}
        if len(years) != 1 or len({r["DATE"] for r in parsed}) != len(parsed):
            raise ValueError("Expected one year of unique daily station records per file")
        for row in parsed:
            float(row["LATITUDE"]), float(row["LONGITUDE"])
            if row["DATE"] in rows:
                raise ValueError("Overlapping station files")
            rows[row["DATE"]] = row
        year = years.pop()
        path = cache / f"{STATION}-{year}.csv"
        path.write_bytes(raw)
        sources.append({"url": f"https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{STATION}.csv",
                        "sha256": hashlib.sha256(raw).hexdigest(), "cache_file": str(path.relative_to(place["base"])),
                        "first_date": min(r["DATE"] for r in parsed), "last_date": max(r["DATE"] for r in parsed),
                        "records": len(parsed)})
    first = next(iter(rows.values()))
    lat, lng = float(first["LATITUDE"]), float(first["LONGITUDE"])
    cases = []
    for event in events:
        if event["status"] != "approved" or not event.get("event_date"):
            continue
        day = dt(event["event_date"] + "T00:00:00Z")
        nearby = []
        for offset in (-1, 0, 1):
            stamp = (day + timedelta(days=offset)).date().isoformat()
            row = rows.get(stamp)
            nearby.append({"date": stamp, **precipitation(row or {}), "record_present": row is not None})
        cases.append({"event_date": event["event_date"], "area_id": event["area_id"], "observations": nearby,
                      "station_distance_km": distance_km(lat, lng, next(a for a in AREAS if a["id"] == event["area_id"]))})
    result = {"station": {"id": STATION, "name": first["NAME"], "lat": lat, "lng": lng},
              "retrieved_at": iso(now_utc()), "sources": sources, "documentation": DOCUMENTATION, "cases": cases,
              "limitations": "Nearby airport observations, not gauges at either pilot location. NOAA daily totals can "
                  "include the previous day and do not exactly match midnight Lagos windows. F/D/G flags cover reported "
                  "24-hour totals; A/B/C/E cover partial periods. H/I and missing values are not zero rainfall. "
                  "No point-by-point forecast error or flood/non-flood label is inferred from this station. "
                  "Observations are used after the event for diagnosis only, never as historical forecast inputs."}
    bt.write_json(place["base"] / "rainfall-audit.json", result)
    return result
