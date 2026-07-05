# Contributing to Project E

Thanks for helping improve Project E. The project is in active development, so focused changes that preserve its local-first, entity-first design are easiest to review.

## Before starting

- Read [the project goal](PROJECT_GOAL.md), [the Stage 1 specification](docs/stage_1_spec.md) and [the contributor instructions](AGENTS.md).
- For a substantial feature or architectural change, open an issue before investing in implementation.
- Treat roadmap items as context, not as automatically approved work.
- Never include personal information, local databases, uploaded documents, logs, exports, backups or other runtime data in an issue, test fixture or commit.

## Development setup

Project E requires Python 3 and currently has no third-party Python dependencies.

```bash
python3 run.py
```

Open `http://127.0.0.1:8000`. Runtime data is created under the Git-ignored `instance/` directory.

## Making a change

1. Create a focused branch from the current default branch.
2. Follow the existing module boundaries and make the smallest maintainable change that solves the problem.
3. Add focused tests for changed behaviour and regressions.
4. Update every existing document made inaccurate by the change.
5. Keep commits concise and explain what changed and why. Do not mix unrelated changes.

Schema changes must be migration-safe. When applicable, test both fresh database creation and upgrading an existing schema. Consequential mutations must require explicit user confirmation, and Stage 1 changes must remain within the boundaries in `AGENTS.md`.

## Checks

Run the full checks before submitting:

```bash
python3 -m unittest discover -s tests
python3 -m compileall app run.py tests
```

For interface changes, also run the application and smoke-test the affected workflow where practical.

## Pull requests

Keep pull requests narrow enough to review. Explain the motivation, describe user-visible and technical changes, list verification performed, call out schema or privacy implications, and link related issues. Screenshots are useful when a visual change is easier to assess than describe.
