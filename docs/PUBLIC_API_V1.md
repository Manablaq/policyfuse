# PolicyFuse v1 Public API

Status: foundation draft to be frozen before implementation.

The v1 API is contract-only and non-custodial. There is no payable method, no asset transfer method, and no automatic downstream execution method.

## Write methods

### `create_policy`

Creates an immutable policy version owned by `gl.message.sender_address`.

Conceptual inputs:

- `slug`
- `version`
- `name`
- `criteria`
- ordered rule ids
- ordered rule texts
- allowed action types
- maximum intent lifetime
- maximum authorization lifetime

Returns the deterministic policy id.

Requirements include unique rule ids, bounded fields, strictly increasing version within an owner/slug lineage, and a deterministic sealed policy fingerprint.

### `supersede_policy`

Owner-only.

Marks an `ACTIVE` policy `SUPERSEDED` and binds it to an already-created replacement policy owned by the same owner and belonging to the same slug lineage.

The replacement must have a greater version and be `ACTIVE`.

Returns no downstream authorization and performs no external call.

### `revoke_policy`

Owner-only.

Marks an `ACTIVE` policy `REVOKED`.

Revocation is terminal and immediately makes historical authorizations under that policy non-current.

### `create_intent`

Creates an immutable `OPEN` intent for one exact action.

Conceptual inputs:

- `policy_id`
- `consumer`
- `action_type`
- `action_core`
- `clarification`
- `deadline`

The method deterministically binds requester, policy fingerprint, consumer, action type, canonical action core, clarification, digests, deadline, and a monotonic requester-local nonce/counter into the intent id.

The action type must be allowed by the policy. Deadline must be future and within policy bounds.

### `evaluate_intent`

Evaluates one `OPEN` intent.

The method:

1. checks lifecycle and deadline deterministically;
2. snapshots all required persistent policy and intent fields into ordinary memory;
3. executes the bounded leader/validator semantic path;
4. validates complete exact rule coverage;
5. requires substantive validator agreement on the consequential rule-state vector;
6. derives `ALLOW`, `DENY`, or `REPAIR_REQUIRED` deterministically; and
7. writes decision/authorization state only after consensus returns.

Returns the derived decision string.

### `repair_intent`

Requester-only.

May be called only on `REPAIR_REQUIRED` before its deadline.

Creates a new immutable intent revision with new clarification/context while preserving the exact action core and all consequence-bearing bindings. The old intent becomes `SUPERSEDED`.

Returns the new intent id.

Repair must not mutate the old intent into a different action.

### `expire_intent`

May be called on `OPEN` or `REPAIR_REQUIRED` after the immutable deadline.

Materializes `EXPIRED`.

Expiry never manufactures a semantic `DENY`.

## View methods

### `get_policy`

Returns the stored policy record by policy id.

### `get_intent`

Returns the stored intent record by intent id.

### `get_decision`

Returns the decision record for a completed semantic evaluation.

A missing decision is an error.

### `get_authorization`

Returns the authorization record for an `ALLOW` intent.

A `DENY`, `REPAIR_REQUIRED`, `SUPERSEDED`, `OPEN`, or `EXPIRED` intent has no authorization.

### `get_verdict`

Returns a compact application-facing view of:

- intent status;
- decision;
- failure/repair code where applicable;
- authorization id where applicable; and
- validity bound.

### `is_authorization_current`

Returns whether the historical authorization is currently usable under PolicyFuse v1 currentness rules.

This checks policy lifecycle, exact stored bindings, intent lineage/state, and time validity.

### `is_authorization_current_for`

Inputs include:

- `authorization_id`
- expected `consumer`
- expected `action_core_digest`

Returns true only if `is_authorization_current` is true and both expected consequential bindings match exactly.

This is the preferred integration read for downstream consumers.

### `get_latest_policy`

Inputs:

- `owner`
- `slug`

Returns the latest-created policy id for that lineage.

Latest-created and active are deliberately distinct concepts.

## No hidden execution API

PolicyFuse v1 exposes no method that:

- transfers GEN or tokens;
- escrows value;
- invokes an arbitrary downstream write;
- claims atomic consumption in another contract;
- mutates an authorization into a consumed state; or
- treats provisional network acceptance as finality.

Applications attach their own consequences after checking a current authorization.

## Error philosophy

Input and lifecycle errors are deterministic `UserError` failures.

Semantic insufficiency is represented by `UNKNOWN` rule states and the durable `REPAIR_REQUIRED` decision, not by fabricating a denial.

Malformed or divergent nondeterministic results cause consensus rejection / no consequential write rather than a permissive fallback.
