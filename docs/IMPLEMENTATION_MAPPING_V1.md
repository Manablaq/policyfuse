# PolicyFuse v1 Implementation Mapping

Status: frozen implementation mapping derived from the v1 specification packet before contract tests.

## Concrete storage serialization

PolicyFuse v1 stores bounded small collections as deterministic strings:

- ordered rule identifiers: comma-separated ASCII identifiers in policy order;
- ordered rule texts: canonical compact JSON array with UTF-8 preserved;
- allowed action types: strictly sorted, unique comma-separated ASCII identifiers;
- accepted rule vector: canonical compact JSON array of objects in policy rule order.

Identifier character restrictions make comma-delimited identifier collections unambiguous. Rule text and rule-state JSON is parsed, validated, normalized, and re-serialized before storage or hashing.

## Collision-safe hashing

Every contract-domain hash uses GenVM `Keccak256`.

Fields are encoded as UTF-8 with an explicit decimal UTF-8 byte length followed by `:` and the field bytes. Hash inputs are therefore sequence-bound and do not rely on ambiguous raw concatenation.

The exact v1 domains are:

- `policyfuse-policy-v1`
- `policyfuse-sealed-policy-v1`
- `policyfuse-action-core-v1`
- `policyfuse-clarification-v1`
- `policyfuse-intent-v1`
- `policyfuse-rule-vector-v1`
- `policyfuse-authorization-v1`

The internal owner/slug lineage map key uses deterministic length-prefixed text rather than introducing an additional contract-domain hash.

## Concrete public write API

```text
create_policy(
    slug: str,
    version: u64,
    name: str,
    criteria: str,
    rule_ids_csv: str,
    rule_texts_json: str,
    allowed_action_types_csv: str,
    max_intent_lifetime_seconds: u64,
    max_authorization_lifetime_seconds: u64,
) -> str

supersede_policy(policy_id: str, replacement_policy_id: str) -> None

revoke_policy(policy_id: str) -> None

create_intent(
    policy_id: str,
    consumer: Address,
    action_type: str,
    action_core: str,
    clarification: str,
    deadline: u64,
) -> str

evaluate_intent(intent_id: str) -> str

repair_intent(
    intent_id: str,
    clarification: str,
    deadline: u64,
) -> str

expire_intent(intent_id: str) -> None
```

## Concrete public view API

```text
get_policy(policy_id: str) -> Policy
get_intent(intent_id: str) -> Intent
get_decision(intent_id: str) -> Decision
get_authorization(authorization_id: str) -> Authorization
get_verdict(intent_id: str) -> list[str]
is_authorization_current(authorization_id: str) -> bool
is_authorization_current_for(
    authorization_id: str,
    expected_consumer: Address,
    expected_action_core_digest: str,
) -> bool
get_latest_policy(owner: Address, slug: str) -> str
```

## Policy creation

The policy id binds owner, slug, and version.

The sealed fingerprint additionally binds name, criteria, ordered rule ids, canonical ordered rule texts, canonical sorted allowed action types, and both lifetime limits.

Creating a newer version updates only the latest-created lineage pointer. It does not implicitly supersede an older active version.

## Intent creation and repair

The action-core digest binds consumer, action type, and exact action payload.

The clarification digest binds the exact clarification bytes.

The intent id binds requester, policy id/fingerprint, action-core digest, clarification digest, deadline, predecessor id, and requester-local monotonic counter.

A separate full-intent digest uses the same `policyfuse-intent-v1` domain with an explicit `full` discriminator and seals the complete immutable semantic input including action payload, clarification, creation time, deadline, lineage, and counter.

Repair creates a new intent and only then marks the prior `REPAIR_REQUIRED` intent `SUPERSEDED`. The action core, requester, consumer, action type, policy id, and policy fingerprint are preserved exactly.

## Consensus mapping

Before `run_nondet_unsafe`, the contract validates lifecycle/deadline state and copies the policy and intent storage records to ordinary memory.

Leader and validator receive only memory snapshots. The leader must return exactly:

```json
{
  "kind": "RULE_VECTOR_V1",
  "rules": [
    {"id": "R1", "state": "PASS"}
  ]
}
```

Every rule must appear exactly once and in policy order. Allowed states are exactly `PASS`, `FAIL`, and `UNKNOWN`.

The validator independently invokes the same bounded semantic evaluation from the same frozen input and requires exact equality of the normalized consequential rule-state vector. Schema-only validation is not accepted.

Persistent writes occur only after `run_nondet_unsafe` returns.

## Deterministic consequence derivation

- any `FAIL` -> `DENY`
- otherwise any `UNKNOWN` -> `REPAIR_REQUIRED`
- otherwise -> `ALLOW`

`DENY` uses deterministic failure code `RULE_FAILED`.
`REPAIR_REQUIRED` uses deterministic repair code `RULE_UNKNOWN`.
`ALLOW` uses an empty failure code.

Only `ALLOW` creates an authorization.

## Authorization validity

Authorization creation time is the deterministic transaction time after semantic consensus returns.

`valid_until` is the minimum of:

- creation time plus the policy maximum authorization lifetime; and
- the immutable intent deadline.

Currentness is recomputed from durable state. It requires the policy to remain active, the exact policy fingerprint and intent/decision/authorization bindings to match, the intent to remain `ALLOW`, and transaction time to remain before `valid_until`.

There is no mutable consumed flag and no cross-contract execution surface in v1.

## Implementation exclusions

The contract has no payable method, no token or GEN transfer, no escrow, no arbitrary downstream write, no external web fetch, no confidence score, no floating-point tolerance, and no claim of atomic single-use consumption.
