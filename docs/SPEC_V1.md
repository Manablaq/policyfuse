# PolicyFuse v1 Specification

Status: foundation draft to be frozen before contract implementation.

## Purpose

PolicyFuse is a reusable semantic authorization primitive. It converts an immutable policy version plus an exact proposed action into one of three consequential outcomes:

- `ALLOW`
- `DENY`
- `REPAIR_REQUIRED`

The primitive does not execute the action. A downstream consumer decides what consequence, if any, follows from a current authorization.

## Actors

- **Policy owner** — creates immutable policy versions and may revoke or supersede them.
- **Requester** — submits an exact action intent for evaluation.
- **Consumer** — the address explicitly bound to the intent and expected to rely on the authorization.
- **Validators** — independently evaluate the same frozen policy and intent through GenLayer consensus.

## Core objects

### Policy

A policy version contains:

- policy identifier;
- owner address;
- version;
- optional predecessor policy identifier;
- human-readable name;
- bounded policy criteria;
- bounded ordered rule set with unique rule identifiers;
- bounded allowed action types;
- maximum intent lifetime;
- maximum authorization lifetime;
- immutable policy fingerprint; and
- lifecycle state.

Policy content is immutable after creation. Lifecycle state may become revoked or superseded. Historical policy data remains queryable.

### Intent

An intent binds:

- policy identifier and fingerprint;
- requester;
- consumer address;
- action type;
- exact action payload/context;
- canonical action digest;
- creation time;
- immutable deadline;
- lineage to a superseded intent when applicable; and
- current lifecycle state.

The consequential action fields may not be edited after intent creation.

### Decision

A completed evaluation stores:

- intent identifier;
- policy fingerprint;
- exact rule-state vector;
- rule-vector digest;
- consequential decision;
- evaluation timestamp; and
- authorization validity bound when the decision is `ALLOW`.

### Authorization

An authorization exists only for `ALLOW`. It binds the exact policy version, exact intent/action digest, requester, consumer, rule-vector digest, creation time, validity bound, and authorization nonce/identifier.

Historical existence is not equivalent to current usability.

## Rule semantics

Every policy rule has a unique stable rule identifier and normative rule text.

The nondeterministic evaluator must classify every rule exactly as:

- `PASS` — the proposed action satisfies the rule;
- `FAIL` — the proposed action violates the rule;
- `UNKNOWN` — the available intent context is insufficient or genuinely ambiguous.

The contract deterministically derives the consequential decision:

- any `FAIL` -> `DENY`;
- no `FAIL` and at least one `UNKNOWN` -> `REPAIR_REQUIRED`;
- every rule `PASS` -> `ALLOW`.

The LLM does not choose the final outcome independently of the rule vector.

## Repair semantics

`REPAIR_REQUIRED` is not a denial.

A requester repairs by creating a new immutable intent revision linked to the prior intent. The action core must remain bound to the same intended consequence, while clarification/context may be replaced under a new digest. The old intent remains historical and cannot become current again.

## Lifecycle

Intent states:

- `OPEN`
- `ALLOW`
- `DENY`
- `REPAIR_REQUIRED`
- `SUPERSEDED`
- `EXPIRED`

An open or repair-required intent can expire after its immutable deadline. Expiry never manufactures an `ALLOW` or `DENY`.

## Currentness

A historical `ALLOW` is current only when all required conditions hold, including:

- the bound policy is still active;
- the authorization has not expired;
- the intent has not been superseded or expired;
- the expected consumer matches;
- the expected action digest matches; and
- all contract-defined currentness guards pass.

Consumers must use a dedicated currentness/view method rather than treating historical authorization existence as sufficient.

## v1 exclusions

PolicyFuse v1 deliberately has:

- no payable entrypoint;
- no GEN custody;
- no token transfer;
- no escrow;
- no automatic downstream execution;
- no arbitrary external contract write;
- no web evidence fetch requirement;
- no claim that policy owners are truthful or benevolent;
- no claim that semantic interpretation is mathematically objective.

The primitive is an authorization decision layer, not an execution or custody layer.
