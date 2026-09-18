# PolicyFuse supported-runtime verification

PolicyFuse includes a reproducible Docker supported-runtime regression for its consequential three-way evaluation path.

## Verified runtime

The permanent harness uses the exact execution profile proven during development:

- GenLayer simulator runtime: v0.121.24 image set
- GenVM: v0.2.16
- platform: linux/arm64
- chain ID: 61999
- finality window: 1 second
- committee: exactly five mock validators
- PolicyFuse py-genlayer runner: 1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6
- runner SHA-256: 0626f0af44103acd2b96e73a0e47c2a56a04313e6bd89e5852025a8f942a64c9

The Docker image references are pinned by registry digest.

The test does not use the obsolete sim_config second eth_sendRawTransaction parameter and does not pass a transaction context.

## Reproduce

From the repository root run:

    ./scripts/verify-supported-runtime.sh

The script creates an isolated Docker Compose project and removes it after the run.

The harness verifies the pinned Python toolchain, runtime image identities, GenVM version, PolicyFuse runner archive, empty starting chain, five-validator committee, contract deployment, deployment finality, deployed schema, one canonical policy and three independent intents.

The evaluation vectors are:

- ALLOW: R1 PASS, R2 PASS
- DENY: R1 PASS, R2 FAIL
- REPAIR_REQUIRED: R1 PASS, R2 UNKNOWN

Every evaluation must reach actual FINALIZED state.

ALLOW must create a live authorization and both authorization-currentness checks must return true.

DENY must return RULE_FAILED and create no authorization.

REPAIR_REQUIRED must return RULE_UNKNOWN and create no authorization.

For each evaluation, the exact raw gen_getStudioTransactionByHash HTTP response body is written to the evidence directory before the first JSON decoding of that response.

Evidence is written under:

    .artifacts/supported-runtime/<UTC-run-id>/

The artifacts directory is ignored by Git. Each successful run also records runtime logs and a SHA256SUMS evidence manifest.

The expected final markers include:

    POLICYFUSE_SUPPORTED_RUNTIME_VERIFY=PASS
    ALLOW_FINALIZED=YES
    DENY_FINALIZED=YES
    REPAIR_REQUIRED_FINALIZED=YES
    ALLOW_AUTHORIZATION_CURRENTNESS_RUNTIME_VERIFIED=YES
    RAW_EVALUATION_RESPONSES_PRESERVED_BEFORE_DECODE=YES
    FINAL_TRANSACTION_COUNT=8
    FINAL_VALIDATOR_COUNT=5
    ISOLATED_STACK_REMOVED=YES

ACCEPTED is not treated as finality. The harness explicitly waits for FINALIZED.
