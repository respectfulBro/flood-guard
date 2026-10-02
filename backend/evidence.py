"""Local evidence collection and explicit review. No model fitting or inferred dry days."""
import csv
import hashlib
import io
import json
import math
import mimetypes
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from urllib.request import Request, urlopen

from . import backtest as bt
from .core import AREAS, dt, iso, now_utc

MAX_BYTES = 25 * 1024 * 1024


def base(root=None):
    return bt.paths(root)["base"]


def read(path, default):
    return bt.read_json(path) if path.exists() else default


def url(value):
    if not isinstance(value, str) or urlsplit(value).scheme not in ("http", "https") or not urlsplit(value).hostname:
        raise ValueError("Source URL must be an absolute HTTP(S) URL")
    if urlsplit(value).username or urlsplit(value).password:
        raise ValueError("Do not put credentials in source URLs")
    return value


def fetch(address):
    request = Request(url(address), headers={"User-Agent": "FloodGuardEvidence/1.0 (research archive)"})
    with urlopen(request, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Source exceeds 25 MiB; save a local copy for import")
        return raw, response.headers.get_content_type(), response.geturl()


class ArticleText(HTMLParser):
    """Readable evidence aid, not an article classifier or event extractor."""
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.metadata = {}

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag == "meta":
            attrs = dict(attrs)
            key = attrs.get("property", attrs.get("name", ""))
            if key in ("article:published_time", "og:title", "og:site_name"):
                self.metadata[key] = attrs.get("content", "")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def sources(root=None):
    return read(base(root) / "sources.json", {})


def verify_source(record, root=None):
    identity = hashlib.sha256((record["url"] + "\n" + record["sha256"]).encode()).hexdigest()
    if identity != record["id"]:
        raise ValueError("Source identity no longer matches URL and checksum")
    path = (base(root) / record["cache_file"]).resolve()
    if not path.is_relative_to((base(root) / "cache" / "sources").resolve()):
        raise ValueError("Source cache path escapes the evidence cache")
    if not path.is_file() or bt.sha256_file(path) != record["sha256"]:
        raise ValueError(f"Missing or altered source cache: {record['url']}")
    if record.get("text_file"):
        text_path = (base(root) / record["text_file"]).resolve()
        if (not text_path.is_relative_to(path.parent) or not text_path.is_file()
                or bt.sha256_file(text_path) != record.get("text_sha256")):
            raise ValueError("Missing or altered extracted source text")
    return path


def add_source(address, file=None, refresh=False, root=None, fetcher=fetch):
    local_raw = Path(file).read_bytes() if file else None
    address = url(address) if address else ("local:" + hashlib.sha256(local_raw).hexdigest() if local_raw else None)
    if not address:
        raise ValueError("Supply --url or a nonempty local --file")
    index = sources(root)
    matches = [s for s in index.values() if s["url"] == address]
    if matches and not file and not refresh:
        latest = max(matches, key=lambda s: s["retrieved_at"])
        verify_source(latest, root)
        return latest
    if file:
        raw = local_raw
        content_type = mimetypes.guess_type(str(file))[0] or "application/octet-stream"
        final = address
    else:
        raw, content_type, final = fetcher(address)
    if not raw:
        raise ValueError("Empty source")
    digest = hashlib.sha256(raw).hexdigest()
    source_id = hashlib.sha256((address + "\n" + digest).encode()).hexdigest()
    if source_id in index:
        verify_source(index[source_id], root)
        return index[source_id]
    path = base(root) / "cache" / "sources" / f"{digest}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)
    record = {"id": source_id, "url": address, "final_url": final if file else url(final), "sha256": digest,
              "cache_file": str(path.relative_to(base(root))), "bytes": len(raw),
              "content_type": content_type, "retrieved_at": iso(now_utc()),
              "import_method": "local_copy" if file else "http", "status": "unreviewed"}
    if "html" in content_type or content_type.startswith("text/"):
        text = raw.decode("utf-8", errors="replace")
        parser = ArticleText()
        if "html" in content_type:
            parser.feed(text)
            text = "\n".join(parser.parts)
        record["metadata"] = parser.metadata
        text_path = path.with_name(f"{source_id}.txt")
        text_path.write_text(text, encoding="utf-8")
        record["text_file"] = str(text_path.relative_to(base(root)))
        record["text_sha256"] = bt.sha256_file(text_path)
    index[source_id] = record
    bt.write_json(base(root) / "sources.json", index)
    return record


def collect(addresses, root=None, fetcher=fetch):
    results = []
    for address in sorted(set(addresses)):
        try:
            source = add_source(address, root=root, fetcher=fetcher)
            results.append({"url": address, "source_id": source["id"], "status": "cached"})
        except (ValueError, OSError) as exc:
            results.append({"url": address, "status": "unavailable", "error": str(exc)})
    path = base(root) / "collection.json"
    previous = read(path, [])
    bt.write_json(path, previous + [{"at": iso(now_utc()), "results": results}])
    return {"results": results, "failed": sum(r["status"] == "unavailable" for r in results)}


def discover(address, terms="flood,lekki,ketu,lagos", limit=20, root=None, fetcher=fetch):
    """Bounded RSS/Atom/sitemap discovery. Modification dates never become event dates."""
    if not 1 <= limit <= 100:
        raise ValueError("--limit must be 1..100 index documents")
    tokens = [t.strip().lower() for t in terms.split(",") if t.strip()]
    if not tokens:
        raise ValueError("Supply at least one discovery term")
    queue, visited, found, errors = [url(address)], set(), {}, []
    while queue and len(visited) < limit:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        try:
            source = add_source(current, root=root, fetcher=fetcher)
            tree = ET.fromstring(verify_source(source, root).read_bytes())
            kind = tree.tag.split("}")[-1]
            if kind not in ("sitemapindex", "urlset", "rss", "feed"):
                raise ValueError("Expected RSS, Atom, or XML sitemap")
            for entry in tree.iter():
                tag = entry.tag.split("}")[-1]
                if tag not in ("sitemap", "url", "item", "entry"):
                    continue
                fields = {child.tag.split("}")[-1]: child.text or "" for child in entry}
                link = fields.get("loc") or fields.get("link")
                if not link:
                    link = next((c.attrib.get("href") for c in entry if c.tag.split("}")[-1] == "link"
                                 and c.attrib.get("rel", "alternate") == "alternate"), None)
                if not link:
                    continue
                link = url(urljoin(current, link.strip()))
                if tag == "sitemap":
                    if urlsplit(link).hostname == urlsplit(address).hostname and link not in visited:
                        queue.append(link)
                    continue
                if any(t in (link + " " + fields.get("title", "")).lower() for t in tokens):
                    found[link] = {"url": link, "title": fields.get("title", ""),
                                   "index_date": fields.get("pubDate") or fields.get("published") or fields.get("lastmod"),
                                   "discovered_in": source["id"], "status": "pending"}
        except (ValueError, OSError, ET.ParseError) as exc:
            errors.append({"url": current, "error": str(exc)})
    result = {"query": tokens, "documents_checked": len(visited), "truncated": bool(queue),
              "candidates": sorted(found.values(), key=lambda r: r["url"]), "errors": errors,
              "note": "Candidate links only. Index dates are not flood dates; search is not exhaustive."}
    path = base(root) / "discovery.json"
    history = read(path, [])
    bt.write_json(path, history + [result])
    return result


def validate_event(event, root=None):
    if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"].strip():
        raise ValueError("Each observation needs an id")
    if event.get("area_id") not in {a["id"] for a in AREAS}:
        raise ValueError("Observation needs a pilot area_id")
    if event.get("status") not in bt.STATUS_VALUES:
        raise ValueError("Invalid review status")
    for field in ("start_at", "end_at"):
        if event.get(field):
            event[field] = iso(dt(event[field]))
    if event.get("start_at") and event.get("end_at") and dt(event["start_at"]) > dt(event["end_at"]):
        raise ValueError("Event start is after end")
    refs = event.get("source_ids", [])
    if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
        raise ValueError("source_ids must be a list of source IDs")
    index = sources(root)
    for ref in refs:
        if ref not in index:
            raise ValueError(f"Unknown source ID: {ref}")
        verify_source(index[ref], root)
    if event["status"] == "context":
        dt(event["start_at"]), dt(event["end_at"])
    if event["status"] != "approved":
        return
    for field in ("storm_id", "location", "description", "cause", "reviewer", "review_note", "location_note", "timing_note"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise ValueError(f"Approved observation needs {field}")
    if len(event["review_note"].strip()) < 10 or not refs:
        raise ValueError("Approval needs cached sources and a meaningful review note")
    start, end = dt(event["start_at"]), dt(event["end_at"])
    if end > now_utc():
        raise ValueError("Cannot approve future observations")
    if event.get("timing_precision") not in ("exact", "hour", "day"):
        raise ValueError("Coarse timing belongs in context, not approved observations")
    if event.get("location_precision") not in ("point", "street", "named_area"):
        raise ValueError("Approval needs evidence locating the observation in the pilot area")
    if not isinstance(event.get("flooded"), bool):
        raise ValueError("Approval needs flooded true/false")
    if event["flooded"] is False and (end <= start or event.get("observation_kind") != "monitored_interval"
                                      or not event.get("monitoring_method")):
        raise ValueError("A negative label needs an explicit monitored interval and method")
    if event.get("event_date"):
        from datetime import datetime
        datetime.strptime(event["event_date"], "%Y-%m-%d")
    if event["flooded"] and event["timing_precision"] in ("exact", "hour") and event.get("observation_kind") != "onset":
        raise ValueError("Hourly flood evidence must establish onset, not merely flood presence")
    if event.get("observation_kind") == "flood_present_on_day" and event["timing_precision"] != "day":
        raise ValueError("Flood presence on a day does not establish onset timing")


def import_events(file, root=None):
    incoming = bt.read_json(file)
    candidates = incoming.get("events") if isinstance(incoming, dict) else None
    if not isinstance(candidates, list):
        raise ValueError("Expected a JSON object with an events list")
    path = base(root) / "events.json"
    register = read(path, {"register": "backtest-events", "events": []})
    existing = {e["id"]: e for e in register["events"]}
    added = 0
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Each candidate must be an object")
        if any(k in candidate for k in ("review_history", "reviewer", "reviewed_at", "evidence_workflow")):
            raise ValueError("Import observations without review metadata; use event-review")
        row = {**candidate, "status": "pending", "evidence_workflow": 1}
        validate_event(row, root)
        # Preserve the original import so reruns remain idempotent after review.
        fingerprint = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        row["import_sha256"] = fingerprint
        if row["id"] in existing:
            if existing[row["id"]].get("import_sha256") != fingerprint:
                raise ValueError(f"Conflicting event ID: {row['id']}; use a review correction")
            continue
        existing[row["id"]] = row
        register["events"].append(row)
        added += 1
    bt.write_json(path, register)
    return {"imported": added, "total": len(register["events"])}


def review_event(event_id, file, root=None):
    decision = bt.read_json(file)
    allowed = {"status", "reviewer", "review_note", "correction_reason", "source_ids", "storm_id", "location",
               "location_precision", "location_note", "timing_note", "description", "cause", "cause_note",
               "start_at", "end_at", "timing_precision", "event_date", "flooded", "observation_kind",
               "monitoring_method", "satellite_evidence", "evidence", "groundsource_ids"}
    if not isinstance(decision, dict) or set(decision) - allowed:
        raise ValueError("Decision contains unsupported fields")
    if decision.get("status") not in ("approved", "rejected", "context"):
        raise ValueError("Decision status must be approved, rejected, or context")
    for field in ("reviewer", "review_note"):
        if not isinstance(decision.get(field), str) or len(decision[field].strip()) < (10 if field == "review_note" else 1):
            raise ValueError(f"Decision needs {field}")
    path = base(root) / "events.json"
    register = bt.read_json(path)
    prior = next((e for e in register["events"] if e["id"] == event_id), None)
    if prior is None or event_id == "template-never-approve":
        raise ValueError("Event not found or is the protected template")
    if prior.get("status") != "pending" and not decision.get("correction_reason", "").strip():
        raise ValueError("Changing a reviewed event requires correction_reason")
    updated = {**prior, **decision, "reviewed_at": iso(now_utc()), "evidence_workflow": 1}
    validate_event(updated, root)
    index = sources(root)
    updated["source_urls"] = sorted({index[s]["url"] for s in updated.get("source_ids", [])})
    updated["source_checksums"] = {s: index[s]["sha256"] for s in updated.get("source_ids", [])}
    updated["review_history"] = prior.get("review_history", []) + [{
        "revision": len(prior.get("review_history", [])) + 1,
        "before": {k: v for k, v in prior.items() if k != "review_history"},
        "decision": decision, "at": updated["reviewed_at"]}]
    register["events"][register["events"].index(prior)] = updated
    bt.write_json(path, register)
    return updated


def verify_events(events, root=None):
    index = sources(root)
    used = {}
    for event in events:
        if not event.get("evidence_workflow"):
            continue  # Existing source-reviewed records retain their legacy provenance.
        validate_event(event, root)
        for ref in event.get("source_ids", []):
            if event.get("status") == "approved" and event.get("source_checksums", {}).get(ref) != index[ref]["sha256"]:
                raise ValueError("Reviewed source checksum no longer matches")
            used[ref] = index[ref]
    return used


def rainfall_rows(raw):
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    seen = set()
    for row in rows:
        start, end = dt(row["start_at"]), dt(row["end_at"])
        lat, lng = float(row["latitude"]), float(row["longitude"])
        if end <= start or end > now_utc() or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("Invalid rainfall interval or coordinates")
        if not row.get("station_or_grid") or row.get("kind") not in ("gauge", "satellite") or not row.get("product_version"):
            raise ValueError("Rainfall needs station_or_grid, kind, and product_version")
        quality = row.get("quality")
        if quality not in ("valid", "missing", "suspect"):
            raise ValueError("Rainfall quality must be valid, missing, or suspect")
        value = float(row["rainfall_mm"]) if row.get("rainfall_mm", "").strip() else None
        if (value is not None and (not math.isfinite(value) or value < 0)) or (quality == "valid" and value is None):
            raise ValueError("Invalid rainfall amount; missing values are not zero")
        key = (row["kind"], row["product_version"], row["station_or_grid"], iso(start), iso(end))
        if key in seen:
            raise ValueError("Duplicate rainfall interval")
        seen.add(key)
        row.update(start_at=iso(start), end_at=iso(end), latitude=lat, longitude=lng, rainfall_mm=value)
    if not rows:
        raise ValueError("Empty rainfall CSV")
    return rows


def import_rainfall(file, source_id, root=None):
    """Canonical gauge/IMERG CSV; observations are diagnosis-only, not forecast inputs."""
    index = sources(root)
    if source_id not in index:
        raise ValueError("Unknown rainfall source ID")
    verify_source(index[source_id], root)
    raw = Path(file).read_bytes()
    rows = rainfall_rows(raw)
    digest = hashlib.sha256(raw).hexdigest()
    folder = base(root) / "cache" / "rainfall"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{digest}.csv").write_bytes(raw)
    path = base(root) / "rainfall-observations.json"
    imports = read(path, {})
    result = {"sha256": digest, "source_id": source_id, "source_sha256": index[source_id]["sha256"],
              "cache_file": str((folder / f"{digest}.csv").relative_to(base(root))), "observations": rows,
              "use": "diagnosis_only; never flood labels or historical forecast inputs"}
    if digest in imports and imports[digest] != result:
        raise ValueError("Rainfall file already imported with different provenance")
    imports[digest] = result
    bt.write_json(path, imports)
    return {"sha256": digest, "observations": len(rows), "use": result["use"]}


def check_rainfall(root=None):
    """Compare complete observation intervals to a previously available archived run."""
    from datetime import timedelta
    from .rainfall_audit import distance_km
    place = bt.paths(root)
    manifest = read(place["manifest"], {})
    imports = read(base(root) / "rainfall-observations.json", {})
    if not imports:
        raise ValueError("No rainfall observations; run backtest-rainfall-import first")
    index, cases, payloads = sources(root), [], {}
    for item in imports.values():
        source = index[item["source_id"]]
        verify_source(source, root)
        path = (base(root) / item["cache_file"]).resolve()
        if not path.is_relative_to((base(root) / 'cache' / 'rainfall').resolve()):
            raise ValueError("Rainfall cache path escapes its directory")
        if not path.is_file() or bt.sha256_file(path) != item["sha256"] or source["sha256"] != item["source_sha256"]:
            raise ValueError("Missing or altered rainfall provenance")
        observations = rainfall_rows(path.read_bytes())
        if observations != item["observations"]:
            raise ValueError("Rainfall register differs from its cached CSV")
        for obs in observations:
            start, end = dt(obs["start_at"]), dt(obs["end_at"])
            for position, area in enumerate(AREAS):
                case = {"area_id": area["id"], "observation": obs, "source_id": item["source_id"],
                        "csv_sha256": item["sha256"], "distance_km": distance_km(obs['latitude'], obs['longitude'], area),
                        "forecast_mm": None, "error_mm": None, "run_at": None, "reason": None}
                candidates = [k for k in manifest if bt.parse_key(k) + bt.ISSUE_DELAY <= start
                              and start - (bt.parse_key(k) + bt.ISSUE_DELAY) <= 18 * bt.HOUR]
                if obs["quality"] != "valid":
                    case["reason"] = "Observation is missing or suspect"
                elif any(t.minute or t.second or t.microsecond for t in (start, end)):
                    case["reason"] = "Interval must align to whole UTC hours; no subhourly interpolation"
                elif not candidates:
                    case["reason"] = "No archived run available within 18 hours before interval start"
                else:
                    key = max(candidates)
                    if key not in payloads:
                        run_file = place["runs"] / f"{key}.json"
                        if bt.sha256_file(run_file) != manifest[key]["sha256"]:
                            raise ValueError("Altered forecast cache")
                        raw = run_file.read_bytes()
                        bt.validate_run(raw, bt.parse_key(key))
                        payloads[key] = json.loads(raw)
                    hourly = payloads[key][position]["hourly"]
                    series = {dt(t if t.endswith('Z') else t + 'Z'): v
                              for t, v in zip(hourly['time'], hourly['precipitation'])}
                    hours = int((end - start).total_seconds() / 3600)
                    values = [series.get(start + timedelta(hours=h)) for h in range(1, hours + 1)]
                    case.update(run_at=iso(bt.parse_key(key)), simulated_issue_at=iso(bt.parse_key(key) + bt.ISSUE_DELAY),
                                cycle=bt.cycle_of(bt.parse_key(key)), run_sha256=manifest[key]['sha256'])
                    if not values or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
                        case["reason"] = "Forecast does not cover the observation interval"
                    else:
                        case['forecast_mm'] = round(sum(values), 6)
                        case['error_mm'] = round(case['forecast_mm'] - obs['rainfall_mm'], 6)
                cases.append(case)
    result = {"cases": cases, "matched_pairs": sum(c['error_mm'] is not None for c in cases),
              "limitations": "Rainfall diagnosis only, not flood skill. Forecast minus observed mm over (start,end]. "
                  "Distances and satellite grid representativeness must be reviewed; do not pool these comparisons "
                  "as neighborhood accuracy. Observations never enter historical forecast inputs."}
    bt.write_json(place['results'] / 'rainfall-comparison.json', result)
    return result
