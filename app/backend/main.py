"""Match Day Poll: backend API.

Records votes in Postgres, keeps live totals in Redis, and serves results.

Endpoints
  GET  /health    liveness: is the process alive?  (never checks dependencies)
  GET  /ready     readiness: can it serve traffic?  (needs the database; Redis is optional)
  POST /vote      {"team": "India"}  -> stores one vote
  GET  /results   live totals (from Redis, rebuilt from Postgres when the cache is empty)
  GET  /version   which pod / node / version answered

Configuration comes from environment variables (see the docs for the full list).
"""
import os
import socket
import threading
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.pool
import redis
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

VERSION = os.getenv("APP_VERSION", "1.0")
BROKEN = os.getenv("BROKEN", "false").lower() == "true"          # a build that never becomes ready
TEAMS = [t.strip() for t in os.getenv("TEAMS", "India,Australia").split(",") if t.strip()]
CPU_COST_MS = int(os.getenv("CPU_COST_MS", "5"))                 # busy-work per vote, so load costs CPU
POD = socket.gethostname()
NODE = os.getenv("NODE_NAME", "unknown")
STARTED = time.time()

cache = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    # Not REDIS_PORT: Kubernetes creates REDIS_PORT=tcp://<ip>:6379 for a Service named "redis".
    port=int(os.getenv("CACHE_PORT", "6379")),
    socket_timeout=1,
    socket_connect_timeout=1,
    decode_responses=True,
)

_pool = None
_pool_lock = threading.Lock()


def pool():
    """Create the connection pool on first use, so the process starts even if the database is down."""
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                1, 8,
                host=os.getenv("DB_HOST", "postgres"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME", "poll"),
                user=os.getenv("DB_USER", "poll"),
                password=os.getenv("DB_PASSWORD", ""),
                connect_timeout=2,
            )
        return _pool


@contextmanager
def db():
    p = pool()
    conn = p.getconn()
    ok = False
    try:
        yield conn
        conn.commit()
        ok = True
    finally:
        if not ok:
            try:
                conn.rollback()
            except Exception:
                pass
        p.putconn(conn, close=not ok)   # a failed connection is discarded, not reused


def burn(ms: int) -> None:
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        pass


def whoami() -> dict:
    return {"pod": POD, "node": NODE, "version": VERSION}


def rebuild_totals() -> dict:
    """Count votes in Postgres and refill the Redis cache."""
    counts = {t: 0 for t in TEAMS}
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT team, COUNT(*) FROM votes GROUP BY team")
        for team, n in cur.fetchall():
            if team in counts:
                counts[team] = int(n)
    try:
        cache.hset("totals", mapping=counts)
    except redis.RedisError:
        pass
    return counts


app = FastAPI(title="matchday-poll backend")


class Vote(BaseModel):
    team: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(resp: Response):
    if BROKEN:
        resp.status_code = 503
        return {"ready": False, "reason": "broken build"}
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM votes LIMIT 1")
    except Exception:
        resp.status_code = 503
        return {"ready": False, "waiting_for": ["database"]}
    return {"ready": True}


@app.get("/version")
def version():
    return {**whoami(), "uptime_s": round(time.time() - STARTED)}


@app.post("/vote")
def vote(v: Vote):
    if v.team not in TEAMS:
        raise HTTPException(status_code=400, detail=f"unknown team, choose one of {TEAMS}")
    burn(CPU_COST_MS)
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO votes (team) VALUES (%s)", (v.team,))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    try:
        cache.hincrby("totals", v.team, 1)
    except redis.RedisError:
        pass   # the cache is rebuilt from the database on the next read
    return {"ok": True, "team": v.team, **whoami()}


@app.get("/results")
def results():
    source = "cache"
    totals = None
    try:
        raw = cache.hgetall("totals")
        if all(t in raw for t in TEAMS):
            totals = {t: int(raw[t]) for t in TEAMS}
    except redis.RedisError:
        pass
    if totals is None:
        source = "database"
        try:
            totals = rebuild_totals()
        except Exception:
            raise HTTPException(status_code=503, detail="database unavailable")
    total = sum(totals.values())
    out = {"teams": TEAMS, "totals": totals, "total": total, "source": source, **whoami()}
    if VERSION != "1.0":   # the new feature shipped in 1.1: percentages
        out["percent"] = {t: (round(100 * n / total, 1) if total else 0) for t, n in totals.items()}
    return out
