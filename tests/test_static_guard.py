from copy import deepcopy

from defiagent_x_lite.domain import WorkflowPlan
from defiagent_x_lite.guards.static import static_guard


def _mutate(plan: WorkflowPlan, action_index: int, **updates: object) -> WorkflowPlan:
    data = plan.model_dump(mode="json")
    data["actions"][action_index].update(updates)
    return WorkflowPlan.model_validate(data)


def test_reference_w1_passes(w1) -> None:
    plan, policy = w1
    decision = static_guard(plan, policy)
    assert decision.allow
    assert decision.reason_codes == ("STATIC_POLICY_PASS",)


def test_recipient_poison_is_blocked(w1) -> None:
    plan, policy = w1
    attacked = _mutate(plan, 1, recipient="0x1111111111111111111111111111111111111111")
    decision = static_guard(attacked, policy)
    assert not decision.allow
    assert "SWAP_RECIPIENT" in decision.reason_codes


def test_unlimited_or_inexact_approval_is_blocked(w1) -> None:
    plan, policy = w1
    data = deepcopy(plan.model_dump(mode="json"))
    data["actions"][0]["amount"]["value"] = str(2**256 - 1)
    decision = static_guard(WorkflowPlan.model_validate(data), policy)
    assert not decision.allow
    assert "WETH_APPROVAL_NOT_EXACT" in decision.reason_codes


def test_w2_requires_symbolic_exact_received_amount(w2) -> None:
    plan, policy = w2
    data = deepcopy(plan.model_dump(mode="json"))
    data["actions"][2]["amount"] = {"kind": "fixed", "value": "1"}
    decision = static_guard(WorkflowPlan.model_validate(data), policy)
    assert not decision.allow
    assert "USDC_APPROVAL_NOT_EXACT_OUTPUT" in decision.reason_codes


def test_w2_minimum_share_predicate_is_frozen(w2) -> None:
    plan, policy = w2
    attacked = _mutate(
        plan,
        3,
        minimum_shares={"kind": "fixed", "value": str(int(policy.minimum_vault_shares) - 1)},
    )
    decision = static_guard(attacked, policy)
    assert not decision.allow
    assert "MINIMUM_SHARES_TOO_LOW" in decision.reason_codes

