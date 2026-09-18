# PolicyFuse v1 Consensus Semantics

Status: foundation draft.

## Principle

Consequential authorization must depend only on fields that validators independently verify.

PolicyFuse will use a custom GenLayer leader/validator path. The leader result is never trusted merely because it is well-formed.

## Deterministic pre-consensus phase

Before entering nondeterminism, contract code must:

1. verify policy and intent lifecycle state;
2. verify caller permissions where applicable;
3. verify deadline/currentness bounds;
4. read the exact policy and intent from storage;
5. copy all storage-backed data needed by the nondeterministic path into ordinary memory; and
6. construct bounded frozen inputs for leader and validator evaluation.

## Leader result

The leader returns a bounded structured object whose consequential content is the complete ordered rule-state vector.

Conceptually:

```json
{
  "kind": "RULE_VECTOR_V1",
  "rules": [
    {"id": "R1", "state": "PASS"},
    {"id": "R2", "state": "UNKNOWN"}
  ]
}
```

Allowed states are exactly `PASS`, `FAIL`, and `UNKNOWN`.

## Validator behavior

A validator must:

1. reject non-return leader results unless an explicitly classified deterministic error path is being compared;
2. independently evaluate the same frozen policy and exact intent;
3. normalize its result using the same deterministic schema checks;
4. require exact rule identifier coverage;
5. require exact equality for every consequential rule state; and
6. return disagreement on malformed LLM output or substantive rule-state divergence.

Schema-only validation is forbidden because it would allow the leader to decide alone.

## Deterministic consequence derivation

After consensus returns an accepted rule vector, deterministic contract code derives:

- any `FAIL` -> `DENY`;
- otherwise any `UNKNOWN` -> `REPAIR_REQUIRED`;
- otherwise -> `ALLOW`.

No free-form reasoning, confidence score, tolerance band, or majority-over-rules may override this derivation.

## State mutation boundary

No persistent storage writes, cross-contract calls, or message emission occur inside the nondeterministic block.

Only after consensus returns may the contract persist the rule vector digest, decision, and any authorization state.

## Failure posture

Malformed or divergent LLM output should force disagreement/leader rotation rather than be converted into an authorization.

If the semantic input itself is insufficient but the nodes agree that one or more rules are `UNKNOWN`, the durable application outcome is `REPAIR_REQUIRED`.

If network consensus cannot be reached, no consequential PolicyFuse state is written.
