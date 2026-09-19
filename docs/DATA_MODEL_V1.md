# PolicyFuse v1 Data Model

Status: v1 frozen data model; implemented by the release-frozen contract.

The implementation uses storage-compatible dataclasses and bounded `TreeMap` state.

## Persistent collections

Conceptual contract storage:

- `policies: TreeMap[str, Policy]`
- `latest_policy: TreeMap[str, str]`
- `intents: TreeMap[str, Intent]`
- `decisions: TreeMap[str, Decision]`
- `authorizations: TreeMap[str, Authorization]`

Additional deterministic counters or lineage maps may be added only if they preserve the frozen semantics.

## `Policy`

Required fields:

- `policy_id: str`
- `owner: Address`
- `slug: str`
- `version: u64`
- `name: str`
- `criteria: str`
- serialized ordered rule ids
- serialized ordered rule texts
- serialized sorted allowed action types
- `max_intent_lifetime_seconds: u64`
- `max_authorization_lifetime_seconds: u64`
- `fingerprint: str`
- lifecycle state
- replacement policy id or empty string

Policy content is immutable after creation. Only lifecycle state and explicit replacement linkage may change.

## `Intent`

Required fields:

- `intent_id: str`
- `requester: Address`
- `policy_id: str`
- `policy_fingerprint: str`
- `consumer: Address`
- `action_type: str`
- `action_core: str`
- `action_core_digest: str`
- `clarification: str`
- `clarification_digest: str`
- `full_intent_digest: str`
- predecessor intent id or empty string
- `created_at: u64`
- `deadline: u64`
- lifecycle status
- requester/counter uniqueness field

The action core and consequence-bearing bindings never mutate.

## `Decision`

Required fields:

- `intent_id: str`
- `policy_id: str`
- `policy_fingerprint: str`
- exact serialized ordered rule-state vector
- `rule_vector_digest: str`
- decision string
- repair/failure code or empty string
- `evaluated_at: u64`
- authorization id or empty string

The decision is written once after consensus and never edited.

## `Authorization`

Required fields:

- `authorization_id: str`
- `policy_id: str`
- `policy_fingerprint: str`
- `intent_id: str`
- `requester: Address`
- `consumer: Address`
- `action_type: str`
- `action_core_digest: str`
- `full_intent_digest: str`
- `rule_vector_digest: str`
- `created_at: u64`
- `valid_until: u64`

There is no mutable `consumed` field in v1.

Single-use execution is a downstream-consumer responsibility because PolicyFuse does not claim atomic consumption across an arbitrary external action.

## Serialization

Storage may use bounded delimiter-safe strings for small ordered collections if GenVM storage constraints make that simpler than nested persistent collections.

Any serialization used for rule ids, rule texts, action types, or rule states must:

- be deterministically parseable;
- reject delimiter ambiguity;
- preserve required order;
- enforce item-count limits;
- reject duplicates where prohibited; and
- be included exactly in the relevant sealed fingerprint/digest.

## Nondeterministic boundary

Before `run_nondet_unsafe`, deterministic code must:

1. load the exact policy and intent from persistent storage;
2. verify lifecycle state and deadline;
3. copy all storage-backed values required by leader and validator logic into ordinary memory;
4. construct bounded immutable memory snapshots; and
5. enter nondeterminism using only those snapshots plus nondeterministic LLM operations.

The leader and validator closures must not read persistent storage directly.

The leader and validator closures must not write persistent storage.

They must not perform cross-contract writes or emit messages.

After consensus returns, deterministic code validates the returned structure again and only then writes `Decision`, intent terminal state, and optional `Authorization`.

## Rule-vector representation

The normalized in-memory representation is conceptually:

```text
[
  ("R1", "PASS"),
  ("R2", "UNKNOWN"),
  ...
]
```

The exact policy-defined rule order is preserved.

Every vector must have the same number of entries as the policy and exactly matching rule ids.

Allowed states are only:

- `PASS`
- `FAIL`
- `UNKNOWN`

## Currentness reads

Currentness is recomputed from durable state at read time.

It is not represented by a stored mutable `current = true` flag.

This prevents stale historical authorization records from silently remaining usable after policy supersession, revocation, intent supersession, or expiry.

## Storage mutation discipline

No semantic evaluation partially writes durable decision state.

If consensus fails or validators disagree, the pre-existing intent state remains unchanged except for deterministic lifecycle transitions that occur before nondeterminism only when explicitly specified by the state machine.

The implementation must keep state writes after successful consensus whenever the write depends on nondeterministic judgment.
