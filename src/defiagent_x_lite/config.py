"""Runtime configuration with an enforced localhost execution boundary.

The split between an archive source and a localhost execution node follows Anvil fork mode:
https://getfoundry.sh/reference/anvil/
"""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import FORK_BLOCK


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fork_rpc_url: SecretStr
    fork_block: int = FORK_BLOCK
    local_rpc_url: str = "http://127.0.0.1:8545"
    anvil_mnemonic: SecretStr
    setup_time_offset_seconds: int = 1_000
    decision_time_offset_seconds: int = 2_000
    primary_model_id: str = "Qwen/Qwen3-4B-Instruct-2507"
    primary_model_revision: str = "main"
    allow_broadcast: int = Field(default=0, ge=0, le=0)
    results_dir: Path = Path("results")

    @field_validator("local_rpc_url")
    @classmethod
    def execution_rpc_must_be_loopback(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("LOCAL_RPC_URL must be an HTTP(S) URL")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, None)}
        except socket.gaierror as exc:
            raise ValueError("LOCAL_RPC_URL hostname does not resolve") from exc
        if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
            raise ValueError("execution is restricted to a loopback RPC")
        return value

    @field_validator("fork_block")
    @classmethod
    def block_is_frozen(cls, value: int) -> int:
        if value != FORK_BLOCK:
            raise ValueError(f"FORK_BLOCK must remain preregistered value {FORK_BLOCK}")
        return value

