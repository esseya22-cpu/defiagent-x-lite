"""Deterministic unit fixtures; no archive or model access is used."""

from __future__ import annotations

import pytest

from defiagent_x_lite.constants import USDC, WETH
from defiagent_x_lite.domain import TrustedQuote, Workflow
from defiagent_x_lite.plans import reference_plan
from defiagent_x_lite.policy import build_policy

USER = "0x3333333333333333333333333333333333333333"
VAULT = "0x4444444444444444444444444444444444444444"


@pytest.fixture
def quote() -> TrustedQuote:
    return TrustedQuote(
        quote_id="quote-test",
        token_in=WETH,
        token_out=USDC,
        fee=3000,
        amount_in="100000000000000000",
        amount_out="300000000",
        block_number=20_000_000,
        pool_tick=200000,
        provider_note="clean",
    )


@pytest.fixture
def w1(quote: TrustedQuote):
    policy = build_policy(workflow=Workflow.W1, user=USER, vault=None, quote=quote)
    return reference_plan(quote=quote, policy=policy), policy


@pytest.fixture
def w2(quote: TrustedQuote):
    policy = build_policy(workflow=Workflow.W2, user=USER, vault=VAULT, quote=quote)
    return reference_plan(quote=quote, policy=policy), policy

