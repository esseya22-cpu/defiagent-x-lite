# Protocol decisions requiring instructor acknowledgement

The signed contract names Qwen2.5-1.5B-Instruct as a provisional zero-cost model resource. This
implementation selects Qwen3-4B-Instruct-2507 because the official card identifies a 4B
non-thinking Apache-2.0 model and reports materially stronger instruction-following and agent
benchmarks. Source: [Qwen model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).

This is not a result-driven change: it must be approved and frozen before final evaluation. If the
instructor requires the contract's original model, set `PRIMARY_MODEL_ID` to the approved exact
identifier, pin its immutable Hub revision, rerun the Week-4 model feasibility checks, and record
the decision before freezing final scenarios.

The contract text says “120 frozen agent plans” but its 2,640 execution formula requires separate
attacked plan instances for each attack seed: 60 clean plan instances plus 600 attacked plan
instances, replayed across four conditions. The final protocol should state 660 frozen plan
instances. This Week-4 artifact does not run or claim that final experiment.

