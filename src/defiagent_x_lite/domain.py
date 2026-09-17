"""Typed experimental domain objects.

PACE motivates typed intents and deterministic policy checks before signing:
https://arxiv.org/html/2608.17220v1
Pydantic emits JSON Schema 2020-12 for the frozen interchange contract:
https://docs.pydantic.dev/latest/concepts/json_schema/
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Address = Annotated[str, StringConstraints(pattern=r"^0x[a-fA-F0-9]{40}$")]
UintString = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]*)$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Workflow(StrEnum):
    W1 = "W1_APPROVE_SWAP"
    W2 = "W2_APPROVE_SWAP_APPROVE_DEPOSIT"


class FixedAmount(StrictModel):
    kind: Literal["fixed"]
    value: UintString


class OutputReference(StrictModel):
    kind: Literal["output_reference"]
    action_id: str
    field: Literal["amount_out"] = "amount_out"


Amount = Annotated[FixedAmount | OutputReference, Field(discriminator="kind")]


class ApproveAction(StrictModel):
    kind: Literal["approve"]
    action_id: str
    token: Address
    spender: Address
    amount: Amount


class SwapAction(StrictModel):
    kind: Literal["swap_exact_input_single"]
    action_id: str
    router: Address
    token_in: Address
    token_out: Address
    fee: int
    recipient: Address
    amount_in: FixedAmount
    amount_out_minimum: FixedAmount
    deadline_seconds: int
    sqrt_price_limit_x96: Literal[0] = 0


class DepositAction(StrictModel):
    kind: Literal["deposit_erc4626"]
    action_id: str
    vault: Address
    asset: Address
    receiver: Address
    assets: OutputReference
    minimum_shares: FixedAmount


Action = Annotated[ApproveAction | SwapAction | DepositAction, Field(discriminator="kind")]


class WorkflowPlan(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    workflow: Workflow
    chain_id: Literal[1]
    fork_block: Literal[20_000_000]
    user: Address
    quote_id: str
    actions: tuple[Action, ...]

    @model_validator(mode="after")
    def action_ids_are_unique(self) -> WorkflowPlan:
        ids = [action.action_id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("action_id values must be unique")
        return self


class TrustedQuote(StrictModel):
    quote_id: str
    token_in: Address
    token_out: Address
    fee: int
    amount_in: UintString
    amount_out: UintString
    block_number: int
    pool_tick: int
    provider_note: str


class Policy(StrictModel):
    policy_version: Literal["week4-v1"] = "week4-v1"
    workflow: Workflow
    trusted_quote_id: str
    user: Address
    vault: Address | None
    amount_in: UintString
    trusted_quote_out: UintString
    swap_minimum_out: UintString
    minimum_vault_shares: UintString | None
    maximum_deadline_seconds: int = 300
    allowed_tokens: tuple[Address, ...]
    allowed_spenders: tuple[Address, ...]
    allowed_targets: tuple[Address, ...]


class GuardCondition(StrEnum):
    B0 = "B0_UNGUARDED"
    B1 = "B1_STATIC"
    B2 = "B2_CURRENT_STATE"
    M = "M_STATE_ENVELOPE"
    M_E = "M_MINUS_E"


class GuardDecision(StrictModel):
    condition: GuardCondition
    allow: bool
    reason_codes: tuple[str, ...]
    simulations: int
    latency_ms: float
    state_ticks: tuple[int, ...] = ()


class TransactionObservation(StrictModel):
    action_id: str
    kind: str
    to: Address
    sender: Address
    status: int
    gas_used: int
    transaction_hash: str
    resolved_amount: UintString | None = None


class StateObservation(StrictModel):
    weth_before: UintString
    weth_after: UintString
    usdc_before: UintString
    usdc_after: UintString
    weth_router_allowance_after: UintString
    usdc_vault_allowance_after: UintString | None
    vault_shares_before: UintString | None
    vault_shares_after: UintString | None
    calldata_matches_plan: bool
    unexpected_token_transfers: bool
    transactions: tuple[TransactionObservation, ...]


class Outcome(StrEnum):
    SAFE_COMPLETE = "SAFE_COMPLETE"
    SAFE_BLOCK = "SAFE_BLOCK"
    FALSE_BLOCK = "FALSE_BLOCK"
    UNSAFE_EXECUTE = "UNSAFE_EXECUTE"
    INCOMPLETE_REVERT = "INCOMPLETE_REVERT"
    INCOMPLETE_INVALID_PLAN = "INCOMPLETE_INVALID_PLAN"
    INFRA_FAILURE = "INFRA_FAILURE"


class Grade(StrictModel):
    outcome: Outcome
    safe: bool
    complete: bool
    predicate_results: dict[str, bool]
    violations: tuple[str, ...]


class EvidenceRecord(StrictModel):
    record_version: Literal["week4-v1"] = "week4-v1"
    run_id: str
    created_at_utc: datetime
    development_only: Literal[True] = True
    scenario_id: str
    seed: int
    model_id: str
    model_revision: str
    rendered_prompt: str
    prompt_sha256: str
    tool_response: TrustedQuote
    tool_response_sha256: str
    raw_model_output: str
    model_input_tokens: int | None
    model_output_tokens: int | None
    model_generation_ms: float
    plan: WorkflowPlan | None
    plan_sha256: str | None
    policy: Policy
    policy_sha256: str
    guard: GuardDecision
    observation: StateObservation | None
    grade: Grade
    condition_runtime_ms: float
    error: str | None

