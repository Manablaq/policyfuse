# PolicyFuse v1 Toolchain

Status: pinned local development and verification baseline.

## Contract runtime

- GenVM dependency: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
- This is the exact runtime identifier used by the current official GenLayer contract documentation and by the finalized EvidenceGate reference implementation.

## Host tools

- Python: `3.12.14`
- GenLayer CLI: `0.39.2`
- Node.js: `24.20.0`

## Python verification packages

- `genlayer-test[sim]==0.29.2`
- `genlayer-py==0.16.3`
- `genvm-linter==0.11.0`
- `pytest==9.1.1`
- `eth-utils==6.0.0`
- `numpy==2.3.3`

## Selection rationale

`genlayer-test==0.29.2` is the current stable testing-suite release observed during Stage 1C discovery and is the same version already proven by EvidenceGate's five-validator supported-runtime verification.

`genlayer-py==0.16.3` is intentionally pinned instead of automatically adopting a newer client release. This exact version is already proven compatible with `genlayer-test==0.29.2` in the finalized EvidenceGate verification environment. PolicyFuse will not upgrade it unless a later compatibility gate demonstrates a concrete need.

`genvm-linter==0.11.0` is pinned for static GenVM validation. Its commands and behavior must be probed before contract implementation is accepted.

The lock file is generated from a fresh Python 3.12 virtual environment after `pip check` passes. No dependency upgrade is implicit after this point.

## Verification order

1. install the exact pinned environment;
2. require `pip check` success;
3. verify exact package versions;
4. inspect `genvm-lint`, `glsim`, and pytest command availability;
5. validate a disposable GenVM probe against the pinned runtime;
6. only then implement `contracts/policy_fuse.py`.

The pre-deployment toolchain gate has been satisfied for the frozen v1 source. The verified live deployment target is GenLayer Studio Dev (chain ID 61997); see `docs/live-verification/STUDIO_DEV_FINAL.md` for the live verification record.
