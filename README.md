# PolicyFuse

PolicyFuse is a reusable GenLayer Intelligent Contract for converting versioned natural-language mandates into exact, bounded, machine-consumable semantic authorizations.

Status: v1 Intelligent Contract implemented and release-frozen after Direct Mode, clean-start five-validator supported-runtime verification on the pinned GenLayer v0.121.24 / GenVM v0.2.16 linux/arm64 profile, and completed Studio Dev live-network verification. The verified live deployment is on GenLayer Studio Dev (chain ID 61997).

## v1 thesis

PolicyFuse answers one question:

> Given this exact proposed action and this exact immutable policy version, is the action allowed?

The contract is intentionally non-custodial. It does not hold funds, transfer assets, or execute downstream actions. It issues and verifies semantic authorization records that other applications can consume.

## Engineering order

1. Freeze specification, threat model, consensus semantics, and state machine.
2. Pin the current GenLayer toolchain and runtime.
3. Implement the smallest contract that satisfies the frozen model.
4. Lint/typecheck and source-security checks.
5. Direct Mode deterministic and adversarial tests.
6. Direct Mode validator agreement/disagreement tests.
7. Supported multi-validator runtime finality tests.
8. Reviewer-style adversarial audit.
9. Deploy the exact verified source only after all earlier gates pass.
10. Verify live-network finality and exact deployed-source identity.

This public repository contains the release-frozen v1 source, reproducible supported-runtime harness, and verified Studio Dev live-network evidence. Deployment and live-network finality verification are complete for the documented Studio Dev contract; see `docs/live-verification/STUDIO_DEV_FINAL.md`.

## Supported-runtime finality verification

PolicyFuse includes a clean-start five-validator supported-runtime regression using the pinned GenLayer v0.121.24 / GenVM v0.2.16 linux/arm64 execution profile.

Run `./scripts/verify-supported-runtime.sh` from the repository root.

The regression requires actual FINALIZED transactions for ALLOW, DENY, and REPAIR_REQUIRED, verifies ALLOW authorization currentness, and persists each raw evaluation RPC response before decoding it.

See `docs/SUPPORTED_RUNTIME_VERIFICATION_V1.md` for the exact runtime and evidence contract.

<!-- POLICYFUSE_STUDIO_DEV_LIVE_VERIFICATION_V1 -->
## Studio Dev live verification

PolicyFuse has completed its live-network verification on **GenLayer Studio Dev (chain ID 61997)** for contract `0xF5066aE61456b1ADEC4871Da1650F64F1aE5C43F`.

The deployment and all seven authorized verification writes reached materialized finality. The three consequence paths were independently verified as:

- `ALLOW` → `R1=PASS`, with authorization current for the exact consumer/action binding at final certification time.
- `DENY` → `R1=FAIL`, `RULE_FAILED`, with no authorization.
- `REPAIR_REQUIRED` → `R1=UNKNOWN`, `RULE_UNKNOWN`, with no authorization.

The final signer nonce is `182`; all seven R7-R1 write authorizations are consumed, and that packet authorizes no further contract writes.

See [`docs/live-verification/STUDIO_DEV_FINAL.md`](docs/live-verification/STUDIO_DEV_FINAL.md) for transaction hashes, rule-vector digests, reproducibility notes, and integrity anchors.
