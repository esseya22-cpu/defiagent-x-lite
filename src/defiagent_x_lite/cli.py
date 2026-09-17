"""Command-line entry points for the reproducible Week-4 workflow."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .canonical import write_json
from .config import Settings
from .domain import WorkflowPlan
from .gate import run_gate
from .manifest import environment_manifest
from .rpc import AnvilClient


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="defiagent-week4")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("export-schema", help="write the frozen WorkflowPlan JSON Schema")
    commands.add_parser("doctor", help="validate local safety boundary and pinned fork")
    commands.add_parser("model-revision", help="resolve the model's current immutable Hub SHA")

    gate = commands.add_parser("gate", help="run the complete Week-4 feasibility gate")
    gate.add_argument("--planner", choices=("qwen",), default="qwen")
    gate.add_argument("--repetitions", type=int, default=20)
    return parser


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def export_schema() -> int:
    output = Path("src/defiagent_x_lite/schemas/workflow-plan-v1.schema.json")
    write_json(output, WorkflowPlan.model_json_schema())
    _print({"written": str(output)})
    return 0

def doctor() -> int:
    settings = Settings()  # type: ignore[call-arg]  # populated from .env
    client = AnvilClient(settings)
    client.assert_fixture()
    report = environment_manifest()
    report.update(
        {
            "chain_id": client.w3.eth.chain_id,
            "block_number": client.w3.eth.block_number,
            "fork_block_hash": client.w3.eth.get_block(settings.fork_block)["hash"].hex(),
            "execution_rpc": settings.local_rpc_url,
            "broadcast_enabled": bool(settings.allow_broadcast),
            "archive_url_present": bool(settings.fork_rpc_url.get_secret_value()),
        }
    )
    _print(report)
    return 0


def model_revision() -> int:
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("install the model extra with `uv sync --extra model`") from exc
    settings = Settings()  # type: ignore[call-arg]
    info = HfApi().model_info(settings.primary_model_id)
    _print({"model_id": settings.primary_model_id, "immutable_revision": info.sha})
    return 0


def gate(repetitions: int) -> int:
    if repetitions != 20:
        raise ValueError("the signed Week-4 gate requires exactly 20 determinism repetitions")
    settings = Settings()  # type: ignore[call-arg]
    report = run_gate(settings=settings, repetitions=repetitions)
    _print(report)
    return 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        if args.command == "export-schema":
            code = export_schema()
        elif args.command == "doctor":
            code = doctor()
        elif args.command == "model-revision":
            code = model_revision()
        else:
            code = gate(args.repetitions)
    except Exception as exc:  # CLI boundary records a concise, non-secret failure.
        failure = {
            "ok": False,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(Path("results") / "last-cli-error.json", failure)
        _print(failure)
        code = 2
    raise SystemExit(code)


if __name__ == "__main__":
    main()
