"""Command-line entry point for the X1 spatial evidence package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import (
    MANIFEST_PATH,
    SCENARIOS_PATH,
    acquire_source,
    cold_start_probe,
    inventory,
    load_manifest,
    probe_provider,
    serve_mbtiles,
)


def _write(value: object, output: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument(
        "--staging-root", default="instance/spatial-evidence", type=Path
    )
    command.add_argument("--manifest", default=MANIFEST_PATH, type=Path)
    subcommands = command.add_subparsers(dest="command", required=True)

    acquire = subcommands.add_parser("acquire", help="download and verify one public source")
    acquire.add_argument("source_key")

    inventory_parser = subcommands.add_parser(
        "inventory", help="inventory available inputs and disposable builds"
    )
    inventory_parser.add_argument("--output")

    probe = subcommands.add_parser("probe", help="probe a running loopback provider")
    probe.add_argument("provider", choices=("motis", "valhalla"))
    probe.add_argument("base_url")
    probe.add_argument("--scenarios", default=SCENARIOS_PATH, type=Path)
    probe.add_argument("--repetitions", default=3, type=int)
    probe.add_argument("--output")

    cold = subcommands.add_parser("cold-start", help="measure one local provider startup")
    cold.add_argument("provider", choices=("motis", "valhalla"))
    cold.add_argument("binary", type=Path)
    cold.add_argument("working_directory", type=Path)
    cold.add_argument("base_url")
    cold.add_argument("--config", type=Path)
    cold.add_argument("--output")

    serve = subcommands.add_parser(
        "serve-mbtiles", help="serve one evidence archive on loopback"
    )
    serve.add_argument("archive", type=Path)
    serve.add_argument("--port", default=18082, type=int)
    return command


def main() -> None:
    arguments = parser().parse_args()
    manifest = load_manifest(arguments.manifest)
    if arguments.command == "acquire":
        _write(acquire_source(arguments.source_key, arguments.staging_root, manifest), None)
    elif arguments.command == "inventory":
        _write(inventory(arguments.staging_root, manifest), arguments.output)
    elif arguments.command == "probe":
        _write(
            probe_provider(
                arguments.provider,
                arguments.base_url,
                arguments.scenarios,
                repetitions=arguments.repetitions,
            ),
            arguments.output,
        )
    elif arguments.command == "cold-start":
        _write(
            cold_start_probe(
                arguments.provider,
                arguments.binary,
                working_directory=arguments.working_directory,
                base_url=arguments.base_url,
                config=arguments.config,
            ),
            arguments.output,
        )
    elif arguments.command == "serve-mbtiles":
        serve_mbtiles(arguments.archive, arguments.port)


if __name__ == "__main__":
    main()
