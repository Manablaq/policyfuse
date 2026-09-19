# PolicyFuse Studio Dev live verification

<!-- POLICYFUSE_STUDIO_DEV_FINAL_REPORT_V1 -->

PolicyFuse completed its live-network verification on **GenLayer Studio Dev (chain ID 61997)** against the frozen repository state recorded below.

## Deployment identity

- Contract: `0xF5066aE61456b1ADEC4871Da1650F64F1aE5C43F`
- Verification signer: `0x1f87Ae197af539253978d435aD45cCf28Fb95024`
- Policy ID: `6026bcf6318b8922145e2e30c3b6a25e78bd4dba9a9ec66ef98f92988860284b`
- Policy fingerprint: `bc5c6ce35f5142e7cf47bd13676c1a49b182d2d802e36a3342eb48e728b2b238`
- Frozen Git HEAD: `d643bfa69c302cc0df2960ab765d8484255ad16e`
- Contract SHA-256: `00f94d240e2090d1e25c6594322057b6246175eae75cafee030de702b427f7e9`
- Direct-test SHA-256: `b8a78fd4af1954f0c43a39342a8575ddd31caf90416581f47057384791b88529`

## Finalized transaction sequence

| Stage | Transaction | Materialized state |
| --- | --- | --- |
| Deployment | `0x438da38961232ced1837e5084d64e06977108f80714226cc396f9a1816ca2905` | `FINALIZED` |
| Write 1 — create policy | `0xf67e5341274bf71b21f1e594613017962a3ae66a0f28e633b6d2d41a41b77bbc` | `FINALIZED` |
| Write 2 — create ALLOW intent | `0x720cc2ceaf6a20ed12fef3a81c5c612faa8c33c0d4ff91538bb34baaa45e5bf5` | `FINALIZED` |
| Write 3 — evaluate ALLOW | `0x322d826e12c8258b5b20f3a2b4cf54895b4b2c4989aefeedf874f6598ad5d14c` | `FINALIZED` |
| Write 4 — create DENY intent | `0x88ab47032d0a97a6cdf3602a516515b1924e2830b2d74f7ea564df3c5541792b` | `FINALIZED` |
| Write 5 — evaluate DENY | `0x39e95d8004757182a6509c8c5a274dd87ece898b7e990a602e917a0bd485b6eb` | `FINALIZED` |
| Write 6 — create REPAIR_REQUIRED intent | `0x750be94f48a2325db14d7627193dc2a66b93ab2dd9596a3176482a3c5c2af83a` | `FINALIZED` |
| Write 7 — evaluate REPAIR_REQUIRED | `0xe7edb99045acb0560e36059ccf546a125b0e37eb8e4127a716cc9172e1eeb70c` | `FINALIZED` |

The final signer nonce is `182`. The R7-R1 authorization covered exactly seven contract-write submissions at nonces `175` through `181`; all seven are consumed and **zero contract writes remain authorized by that packet**.

No explicit finalization transaction was used. Finality was observed read-only from the transaction lifecycle.

## Consequence-path results

### ALLOW

- Intent ID: `5b7f374e9e56061d867ec3212ae9451868e43f6143b921f4aba9830f9bb83223`
- Decision: `ALLOW`
- Rule vector: `[{"id":"R1","state":"PASS"}]`
- Rule-vector digest: `84ec91f2ba9209d74704bd4912db6d9ac6789e8b2092dbf2b0830a2789c9455e`
- Authorization ID: `5e20046e5b5d7d73d0bfc4339ab4db7b992bb53333c8a851004767638e5b8d85`
- `is_authorization_current`: `true` at final certification time
- `is_authorization_current_for`: `true` for the exact consumer and action-core digest at final certification time

### DENY

- Intent ID: `f5138fdbe2b8916dcefa1621893d35311db3b54e7e64f06fff262fccd849107d`
- Decision: `DENY`
- Failure code: `RULE_FAILED`
- Rule vector: `[{"id":"R1","state":"FAIL"}]`
- Rule-vector digest: `6cd574565c497d0fd8b1e7d56f93d72b0b1037db71337497364a9f120a5a51ab`
- Authorization ID: empty

### REPAIR_REQUIRED

- Intent ID: `c3d2a8ffbc52ac0aacf1b633fe1bf4998b5ff2cc101440ff7cf0e258af3a1aa8`
- Decision: `REPAIR_REQUIRED`
- Failure code: `RULE_UNKNOWN`
- Rule vector: `[{"id":"R1","state":"UNKNOWN"}]`
- Rule-vector digest: `9bb61b6336547f2553b082841db767a9078e456c8e272c4a6a42eba468e04fd4`
- Authorization ID: empty

## Reproducibility notes

Verification used GenLayer CLI `0.40.0-rc.3` with package JSON SHA-256 `55129dd0816b8433f825a0913f40ea8a39c22a0495dab2bf748b32b30aba17e2`.

For reproducible simulations, the verifier used a **temporary CLI copy** with simulation-only GenVM datetime injection. The create-intent checks also used a temporary literal-string transport escape so JSON action-core strings and the empty clarification string reached the ABI exactly as intended. These changes were confined to temporary verification runtimes: the deployed contract, repository source, global CLI, and real write path were not patched.

The final certification was read-only. Its successful R2 runner copied the existing **encrypted** worker keystore into the temporary CLI home only so the CLI could resolve the configured `worker` account for view calls. It did not request a password, decrypt the keystore, sign, or submit a transaction.

## Integrity anchors

- Final live certification record SHA-256: `fe7f74c65507c35c1dfb377b850703136f959e00fc179754290fe2de2d1996d1`
- R7-R1 authorization packet SHA-256: `2771a0799ae792f1ded8a86c53a7742279cc5e3605ce5655c048e884e1f866ff`
- External Position-7 reviewer bundle manifest SHA-256: `d67a3ece751f0db9d0263711400dbce154df54640b2e582b4e8db599eb6c49be`
- External live report SHA-256: `9314f199c6f30a19f1ff62700cc11fde58b235acc706b7407e236c8dc64f8870`

Repository copies of the final certification record and R7-R1 authorization packet are stored beside this report. `INTEGRITY.sha256` binds the repository-integrated evidence bytes.
