# PolicyFuse v1 Bounds and Identifiers

Status: foundation draft to be frozen before implementation.

Every untrusted string or collection is bounded before it can affect nondeterministic execution.

## Text and collection bounds

Normative v1 bounds:

- policy slug: 1 to 64 ASCII identifier characters;
- policy name: 1 to 96 UTF-8 bytes;
- policy criteria: 1 to 4096 UTF-8 bytes;
- rules per policy: 1 to 12;
- rule id: 1 to 32 ASCII identifier characters;
- rule text: 1 to 1024 UTF-8 bytes each;
- aggregate rule text: maximum 8192 UTF-8 bytes;
- allowed action types: 1 to 12;
- action type: 1 to 64 ASCII identifier characters;
- action payload: 1 to 4096 UTF-8 bytes;
- clarification/context: 0 to 4096 UTF-8 bytes;
- maximum intent lifetime: 60 to 604,800 seconds;
- maximum authorization lifetime: 60 to 604,800 seconds.

Policy configuration may choose smaller lifetime bounds but never exceed these v1 hard caps.

NUL bytes are forbidden in free-form UTF-8 strings.

Identifier-like strings use a deliberately small character set suitable for canonical hashing.

## Canonical ordering

Rule ids are unique and stored in the policy-defined order.

Allowed action types are strictly sorted and unique.

The semantic result must contain exactly one state for every rule id in policy order. Reordered, missing, duplicate, or additional rule entries are invalid.

## Hash function

PolicyFuse v1 uses GenVM `Keccak256` for contract-domain identifiers and fingerprints.

All hashes use explicit domain separators and unambiguous length-prefixed field encoding or an equivalently collision-safe canonical encoding. Raw string concatenation without boundaries is forbidden.

## Domain separators

The implementation must use these exact conceptual domains:

- `policyfuse-policy-v1`
- `policyfuse-sealed-policy-v1`
- `policyfuse-action-core-v1`
- `policyfuse-clarification-v1`
- `policyfuse-intent-v1`
- `policyfuse-rule-vector-v1`
- `policyfuse-authorization-v1`

No identifier from one domain may be substituted for another.

## Policy id

Conceptually binds:

- policy owner address;
- slug;
- version.

The policy fingerprint additionally seals every immutable consequential policy field, including criteria, ordered rules, allowed action types, and both lifetime bounds.

A policy id identifies lineage/version. The fingerprint identifies exact policy content.

## Action-core digest

`policyfuse-action-core-v1` binds the exact consequence-bearing action core.

The action core includes at least:

- consumer address;
- action type; and
- exact action payload.

Clarification is intentionally excluded from the action-core digest so a repair can add or replace explanatory context without changing the underlying action.

Changing consumer, action type, or action payload changes the action-core digest and therefore requires a new unrelated intent rather than a repair revision.

## Clarification digest

`policyfuse-clarification-v1` binds the exact clarification/context bytes supplied for one intent revision.

Empty clarification is valid and hashes as an explicit empty field within the domain encoding.

## Intent id

`policyfuse-intent-v1` binds at least:

- requester address;
- policy id;
- policy fingerprint;
- action-core digest;
- clarification digest;
- deadline;
- predecessor intent id or an explicit empty predecessor marker; and
- requester-local monotonic counter.

The intent id therefore distinguishes repair revisions even when other fields are unchanged.

## Full intent digest

Where a separate full intent digest is stored, it binds the exact immutable intent fields that semantic consensus evaluated.

The authorization must reference this digest so later consumers can distinguish the exact revision that received `ALLOW`.

## Rule-vector digest

`policyfuse-rule-vector-v1` binds the complete ordered vector of:

`(rule_id, PASS|FAIL|UNKNOWN)`

for every policy rule.

The final consequential decision is derived from this exact accepted vector. The digest is evidence of which semantic classifications were consensus-bound.

## Authorization id

`policyfuse-authorization-v1` binds at least:

- policy id;
- policy fingerprint;
- intent id;
- requester;
- consumer;
- action type;
- action-core digest;
- full intent digest;
- rule-vector digest;
- authorization creation time; and
- `valid_until`.

Any material change produces a different authorization id.

## Time semantics

PolicyFuse uses deterministic transaction time for lifecycle checks.

GenLayer transaction time is deterministic across validators for a transaction and is suitable for immutable deadlines and authorization expiry checks.

Required inequalities:

- intent deadline must be strictly greater than creation time;
- intent lifetime must not exceed policy maximum intent lifetime;
- an intent cannot be semantically evaluated at or after its deadline;
- authorization `valid_until` must be strictly greater than authorization creation time;
- authorization lifetime must not exceed policy maximum authorization lifetime;
- authorization `valid_until` must not exceed the intent deadline.

## Counter semantics

A monotonic contract counter or requester-scoped counter may be used solely to guarantee deterministic uniqueness of otherwise identical intent creations.

The counter is not evidence of authorization currentness and is never interpreted semantically.

## No floating-point or confidence thresholds

v1 stores no confidence score and has no percentage tolerance.

Consequential semantic states are discrete exact strings: `PASS`, `FAIL`, and `UNKNOWN`.

Application outcomes are discrete exact strings: `ALLOW`, `DENY`, and `REPAIR_REQUIRED`.
