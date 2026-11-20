"""Operational commands, meant to run as Kubernetes Jobs.

  python tools.py migrate    create the tables (safe to run again)
  python tools.py reset      delete all votes and clear the Redis cache
  python tools.py snapshot   store the current totals in the snapshots table and print them
"""
import json
import os
import sys
import time

import psycopg2
import redis


def connect():
    last = None
    for attempt in range(15):          # the database may still be starting
        try:
            return psycopg2.connect(
                host=os.getenv("DB_HOST", "postgres"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME", "poll"),
                user=os.getenv("DB_USER", "poll"),
                password=os.getenv("DB_PASSWORD", ""),
                connect_timeout=3,
            )
        except psycopg2.OperationalError as exc:
            last = exc
            print(f"waiting for database ({attempt + 1}/15): {str(exc).strip()}", flush=True)
            time.sleep(2)
    print("database never became reachable", flush=True)
    raise SystemExit(f"{last}")


def migrate():
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS votes (
                 id BIGSERIAL PRIMARY KEY,
                 team TEXT NOT NULL,
                 voted_at TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS snapshots (
                 id SERIAL PRIMARY KEY,
                 taken_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                 total BIGINT NOT NULL,
                 totals JSONB NOT NULL)"""
        )
    print("migrate: tables ready", flush=True)


def reset():
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE votes")
    try:
        redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", "6379")),
                    socket_timeout=3, socket_connect_timeout=3).delete("totals")
    except redis.RedisError as exc:
        print(f"reset: could not clear the cache ({exc}); it is rebuilt on the next read", flush=True)
    print("reset: votes deleted, cache cleared", flush=True)


def snapshot():
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT team, COUNT(*) FROM votes GROUP BY team ORDER BY team")
        totals = {team: int(n) for team, n in cur.fetchall()}
        total = sum(totals.values())
        cur.execute("INSERT INTO snapshots (total, totals) VALUES (%s, %s)", (total, json.dumps(totals)))
    print(f"snapshot: total={total} totals={json.dumps(totals)}", flush=True)


COMMANDS = {"migrate": migrate, "reset": reset, "snapshot": snapshot}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(f"usage: python tools.py {'|'.join(COMMANDS)}")
    COMMANDS[sys.argv[1]]()
