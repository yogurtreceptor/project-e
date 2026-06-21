# Operation Eddy

Local-first Personal Operational Intelligence Platform.

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
