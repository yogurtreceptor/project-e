# Operation Eddy

Local-first Personal Operational Intelligence Platform.

## Stage 1

Stage 1 stores and navigates structured local information for People, Organisations, Locations, Projects, Documents, Assets and Relationships.

Stage 1 excludes AI, chat, dispatcher architecture, automation, scheduling, decision support, WAN/mobile access and login.

Codex is the current primary implementation and review tool. Repository docs and current code are the source of truth; the [implementation/refactor handoff](docs/reviews/claude_handoff.md) is retained as historical guidance.

## Run

```bash
python3 run.py
```

Open `http://127.0.0.1:8000`.

The app creates a local SQLite database at `instance/eddy.sqlite3`.
It also creates `instance/documents/` for uploaded Document files. A fresh clone
starts with an empty database: dashboard counts are zero and list, search, map and
relationship pages show empty states until records are added.

## Local data and privacy

Personal data belongs under the Git-ignored `instance/` directory. The database,
uploaded documents, SQLite runtime files, logs, caches, exports and backups are not
source files and must not be committed. Root-level `data/`, `local-data/`,
`exports/` and `backups/` directories are also ignored as safeguards for local
working copies.

No sample data is required. New developers obtain a clean schema simply by
starting the app; they can then create clearly fictional records through the UI if
they need development data. Intentionally shareable fixtures or examples should
live in a clearly named tracked test or example-data location, contain no real
personal information, and be reviewed before commit.

## Stop

Press `Ctrl+C` in the terminal running `python3 run.py`.

If a server is detached, find it with `lsof -i :8000` and stop the listed PID with `kill <pid>`.

## Test

```bash
python3 -m unittest discover -s tests
```
