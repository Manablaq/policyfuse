# PolicyFuse v1 State Machine

Status: v1 frozen state machine; implemented and verified.

## Design rule

PolicyFuse separates three different concepts:

1. policy lifecycle;
2. intent evaluation lifecycle; and
3. authorization currentness.

Historical records remain queryable. Historical existence never implies current authority.

## Policy lifecycle

Policy states:

- `ACTIVE`
- `SUPERSEDED`
- `REVOKED`

Allowed transitions:

- `ACTIVE -> SUPERSEDED`
- `ACTIVE -> REVOKED`

`SUPERSEDED` and `REVOKED` are terminal.

A policy version is immutable after creation. Superseding a policy creates a new immutable policy version and marks the prior policy `SUPERSEDED`. Revocation does not create a replacement.

Any authorization bound to a policy that is no longer `ACTIVE` is not current.

## Intent lifecycle

Intent states:

- `OPEN`
- `ALLOW`
- `DENY`
- `REPAIR_REQUIRED`
- `SUPERSEDED`
- `EXPIRED`

Allowed transitions:

- `OPEN -> ALLOW`
- `OPEN -> DENY`
- `OPEN -> REPAIR_REQUIRED`
- `OPEN -> EXPIRED`
- `REPAIR_REQUIRED -> SUPERSEDED`
- `REPAIR_REQUIRED -> EXPIRED`

`ALLOW`, `DENY`, `SUPERSEDED`, and `EXPIRED` are terminal.

An `OPEN` intent may be evaluated only before its immutable deadline.

If the deadline is reached before successful evaluation, any caller may materialize `EXPIRED`. Expiry never manufactures `ALLOW` or `DENY`.

## Rule-vector semantics

Every policy contains an ordered set of stable rule identifiers. Every semantic evaluation must classify every rule exactly once as:

- `PASS`
- `FAIL`
- `UNKNOWN`

The LLM does not independently choose `ALLOW`, `DENY`, or `REPAIR_REQUIRED`.

After consensus accepts the exact rule-state vector, deterministic contract code derives:

- any `FAIL` -> `DENY`;
- otherwise any `UNKNOWN` -> `REPAIR_REQUIRED`;
- otherwise every rule is `PASS` -> `ALLOW`.

No confidence score, tolerance band, majority-over-rules rule, or free-form prose may override this derivation.

## Repair

`REPAIR_REQUIRED` means the available context is insufficient or genuinely ambiguous. It is not a denial.

Repair creates a new immutable intent revision with:

- the same policy id and fingerprint;
- the same requester;
- the same consumer;
- the same action type;
- the same canonical action core and action-core digest;
- new clarification/context;
- a new clarification digest;
- a new intent id;
- a new immutable deadline; and
- lineage to the prior intent.

The prior `REPAIR_REQUIRED` intent becomes `SUPERSEDED`.

Repair may clarify context but may not substitute the consequential action. If the caller wants to change the action core, target, consumer, action type, or other consequence-bearing fields, a new unrelated intent must be created.

## Authorization creation

Only an `ALLOW` decision creates an authorization.

The authorization binds at least:

- policy id;
- policy fingerprint;
- intent id;
- requester;
- consumer;
- action type;
- action-core digest;
- full intent digest;
- rule-vector digest;
- creation time;
- `valid_until`; and
- authorization id.

Authorization lifetime is bounded by both the policy maximum and the intent deadline.

## Authorization currentness

Historical authorization existence is not enough.

A currentness check returns true only if all contract-defined conditions still hold, including:

- the authorization exists;
- the underlying decision is `ALLOW`;
- the bound policy is still `ACTIVE`;
- the policy fingerprint still matches;
- the bound intent remains the exact terminal `ALLOW` intent;
- the intent was not superseded;
- current transaction time is before `valid_until`;
- expected consumer matches;
- expected action-core digest matches; and
- any additional v1 identity checks pass.

Policy supersession or revocation invalidates currentness immediately without deleting history.

## Consumer binding

A consumer-specific authorization is not transferable to another consumer.

`is_authorization_current_for` must require the caller-supplied consumer and action-core digest to match the authorization exactly.

## Replay boundary

PolicyFuse v1 does not claim atomic single-use consumption across an arbitrary downstream action.

There is no mutable `consumed` flag in v1. PolicyFuse proves current semantic authorization for an exact consumer and action. A downstream consumer that requires single-use execution must maintain its own replay/nonce state around the action it executes.

This avoids pretending that two independent contracts can atomically consume the same authorization without an explicit cross-contract execution protocol.

## Policy latest-version semantics

Each owner-controlled policy slug has monotonically increasing versions.

`get_latest_policy(owner, slug)` returns the latest created policy id for that lineage. Latest does not imply active: callers must still inspect lifecycle state.

Creating a new version alone does not silently supersede the previous version. `supersede_policy` performs the explicit lifecycle transition and links the replacement.

## Failure posture

Malformed model output, incomplete rule coverage, duplicate rule ids, unknown rule ids, invalid states, validator divergence, or consensus failure must not be converted into `ALLOW`.

Before consensus succeeds, no consequential PolicyFuse decision or authorization state is written.
