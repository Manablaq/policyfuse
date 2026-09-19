# PolicyFuse

PolicyFuse is a GenLayer Intelligent Contract for turning immutable, versioned natural-language policies into exact, machine-consumable semantic authorization decisions.

It answers one consequential question:

> Given this exact policy version and this exact proposed action, is the action allowed?

PolicyFuse is deliberately non-custodial. It does not hold funds, transfer assets, or execute downstream actions. It produces bounded authorization records that downstream applications may consume.

## Status

**v1 is implemented, release-frozen, tested, and live-verified.**

- Direct Mode regression: **36/36 tests passed**
- Supported-runtime verification: **five validators**, actual `FINALIZED` outcomes
- Live verification network: **GenLayer Studio Dev**
- Chain ID: `61997`
- Contract: `0xF5066aE61456b1ADEC4871Da1650F64F1aE5C43F`
- Published verification commit: `4e62920d5d0b7173c6c413faf95d66d99103337b`
- Final signer nonce after the authorized live-verification sequence: `182`
- Additional contract writes authorized by the R7-R1 packet: **0**

See [`docs/live-verification/STUDIO_DEV_FINAL.md`](docs/live-verification/STUDIO_DEV_FINAL.md) for the complete live-network record.

## Why PolicyFuse

Many applications need to evaluate a policy before allowing a consequential action. A free-form model response is not enough: the decision must be bound to the exact policy version, exact action, exact consumer, explicit validity window, and validator-agreed rule states.

PolicyFuse provides that binding.

Its v1 outcome model is:

| Outcome | Meaning | Authorization |
| --- | --- | --- |
| `ALLOW` | Every consequential rule passes | Created and bound to the exact consumer/action |
| `DENY` | At least one rule fails | None |
| `REPAIR_REQUIRED` | No rule fails, but at least one rule is unknown | None |

This prevents uncertainty or partial evidence from silently becoming authority.

## Core guarantees

PolicyFuse v1 is designed around the following invariants:

- **Immutable policy versions** — policy content and fingerprints do not change after creation.
- **Exact action binding** — authorization is tied to the canonical action digest.
- **Exact consumer binding** — an authorization cannot be replayed for a different consumer.
- **No tolerance on consequential states** — validator agreement is over exact rule outcomes.
- **No authorization on failure or uncertainty** — `DENY` and `REPAIR_REQUIRED` produce no authorization.
- **Currentness is recomputed from durable state** — supersession, revocation, expiry, or intent changes invalidate stale authority.
- **Bounded nondeterminism** — untrusted strings and collections are validated before entering validator evaluation.
- **Non-custodial design** — the contract never holds or transfers user assets.

## Architecture

A request moves through four durable layers:

1. **Policy** — an immutable versioned rule set owned by a policy owner.
2. **Intent** — an exact proposed action, consumer, clarification context, and deadline.
3. **Decision** — validator-agreed rule states and the resulting `ALLOW`, `DENY`, or `REPAIR_REQUIRED` outcome.
4. **Authorization** — created only for `ALLOW`, with exact bindings and an explicit validity window.

Historical records remain queryable, but historical existence never implies current authority.

For the detailed model, see:

- [`docs/SPEC_V1.md`](docs/SPEC_V1.md)
- [`docs/DATA_MODEL_V1.md`](docs/DATA_MODEL_V1.md)
- [`docs/STATE_MACHINE_V1.md`](docs/STATE_MACHINE_V1.md)
- [`docs/CONSENSUS_V1.md`](docs/CONSENSUS_V1.md)

## Public contract API

### Write methods

- `create_policy`
- `supersede_policy`
- `revoke_policy`
- `create_intent`
- `evaluate_intent`
- `repair_intent`
- `expire_intent`

### Read methods

- `get_policy`
- `get_intent`
- `get_decision`
- `get_authorization`
- `get_verdict`
- `is_authorization_current`
- `is_authorization_current_for`
- `get_latest_policy`

The exact signatures, lifecycle rules, and bounds are documented in [`docs/PUBLIC_API_V1.md`](docs/PUBLIC_API_V1.md) and [`docs/BOUNDS_AND_IDENTIFIERS_V1.md`](docs/BOUNDS_AND_IDENTIFIERS_V1.md).

## Verification

### Direct Mode

The release-frozen Direct Mode regression lives at:

```text
tests/direct/test_policy_fuse_v1.py
```

