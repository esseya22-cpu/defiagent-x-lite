import pytest
from pydantic import ValidationError

from defiagent_x_lite.config import Settings


def test_loopback_execution_rpc_is_accepted() -> None:
    settings = Settings(
        _env_file=None,
        fork_rpc_url="https://archive.invalid/key",
        anvil_mnemonic="test mnemonic",
        local_rpc_url="http://127.0.0.1:8545",
    )
    assert settings.allow_broadcast == 0


def test_remote_execution_rpc_is_rejected() -> None:
    with pytest.raises(ValidationError, match="loopback"):
        Settings(
            _env_file=None,
            fork_rpc_url="https://archive.invalid/key",
            anvil_mnemonic="test mnemonic",
            local_rpc_url="https://8.8.8.8:8545",
        )


def test_fork_block_is_frozen() -> None:
    with pytest.raises(ValidationError, match="preregistered"):
        Settings(
            _env_file=None,
            fork_rpc_url="https://archive.invalid/key",
            anvil_mnemonic="test mnemonic",
            fork_block=20_000_001,
        )

