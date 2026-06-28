# Operation Eddy

Operation Eddy is a local-first Personal Information Platform for structured, connected records. The longer-term direction includes operational intelligence, but Stage 1 is deliberately limited to storing, organising and navigating information.

## Stage 1

Stage 1 supports People, Organisations, Locations, Projects, Documents, Assets and first-class Relationships. It includes CRUD, search, favourites, recent records, structured filters, maps, duplicate warnings and merges, document uploads, relationship integrity checks, and reviewed deterministic family inference.

Stage 1 excludes AI, chat, dispatcher architecture, decision support, automation, scheduling, login, WAN/mobile access and cloud dependencies. Map tiles and address lookup may use optional network services; core records remain usable without them.

## Documentation

- [Project goal](PROJECT_GOAL.md) — product direction and boundaries.
- [Stage 1 specification](docs/stage_1_spec.md) — current scope and acceptance criteria.
- [Roadmap](ROADMAP.md) — delivered, active, next and deferred work.
- [Architecture](docs/architecture.md) — current application structure and boundaries.
- [Database design](docs/database_design.md) — persistence and migration rules.
- [Ontology](docs/ontology.md) — entity and relationship semantics.
- [UI principles](docs/ui_principles.md) — interaction and presentation rules.
- [Architecture decisions](ARCHITECTURE_DECISIONS.md) — durable decisions and consequences.
- [Glossary](docs/glossary.md) — canonical project terminology.
- [Technical debt](docs/reviews/technical_debt_register.md) — unresolved, actionable debt only.
- [Build history](docs/build_log.md) — concise historical summaries by day.

## Run

```bash
python3 run.py
```

Open `http://127.0.0.1:8000`. The app creates `instance/eddy.sqlite3` and `instance/documents/` as needed. A fresh clone starts empty.

## Local data and privacy

Personal data belongs under the Git-ignored `instance/` directory. Databases, uploaded files, SQLite runtime files, logs, caches, exports and backups must not be committed. Root-level `data/`, `local-data/`, `exports/` and `backups/` are also ignored.

No sample data is required. Shareable fixtures must be clearly fictional, intentionally tracked and reviewed before commit.

## Test

```bash
python3 -m unittest discover -s tests
python3 -m compileall app run.py tests
```
