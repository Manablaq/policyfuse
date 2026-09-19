# PolicyFuse v1 Threat Model

Status: v1 frozen threat model for the release-frozen implementation.

## Security goals

PolicyFuse must prevent an accepted authorization from being reused for a materially different action, policy version, consumer, or validity window.

The contract must preserve exact consensus-to-consequence binding: validator tolerance must never transform disagreement over a consequential rule state into an authorization.

## Primary threats

1. **Action substitution** — obtain approval for one action, then present it for another.
   - Bind authorization to an exact canonical action digest and consumer.

2. **Policy mutation** — alter rules after evaluation.
   - Policy content and fingerprint are immutable after creation.

3. **Policy downgrade** — reuse an authorization after revocation or supersession.
   - Currentness checks include active policy lifecycle state.

4. **Semantic ambiguity** — vague inputs cause validators to guess.
   - Use `UNKNOWN` and derive `REPAIR_REQUIRED`; do not force ambiguity into `ALLOW` or `DENY`.

5. **Malicious leader** — leader proposes a plausible but substantively false rule vector.
   - Validators independently evaluate the same frozen policy and intent and compare consequential rule states.

6. **Malformed LLM output** — missing rules, duplicate rules, unknown states, reordered or injected fields.
   - Strict deterministic schema normalization and exact rule-ID coverage are required before state mutation.

7. **Validator divergence** — validators disagree on a rule.
   - Reject the leader result; do not write consequential state. No numeric or semantic tolerance may cross an authorization boundary.

8. **Replay/stale authorization** — a historical approval is presented after its validity conditions changed.
   - Require dedicated currentness checks using policy state, deadline, consumer, and action digest.

9. **Deadline bypass** — evaluation or repair occurs after the immutable intent deadline.
   - Deterministic time guards execute before consequential writes.

10. **Unauthorized lifecycle mutation** — non-owner revokes/supersedes policy.
    - Owner-only policy lifecycle methods.

11. **Nondeterministic storage misuse** — validator closure reads persistent storage or writes state.
    - Snapshot required storage into ordinary memory before the nondeterministic block; all storage writes occur only after consensus returns.

12. **Scope creep into custody** — semantic authorization accidentally becomes asset custody/execution.
    - v1 has no payable surface, transfer, escrow, or automatic downstream write.

## Explicit non-guarantees

PolicyFuse does not prove that a policy is fair, lawful, wise, or authored by a trustworthy entity. It does not guarantee that LLM judgment is objectively correct. It guarantees the contract-defined binding, lifecycle, and consensus process around a bounded semantic decision.

A consumer remains responsible for the consequence it attaches to an authorization and for any application-specific replay protection beyond the contract's currentness checks.
