"""Local Qwen planner with schema-constrained output.

Model choice and inference settings are sourced from the official model card:
https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
The card identifies a 4B Apache-2.0 non-thinking model, reports agent benchmarks, requires
Transformers >=4.51, and recommends temperature=0.7/top-p=0.8/top-k=20.

Outlines constrains open-model output to a Pydantic/JSON schema:
https://dottxt-ai.github.io/outlines/0.1.14/reference/generation/json/
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from time import perf_counter
from typing import Any, cast

from .canonical import canonical_bytes
from .constants import BPS_DENOMINATOR, FEE, SWAP_ROUTER, USDC, WETH
from .domain import TrustedQuote, Workflow, WorkflowPlan


def system_prompt() -> str:
    return (
        files("defiagent_x_lite.prompts")
        .joinpath("planner_system_v1.txt")
        .read_text(encoding="utf-8")
        .strip()
    )


def planner_payload(
    *, workflow: Workflow, user: str, vault: str | None, quote: TrustedQuote
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "workflow": workflow.value,
        "chain_id": 1,
        "fork_block": 20_000_000,
        "user": user,
        "vault": vault,
        "amount_in": quote.amount_in,
        "deadline_seconds": 300,
    }
    router_tolerance_bps = 100 if workflow is Workflow.W1 else 200
    quote_out = int(quote.amount_out)
    constraints = {
        "weth": WETH,
        "usdc": USDC,
        "router": SWAP_ROUTER,
        "fee": FEE,
        "swap_minimum_out": str(
            quote_out * (BPS_DENOMINATOR - router_tolerance_bps) // BPS_DENOMINATOR
        ),
        "minimum_vault_shares": (
            str(quote_out * 9_900 // BPS_DENOMINATOR) if workflow is Workflow.W2 else None
        ),
    }
    return {
        "user_request": request,
        "quote_tool_response": quote.model_dump(mode="json"),
        "planning_constraints": constraints,
        "output_schema": WorkflowPlan.model_json_schema(),
    }


def planner_messages(
    *, workflow: Workflow, user: str, vault: str | None, quote: TrustedQuote
) -> list[dict[str, str]]:
    payload = canonical_bytes(planner_payload(workflow=workflow, user=user, vault=vault, quote=quote))
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": f"INPUT_JSON:\n{payload.decode('utf-8')}"},
    ]


def render_prompt(
    *, workflow: Workflow, user: str, vault: str | None, quote: TrustedQuote
) -> str:
    """Stable human-readable representation; QwenPlanner stores the exact chat-templated input."""
    return "\n\n".join(
        f"{message['role'].upper()}:\n{message['content']}"
        for message in planner_messages(workflow=workflow, user=user, vault=vault, quote=quote)
    )




def _workflow_schema(workflow: Workflow, vault: str | None = None) -> str:
    """Workflow-specific schema with strict structural constraints.

    Constrained decoding removes ambiguity in structural fields (action_id
    references) that carry no experimental meaning, while leaving the
    poison-relevant and drift-relevant fields free:

      Locked (const):
        - WETH approve: token = WETH, spender = SwapRouter
        - USDC approve: token = USDC, amount.action_id = "swap"
        - Swap: action_id = "swap"
        - Deposit: assets.action_id = "swap", assets.field = "amount_out"

      Free (model chooses):
        - USDC approve: spender            (D04 poison target)
        - Swap: recipient                  (D03 poison target)
        - Deposit: vault, receiver, minimum_shares
        - All amounts, deadlines, fees
    """
    schema = WorkflowPlan.model_json_schema()
    defs = schema["$defs"]

    def copy_def(name: str) -> dict:
        return cast(dict, json.loads(json.dumps(defs[name])))

    def locked_output_reference() -> dict:
        return {
            "type": "object",
            "properties": {
                "kind": {"const": "output_reference", "type": "string"},
                "action_id": {"const": "swap", "type": "string"},
                "field": {"const": "amount_out", "type": "string"},
            },
            "required": ["kind", "action_id", "field"],
            "additionalProperties": False,
        }

    def weth_approve() -> dict:
        a = copy_def("ApproveAction")
        a["properties"]["token"] = {"const": WETH, "type": "string"}
        a["properties"]["spender"] = {"const": SWAP_ROUTER, "type": "string"}
        return a

    def usdc_approve() -> dict:
        a = copy_def("ApproveAction")
        a["properties"]["token"] = {"const": USDC, "type": "string"}
        a["properties"]["amount"] = locked_output_reference()
        # spender intentionally FREE for D04 poison
        return a

    def swap_action() -> dict:
        s = copy_def("SwapAction")
        s["properties"]["action_id"] = {"const": "swap", "type": "string"}
        return s

    def deposit_action() -> dict:
        d = copy_def("DepositAction")
        d["properties"]["assets"] = locked_output_reference()
        return d

    if workflow is Workflow.W1:
        schema["properties"]["actions"] = {
            "type": "array",
            "prefixItems": [weth_approve(), swap_action()],
            "minItems": 2,
            "maxItems": 2,
        }
        schema["properties"]["workflow"] = {"const": Workflow.W1.value, "type": "string"}
    else:
        schema["properties"]["actions"] = {
            "type": "array",
            "prefixItems": [
                weth_approve(),
                swap_action(),
                usdc_approve(),
                deposit_action(),
            ],
            "minItems": 4,
            "maxItems": 4,
        }
        schema["properties"]["workflow"] = {"const": Workflow.W2.value, "type": "string"}
    return json.dumps(schema)


@dataclass(frozen=True)
class PlannerResult:
    plan: WorkflowPlan
    raw_output: str
    rendered_prompt: str
    input_tokens: int | None
    output_tokens: int | None
    generation_ms: float


class QwenPlanner:
    """Lazy-loading adapter so core tests do not require the multi-gigabyte model extra."""

    def __init__(self, *, model_id: str, revision: str) -> None:
        if revision in {"", "main", "REPLACE_WITH_HF_COMMIT_SHA"}:
            raise ValueError("PRIMARY_MODEL_REVISION must be an immutable Hugging Face commit SHA")
        self.model_id = model_id
        self.revision = revision
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._sampler: Any | None = None
        self._generators: dict[tuple, Any] = {}

    def _load(self, workflow: Workflow, vault: str | None = None) -> Any:
        cache_key = (workflow, vault)
        if cache_key in self._generators:
            return self._generators[cache_key]
        from outlines import generate, models, samplers
        if self._tokenizer is None:
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:  # pragma: no cover - depends on optional GPU environment
                raise RuntimeError("install the model extra with `uv sync --extra model`") from exc
            tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            causal_model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                revision=self.revision,
                torch_dtype="auto",
                device_map="auto",
            )
            self._tokenizer = tokenizer
            self._model = models.Transformers(causal_model, tokenizer)
            self._sampler = samplers.multinomial(samples=1, temperature=0.7, top_k=20, top_p=0.8)
        assert self._model is not None
        assert self._sampler is not None
        self._generators[cache_key] = generate.json(
            self._model,
            _workflow_schema(workflow, vault),
            sampler=self._sampler,
        )
        return self._generators[cache_key]

    def plan(
        self,
        *,
        workflow: Workflow,
        user: str,
        vault: str | None,
        quote: TrustedQuote,
        seed: int,
    ) -> PlannerResult:
        generator = self._load(workflow, vault)
        assert self._tokenizer is not None
        messages = planner_messages(workflow=workflow, user=user, vault=vault, quote=quote)
        # Qwen's official quickstart requires its chat template with a generation prompt:
        # https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507#quickstart
        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        started = perf_counter()
        generated = generator(prompt, max_tokens=2_048, seed=seed)
        generation_ms = (perf_counter() - started) * 1_000
        plan = generated if isinstance(generated, WorkflowPlan) else WorkflowPlan.model_validate(generated)
        # Outlines returns the parsed constrained object. Preserve its exact canonical visible surface;
        # no hidden reasoning is requested or stored (course brief reproducibility requirement).
        raw = json.dumps(plan.model_dump(mode="json"), separators=(",", ":"), ensure_ascii=False)
        return PlannerResult(
            plan=plan,
            raw_output=raw,
            rendered_prompt=prompt,
            input_tokens=len(self._tokenizer.encode(prompt)),
            output_tokens=len(self._tokenizer.encode(raw)),
            generation_ms=generation_ms,
        )
