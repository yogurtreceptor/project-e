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

## Stop

Press `Ctrl+C` in the terminal running `python3 run.py`.

If a server is detached, find it with `lsof -i :8000` and stop the listed PID with `kill <pid>`.

## Test

```bash
python3 -m unittest discover -s tests
```
