#!/usr/bin/env python3
"""Run Project E with a private, loopback-only PostgreSQL instance."""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "instance"
PGDATA = INSTANCE / "postgres" / "data"
SOCKET = INSTANCE / "postgres" / "socket"
LOG = INSTANCE / "postgres" / "postgres.log"
PORT = os.environ.get("PROJECT_E_POSTGRES_PORT", "55432")


def pg_bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    pg_config = shutil.which("pg_config")
    if pg_config:
        bindir = subprocess.check_output([pg_config, "--bindir"], text=True).strip()
        candidate = Path(bindir) / name
        if candidate.is_file():
            return str(candidate)
    raise SystemExit(f"PostgreSQL tool '{name}' was not found. Install PostgreSQL 16 or later.")


def run(*command: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=check, text=True)


def ready() -> bool:
    return subprocess.run(
        [pg_bin("pg_isready"), "-h", str(SOCKET), "-p", PORT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0


def initialise() -> None:
    SOCKET.mkdir(parents=True, exist_ok=True)
    if not (PGDATA / "PG_VERSION").exists():
        PGDATA.parent.mkdir(parents=True, exist_ok=True)
        run(pg_bin("initdb"), "-D", str(PGDATA), "--auth=trust", "--username=project_e")


def start_postgres() -> None:
    initialise()
    options = f"-h 127.0.0.1 -p {PORT} -k {SOCKET}"
    run(pg_bin("pg_ctl"), "-D", str(PGDATA), "-l", str(LOG), "-o", options, "start")
    for _ in range(100):
        if ready():
            return
        time.sleep(0.1)
    raise SystemExit(f"PostgreSQL did not become ready; inspect {LOG}")


def stop_postgres() -> None:
    if (PGDATA / "postmaster.pid").exists():
        run(pg_bin("pg_ctl"), "-D", str(PGDATA), "-m", "fast", "stop", check=False)


def database_url(database: str = "project_e") -> str:
    return f"postgresql://project_e@/{database}?host={SOCKET}&port={PORT}"


def ensure_database() -> None:
    result = subprocess.run(
        [pg_bin("psql"), database_url("postgres"), "-tAc", "SELECT 1 FROM pg_database WHERE datname='project_e'"],
        text=True, capture_output=True, check=True,
    )
    if result.stdout.strip() != "1":
        run(pg_bin("createdb"), "--maintenance-db", database_url("postgres"), "project_e")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-only", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.reset:
        if not args.yes and input("Delete the private Project E PostgreSQL cluster? [y/N] ").lower() != "y":
            return 1
        stop_postgres()
        shutil.rmtree(PGDATA, ignore_errors=True)
    start_postgres()
    try:
        ensure_database()
        env = os.environ | {"PROJECT_E_DATABASE_URL": database_url()}
        os.environ.update(env)
        python = ROOT / ".venv" / "bin" / "python"
        executable = str(python if python.exists() else Path(sys.executable))
        run(executable, "-c", "from app.db import initialise_database; initialise_database()")
        if args.test:
            return subprocess.run(
                [executable, "-m", "unittest", "discover", "-s", "tests"],
                cwd=ROOT, env=env,
            ).returncode
        if args.postgres_only:
            print(f"PostgreSQL ready: {database_url()}")
            return 0
        app = subprocess.Popen([executable, str(ROOT / "run.py")], cwd=ROOT, env=env)
        return app.wait()
    finally:
        stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