The final reviewer-readiness run passed:

```text
36 passed
```

### Supported runtime

PolicyFuse includes a clean-start five-validator Docker supported-runtime regression.

Run from the repository root:

```bash
./scripts/verify-supported-runtime.sh
```

The harness requires real `FINALIZED` state for all three consequential paths and persists each raw evaluation RPC response before decoding it.

Expected outcome markers include:

```text
POLICYFUSE_SUPPORTED_RUNTIME_VERIFY=PASS
ALLOW_FINALIZED=YES
DENY_FINALIZED=YES
REPAIR_REQUIRED_FINALIZED=YES
ALLOW_AUTHORIZATION_CURRENTNESS_RUNTIME_VERIFIED=YES
RAW_EVALUATION_RESPONSES_PRESERVED_BEFORE_DECODE=YES
FINAL_TRANSACTION_COUNT=8
FINAL_VALIDATOR_COUNT=5
```

See [`docs/SUPPORTED_RUNTIME_VERIFICATION_V1.md`](docs/SUPPORTED_RUNTIME_VERIFICATION_V1.md).

### Studio Dev live verification

The release-frozen contract was deployed and independently exercised on GenLayer Studio Dev, chain ID `61997`.

The verified paths were:

- `ALLOW` → `R1=PASS`, with authorization current for the exact consumer/action binding at final-certification time.
- `DENY` → `R1=FAIL`, `RULE_FAILED`, with no authorization.
- `REPAIR_REQUIRED` → `R1=UNKNOWN`, `RULE_UNKNOWN`, with no authorization.

The deployment and all seven authorized verification writes reached materialized `FINALIZED` state. No explicit finalization transaction was used.

Complete transaction hashes, rule-vector digests, integrity anchors, and reproducibility notes are published in [`docs/live-verification/STUDIO_DEV_FINAL.md`](docs/live-verification/STUDIO_DEV_FINAL.md).

## Repository layout

```text
contracts/
  policy_fuse.py                     Intelligent Contract

tests/
  direct/                            deterministic/adversarial Direct Mode tests
  supported_runtime/                 five-validator supported-runtime regression

scripts/
  verify-supported-runtime.sh        reproducible supported-runtime runner

docs/
  README.md                           documentation index
  SPEC_V1.md                         normative v1 behavior
  PUBLIC_API_V1.md                   public methods and lifecycle rules
  DATA_MODEL_V1.md                   persistent state model
  STATE_MACHINE_V1.md                lifecycle transitions and currentness
  CONSENSUS_V1.md                    leader/validator semantics
  BOUNDS_AND_IDENTIFIERS_V1.md       input bounds and identifiers
  THREAT_MODEL_V1.md                 security goals and threats
  IMPLEMENTATION_MAPPING_V1.md       spec-to-code mapping
  TOOLCHAIN_V1.md                    pinned development toolchain
  GENVM_ARTIFACT_PIN_V1.md           frozen GenVM artifact baseline
  SUPPORTED_RUNTIME_VERIFICATION_V1.md
  live-verification/                 final Studio Dev evidence and integrity files

requirements-dev.txt
requirements-lock.txt
```

## Toolchain and runtime profiles

PolicyFuse intentionally records separate version scopes:

- the **frozen local development / Direct Mode baseline** is documented in [`docs/TOOLCHAIN_V1.md`](docs/TOOLCHAIN_V1.md);
- the **supported-runtime execution profile** is documented in [`docs/SUPPORTED_RUNTIME_VERIFICATION_V1.md`](docs/SUPPORTED_RUNTIME_VERIFICATION_V1.md);
- the **Studio Dev live-verification CLI/runtime evidence** is documented in [`docs/live-verification/STUDIO_DEV_FINAL.md`](docs/live-verification/STUDIO_DEV_FINAL.md).

These are different verification layers, not conflicting version claims.

## Security model

PolicyFuse is a semantic authorization primitive, not an execution engine.

A downstream consumer remains responsible for the consequence attached to an authorization and for any application-specific replay protection beyond PolicyFuse currentness checks.

The full threat model is in [`docs/THREAT_MODEL_V1.md`](docs/THREAT_MODEL_V1.md).

## Documentation

Start with [`docs/README.md`](docs/README.md) for the complete documentation map.

## License

No license file is currently published in this repository. Consumers should not assume reuse rights beyond what the repository owner explicitly grants.
