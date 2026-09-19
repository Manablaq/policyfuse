# PolicyFuse documentation

This directory contains the normative v1 specification, implementation mapping, security model, reproducibility material, and final live-verification evidence for PolicyFuse.

## Start here

For a reviewer evaluating the project:

1. [`../README.md`](../README.md) — project overview and verification summary
2. [`SPEC_V1.md`](SPEC_V1.md) — normative contract behavior
3. [`PUBLIC_API_V1.md`](PUBLIC_API_V1.md) — public methods and lifecycle rules
4. [`THREAT_MODEL_V1.md`](THREAT_MODEL_V1.md) — security goals and threat analysis
5. [`SUPPORTED_RUNTIME_VERIFICATION_V1.md`](SUPPORTED_RUNTIME_VERIFICATION_V1.md) — reproducible five-validator finality regression
6. [`live-verification/STUDIO_DEV_FINAL.md`](live-verification/STUDIO_DEV_FINAL.md) — final Studio Dev deployment and live-network evidence

## Specification and semantics

| Document | Purpose |
| --- | --- |
| [`SPEC_V1.md`](SPEC_V1.md) | Normative v1 behavior and actor model |
| [`CONSENSUS_V1.md`](CONSENSUS_V1.md) | Leader/validator semantics and exact consensus binding |
| [`STATE_MACHINE_V1.md`](STATE_MACHINE_V1.md) | Policy, intent, decision, and authorization lifecycle |
| [`DATA_MODEL_V1.md`](DATA_MODEL_V1.md) | Persistent collections and record structures |
| [`PUBLIC_API_V1.md`](PUBLIC_API_V1.md) | Write/read methods and lifecycle constraints |
| [`BOUNDS_AND_IDENTIFIERS_V1.md`](BOUNDS_AND_IDENTIFIERS_V1.md) | Input bounds, canonical identifiers, and hash-domain rules |
| [`THREAT_MODEL_V1.md`](THREAT_MODEL_V1.md) | Security goals, threats, and downstream-consumer responsibilities |
| [`IMPLEMENTATION_MAPPING_V1.md`](IMPLEMENTATION_MAPPING_V1.md) | Mapping from frozen specification to concrete implementation |

## Toolchain and reproducibility

| Document | Purpose |
| --- | --- |
| [`TOOLCHAIN_V1.md`](TOOLCHAIN_V1.md) | Frozen local development and Direct Mode baseline |
| [`GENVM_ARTIFACT_PIN_V1.md`](GENVM_ARTIFACT_PIN_V1.md) | Frozen static semantic-validation / GenVM artifact baseline |
| [`SUPPORTED_RUNTIME_VERIFICATION_V1.md`](SUPPORTED_RUNTIME_VERIFICATION_V1.md) | Five-validator Docker supported-runtime profile and evidence contract |

PolicyFuse records these profiles separately because local/static validation, supported-runtime execution, and Studio Dev live verification are distinct verification layers.

## Live verification

The live-verification directory contains the final Studio Dev reviewer evidence:

- [`live-verification/STUDIO_DEV_FINAL.md`](live-verification/STUDIO_DEV_FINAL.md) — human-readable final verification report
- [`live-verification/final-certification.txt`](live-verification/final-certification.txt) — machine-readable final certification record
- [`live-verification/r7-r1-authorization-packet.json`](live-verification/r7-r1-authorization-packet.json) — exact seven-write authorization scope
- [`live-verification/INTEGRITY.sha256`](live-verification/INTEGRITY.sha256) — SHA-256 manifest for the repository-integrated evidence

The verified Studio Dev contract is:

```text
0xF5066aE61456b1ADEC4871Da1650F64F1aE5C43F
```

Network:

```text
GenLayer Studio Dev
chain ID 61997
```

The live verification finalized the deployment plus seven authorized write transactions and verified the `ALLOW`, `DENY`, and `REPAIR_REQUIRED` consequence paths.

## Source of truth

The release-frozen implementation is:

```text
contracts/policy_fuse.py
```

The final documentation should be interpreted together with the frozen source, test suites, and integrity-bound verification evidence rather than as a substitute for them.
