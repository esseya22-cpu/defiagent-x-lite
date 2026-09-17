# Known limitations at Week 4

- The artifact has no production-safety claim and must not control real assets.
- The nine-point envelope samples states; it does not prove behavior between points.
- The USDC fork-holder address is validated at runtime but remains an external historical-state
  dependency. If unavailable at block 20,000,000, use the contract-approved fully local fixture
  and document that scope change before collecting final results.
- Qwen constrained generation prevents malformed syntax but can still select unsafe semantic
  values. That is intentional.
- The W2 one-to-one vault makes the share floor translatable into a stricter swap minimum. This is
  a required sensitivity analysis and narrows the mechanism claim.
- `raw_model_output` is the exact canonical constrained object exposed by Outlines, not hidden
  logits or chain-of-thought.
- Development attacks are calibration cases and cannot be reused as final frozen evaluation cases.

