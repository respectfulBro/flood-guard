import asyncio
import base64
import binascii
import logging
import os
import secrets
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .core import AREAS, ROOT, LIVE_VERSION, database, ingest, iso, list_areas, now_utc
from .evaluation import evaluate
from .daily_backtest import read_report
from .historical_rainfall import read_report as read_rainfall_report

DEMO_DB = ROOT / "data/demo.sqlite3"


async def collect_hourly():
    while True:
        try:
            results = await asyncio.to_thread(ingest)
            for result in results:
                if not result["success"]:
                    logging.error("Ingestion failed: %s", result)
        except Exception:
            logging.exception("Ingestion job failed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app):
    if not os.environ.get("PILOT_PASSWORD") or len(os.environ["PILOT_PASSWORD"]) < 16:
        raise RuntimeError("Set PILOT_PASSWORD to a private password of at least 16 characters")
    if os.environ.get("PILOT_DEMO") == "1":
        os.environ["FLOODGUARD_DB"] = str(DEMO_DB)
    with database():
        pass
    task = asyncio.create_task(collect_hourly()) if os.environ.get("PILOT_INGEST", "1") == "1" and os.environ.get("PILOT_DEMO") != "1" else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="FloodGuard Lagos research pilot", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def private_pilot(request: Request, call_next):
    user = password = ""
    try:
        scheme, value = request.headers.get("authorization", "").split(" ", 1)
        if scheme.lower() == "basic":
            user, password = base64.b64decode(value, validate=True).decode().split(":", 1)
    except (ValueError, UnicodeError, binascii.Error):
        pass
    expected = os.environ.get("PILOT_PASSWORD", "")
    user_ok = secrets.compare_digest(user.encode(), os.environ.get("PILOT_USER", "researcher").encode())
    password_ok = secrets.compare_digest(password.encode(), expected.encode())
    if not expected or not (user_ok and password_ok):
        return JSONResponse({"detail": "Private research pilot"}, 401,
                            headers={"WWW-Authenticate": 'Basic realm="FloodGuard pilot", charset="UTF-8"', "Cache-Control": "no-store"})
    if request.method not in ("GET", "HEAD"):
        if request.headers.get("x-pilot-request") != "1" or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Use the pilot application to submit reports"}, 403)
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"detail": "Expected JSON"}, 415)
        # Consume at most 32 KiB, including chunked requests.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 32768:
                return JSONResponse({"detail": "Report too large"}, 413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    area_id: str
    start_at: AwareDatetime
    end_at: AwareDatetime
    flooded: bool = Field(strict=True)
    cause: Literal["rainfall", "coastal", "river", "unknown"]
    description: str = Field(min_length=10, max_length=3000)
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def valid_observation(self):
        if self.area_id not in {a["id"] for a in AREAS}:
            raise ValueError("Unknown pilot area")
        if self.start_at > self.end_at or self.end_at > now_utc():
            raise ValueError("Observation must end after it starts and cannot be in the future")
        if not self.flooded and self.start_at == self.end_at:
            raise ValueError("Non-flood observation needs a monitoring interval")
        if self.source_url and len(str(self.source_url)) > 2000:
            raise ValueError("Source URL too long")
        return self


@app.get("/api/areas")
def areas():
    current = list_areas()
    if os.environ.get("PILOT_DEMO") != "1":
        return current
    report = read_report()
    if not report.get("available") or report.get("stale"):
        return [{**a, "risk_tier": "unavailable", "data_status": "unavailable", "forecast": None,
                 "demo_message": "Historical demo results are missing or stale. Run npm run demo to rebuild them."}
                for a in current]
    comparison = next((c for c in report.get("sensitivity", {}).get("comparisons", [])
                       if c["version"] == LIVE_VERSION), {})
    for a in current:
        case = next((c for c in comparison.get("cases", []) if c["area_id"] == a["id"] and c.get("forecast")), None)
        if not case:
            continue
        f = case["forecast"]
        a.update(data_status="historical", event_date=case["event_date"], last_check=None,
                 risk_tier=max((w["risk_tier"] for w in f["windows"]), key={"low": 0, "moderate": 1, "high": 2}.get),
                 forecast={**f, "source_run_at": f["run_at"], "grid_lat": f["grid"][0], "grid_lng": f["grid"][1],
                           "basis": "Cached historical model experiment; daily decision at midnight Lagos"})
    return current


@app.get("/api/areas/{area_id}")
def area(area_id: str):
    found = next((a for a in areas() if a["id"] == area_id), None)
    if not found:
        raise HTTPException(404, "Area not found")
    return found


@app.get("/api/areas/{area_id}/forecast")
def forecast(area_id: str):
    current = area(area_id)
    return {"data_status": current["data_status"], "forecast": current["forecast"]}


@app.post("/api/reports", status_code=201)
def report(observation: Report):
    with database() as conn:
        row = conn.execute("""INSERT INTO reports(area_id,start_at,end_at,flooded,cause,description,source_url,submitted_at)
                            VALUES (?,?,?,?,?,?,?,?)""",
                           (observation.area_id, iso(observation.start_at), iso(observation.end_at),
                            observation.flooded, observation.cause, observation.description,
                            str(observation.source_url) if observation.source_url else None, iso(now_utc())))
        return {"id": row.lastrowid, "status": "pending"}


@app.get("/api/evaluation")
def evaluation():
    return evaluate()


@app.get("/api/backtest")
def historical_backtest():
    return read_report()


@app.get("/api/historical-rainfall")
def historical_rainfall():
    return read_rainfall_report()


@app.get("/api/session")
def session():
    return {"demo": os.environ.get("PILOT_DEMO") == "1"}


@app.get("/api/health")
def health():
    current = list_areas()
    return {"status": "ok" if all(a["data_status"] == "fresh" for a in current) else "degraded",
            "areas": [{"id": a["id"], "data_status": a["data_status"], "last_check": a["last_check"]} for a in current]}


@app.get("/{path:path}")
def website(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API route not found")
    root = (ROOT / "dist").resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    if Path(path).suffix:
        raise HTTPException(404)
    if not (root / "index.html").exists():
        raise HTTPException(503, "Build the frontend with npm run build")
    return FileResponse(root / "index.html")
