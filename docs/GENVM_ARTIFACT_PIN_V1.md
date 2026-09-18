# PolicyFuse v1 GenVM Artifact Pin

Status: frozen pre-implementation runtime artifact baseline.

## Contract runtime

PolicyFuse v1 uses the exact GenLayer runtime declared by the contract header:

`py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`

The current official GenLayer documentation still uses this exact runtime hash for Intelligent Contract examples and storage documentation.

## GenVM artifact source

Static semantic validation and schema/type tooling are bound to:

- GenVM release: `v0.3.0-rc7`
- Runner bundle: `genvm-runners-all.tar.xz`
- Local linter cache path: `~/.cache/genvm-linter/genvm-universal-v0.3.0-rc7.tar.xz`
- Exact bundle size: `134842512` bytes
- Exact bundle SHA-256: `e218a1854214681560351051f76fe2b878545cf3409455ef372d57014a88ca67`
- Exact runtime member:
  `runners/py-genlayer/1j/b45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6.tar`

The runtime member was verified to occur exactly once in the pinned bundle before semantic validation was permitted.

## Host verification stack

- Python: `3.12.14`
- GenLayer CLI: `0.39.2`
- `genlayer-test[sim]`: `0.29.2`
- `genlayer-py`: `0.16.3`
- `genvm-linter`: `0.11.0`
- `pytest`: `9.1.1`
- `pyright`: `1.1.414`

`genlayer-test==0.29.2` is intentionally paired with `genlayer-py==0.16.3`; the tagged testing-suite release accepts `genlayer-py>=0.13.0,<0.17.0`.

## Proven pre-implementation capabilities

The disposable runtime probe passed all of the following against this exact baseline:

- GenVM lint;
- SDK semantic validation;
- Pyright type checking;
- ABI schema extraction;
- Direct Mode deployment;
- persistent `TreeMap` storage;
- `@allow_storage` dataclass round-tripping;
- `Address` storage;
- `u64` storage;
- `Keccak256`;
- `gl.storage.copy_to_memory`;
- deterministic transaction-time access;
- `@gl.public.write` and `@gl.public.view`;
- `gl.vm.run_nondet_unsafe`;
- validator agreement;
- validator disagreement;
- pickling checks.

## Change control

No runtime hash, GenVM bundle, `genlayer-test`, `genlayer-py`, or linter version may be changed silently after this point.

A future upgrade requires a separate compatibility gate that re-runs semantic validation, type checking, ABI extraction, Direct Mode execution, validator agreement/disagreement tests, and supported multi-validator runtime tests before the replacement becomes canonical.

Bradbury deployment remains forbidden until implementation, Direct Mode, supported-runtime, adversarial, exact-source, and finality gates pass.
