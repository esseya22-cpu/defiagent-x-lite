"""Machine-readable environment manifest.

The course brief requires model, seed, code commit, policy version, latency, and environment
version for every run. This module records observable versions without collecting secrets.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


def _command(*args: str) -> str:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable"


def _package(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def environment_manifest() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": _command("git", "rev-parse", "HEAD"),
        "git_status_porcelain": _command("git", "status", "--porcelain"),
        "forge": _command("forge", "--version"),
        "cast": _command("cast", "--version"),
        "anvil": _command("anvil", "--version"),
        "uv": _command("uv", "--version"),
        "packages": {
            name: _package(name)
            for name in (
                "web3",
                "pydantic",
                "jsonschema",
                "rfc8785",
                "transformers",
                "torch",
                "outlines",
            )
        },
    }

