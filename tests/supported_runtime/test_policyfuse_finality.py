import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import time
import urllib.request

import pytest

from genlayer_py import (
    create_account,
    create_client,
)

from genlayer_py.abi import calldata
from genlayer_py.chains import localnet

from genlayer_py.types import (
    TransactionHashVariant,
)

from genlayer_py.types.calldata import (
    CalldataAddress,
)


pytestmark = pytest.mark.skipif(
    os.environ.get(
        "POLICYFUSE_SUPPORTED_RUNTIME"
    )
    != "1",
    reason=(
        "requires the pinned Docker supported-runtime "
        "stack; run scripts/verify-supported-runtime.sh"
    ),
)


RPC_URL = os.environ.get(
    "POLICYFUSE_SUPPORTED_RUNTIME_RPC",
    "http://127.0.0.1:4200/api",
)

POSTGRES_ID = os.environ.get(
    "POLICYFUSE_SUPPORTED_RUNTIME_POSTGRES_ID",
    "",
)

WORKER_ID = os.environ.get(
    "POLICYFUSE_SUPPORTED_RUNTIME_WORKER_ID",
    "",
)

EVIDENCE_DIR = Path(
    os.environ.get(
        "POLICYFUSE_SUPPORTED_RUNTIME_EVIDENCE_DIR",
        ".artifacts/supported-runtime",
    )
)

REPO_ROOT = Path(
    __file__
).resolve().parents[2]

CONTRACT_PATH = (
    REPO_ROOT
    / "contracts"
    / "policy_fuse.py"
)

EXPECTED_CONTRACT_SHA256 = (
    "00f94d240e2090d1e25c6594322057b6246175eae75cafee030de702b427f7e9"
)

EXPECTED_OWNER = (
    "0x3184Afa1363B4b5BFBe6569eDa4972CE3259C4E0"
)

PROMPT_KEY = (
    "PolicyFuse semantic authorization evaluator"
)

RULE_IDS = "R1,R2"

RULE_TEXTS = json.dumps(
    [
        "The purchase amount must not exceed the approved budget.",
        "The vendor must be approved by the policy owner.",
    ]
)

CRITERIA = (
    "Evaluate the exact proposed action against every rule. "
    "Do not infer missing facts; use UNKNOWN when context is insufficient."
)

ACTION = (
    '{"amount_usd":50,"vendor":"Acme"}'
)

CLARIFICATION = (
    "Acme appears on the approved vendor list."
)

HOUR = 3600
DAY = 24 * HOUR

CASES = (
    (
        "ALLOW",
        ("PASS", "PASS"),
        "ALLOW",
        "",
    ),
    (
        "DENY",
        ("PASS", "FAIL"),
        "DENY",
        "RULE_FAILED",
    ),
    (
        "REPAIR_REQUIRED",
        ("PASS", "UNKNOWN"),
        "REPAIR_REQUIRED",
        "RULE_UNKNOWN",
    ),
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def rpc_raw(
    method: str,
    params=None,
    *,
    timeout=60,
) -> bytes:
    request = urllib.request.Request(
        RPC_URL,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": method,
                "method": method,
                "params": (
                    []
                    if params is None
                    else params
                ),
            },
            separators=(",", ":"),
        ).encode(),
        headers={
            "Content-Type":
                "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
    ) as response:
        return response.read()


def decode_rpc(raw: bytes):
    body = json.loads(
        raw
    )

    if "error" in body:
        raise AssertionError(
            "RPC error: "
            + repr(
                body["error"]
            )
        )

    return body.get(
        "result"
    )


def rpc(
    method: str,
    params=None,
    *,
    timeout=60,
):
    return decode_rpc(
        rpc_raw(
            method,
            params,
            timeout=timeout,
        )
    )


def db_scalar(sql: str) -> str:
    assert POSTGRES_ID

    value = subprocess.check_output(
        [
            "docker",
            "exec",
            "-e",
            "PGPASSWORD=postgres",
            POSTGRES_ID,
            "psql",
            "-U",
            "postgres",
            "-d",
            "genlayer_state",
            "-Atc",
            sql,
        ],
        text=True,
    )

    return value.strip()


def db_tx_count() -> int:
    return int(
        db_scalar(
            "SELECT count(*) FROM transactions;"
        )
    )


def normalize_hash(value) -> str:
    if hasattr(
        value,
        "hex",
    ):
        value = value.hex()

    value = str(
        value
    )

    if not value.startswith(
        "0x"
    ):
        value = (
            "0x"
            + value
        )

    return value


def obj_field(
    value,
    name: str,
):
    if isinstance(
        value,
        dict,
    ):
        return value[
            name
        ]

    return getattr(
        value,
        name,
    )


def decode_result_blob(
    receipt_result,
):
    value = receipt_result

    if isinstance(
        value,
        dict,
    ):
        if "raw" in value:
            value = value[
                "raw"
            ]
        elif "base64" in value:
            value = value[
                "base64"
            ]

    assert isinstance(
        value,
        str,
    )

    blob = base64.b64decode(
        value
    )

    assert blob
    assert blob[0] == 0

    return calldata.decode(
        blob[1:]
    )


def leader_receipt(
    transaction,
):
    consensus = (
        transaction.get(
            "consensus_data"
        )
        or {}
    )

    receipts = (
        consensus.get(
            "leader_receipt"
        )
        or []
    )

    if isinstance(
        receipts,
        dict,
    ):
        receipts = [
            receipts
        ]

    assert receipts

    receipt = receipts[0]

    assert (
        str(
            receipt.get(
                "execution_result",
                "",
            )
        ).upper()
        == "SUCCESS"
    )

    return receipt


def transaction_return(
    transaction,
):
    return decode_result_blob(
        leader_receipt(
            transaction
        ).get(
            "result"
        )
    )


def validate_consensus(
    label: str,
    transaction,
):
    assert (
        transaction.get(
            "status"
        )
        == "FINALIZED"
    )

    votes = (
        (
            transaction.get(
                "consensus_data"
            )
            or {}
        ).get(
            "votes"
        )
        or {}
    )

    normalized = []

    for value in votes.values():
        if isinstance(
            value,
            dict,
        ):
            value = (
                value.get(
                    "vote"
                )
                or value.get(
                    "result"
                )
                or ""
            )

        normalized.append(
            str(
                value
            ).upper()
        )

    assert len(
        normalized
    ) == 5

    agree = normalized.count(
        "AGREE"
    )

    idle = normalized.count(
        "IDLE"
    )

    disagree = normalized.count(
        "DISAGREE"
    )

    timeout = normalized.count(
        "TIMEOUT"
    )

    violation = normalized.count(
        "DETERMINISTIC_VIOLATION"
    )

    assert disagree == 0
    assert timeout == 0
    assert violation == 0

    assert agree > (
        len(
            normalized
        )
        / 2
    )

    assert (
        disagree
        + idle
    ) <= (
        len(
            normalized
        )
        / 2
    )

    leader_receipt(
        transaction
    )

    print(
        f"{label}_CONSENSUS_VOTES={normalized}"
    )

    print(
        f"{label}_AGREE_COUNT={agree}"
    )

    print(
        f"{label}_IDLE_COUNT={idle}"
    )


def wait_finalized(
    label: str,
    tx_hash: str,
    history_file: Path,
):
    seen = []

    for attempt in range(
        1,
        901,
    ):
        status = rpc(
            "gen_getTransactionStatus",
            [
                tx_hash
            ],
            timeout=30,
        )

        with history_file.open(
            "a"
        ) as handle:
            handle.write(
                json.dumps(
                    {
                        "label":
                            label,
                        "transaction_hash":
                            tx_hash,
                        "attempt":
                            attempt,
                        "status":
                            status,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

        if (
            not seen
            or seen[-1] != status
        ):
            seen.append(
                status
            )

            print(
                f"{label}_STATUS={status}"
            )

        if status == "FINALIZED":
            return seen

        assert status != "CANCELED"

        time.sleep(
            1
        )

    raise AssertionError(
        label
        + " did not reach FINALIZED"
    )


def fetch_final_transaction(
    tx_hash: str,
    *,
    preserve_before_decode: Path | None = None,
):
    raw = rpc_raw(
        "gen_getStudioTransactionByHash",
        [
            tx_hash,
            True,
        ],
        timeout=90,
    )

    if preserve_before_decode is not None:
        preserve_before_decode.write_bytes(
            raw
        )

        assert (
            preserve_before_decode.read_bytes()
            == raw
        )

    transaction = decode_rpc(
        raw
    )

    assert isinstance(
        transaction,
        dict,
    )

    return (
        raw,
        transaction,
    )


def submit_write(
    client,
    account,
    *,
    label: str,
    function_name: str,
    args,
    expected_tx_count: int,
    history_file: Path,
    preserve_before_decode: Path | None = None,
):
    assert (
        db_tx_count()
        == expected_tx_count - 1
    )

    tx_hash = normalize_hash(
        client.write_contract(
            address=os.environ[
                "POLICYFUSE_DEPLOYED_ADDRESS"
            ],
            function_name=function_name,
            account=account,
            consensus_max_rotations=3,
            leader_only=False,
            args=args,
        )
    )

    print(
        f"{label}_TX_HASH={tx_hash}"
    )

    assert (
        db_tx_count()
        == expected_tx_count
    )

    journey = wait_finalized(
        label,
        tx_hash,
        history_file,
    )

    raw, transaction = (
        fetch_final_transaction(
            tx_hash,
            preserve_before_decode=(
                preserve_before_decode
            ),
        )
    )

    assert (
        transaction.get(
            "status"
        )
        == "FINALIZED"
    )

    validate_consensus(
        label,
        transaction,
    )

    return (
        tx_hash,
        journey,
        raw,
        transaction,
    )


def read_final(
    client,
    function_name: str,
    args,
):
    return client.read_contract(
        address=os.environ[
            "POLICYFUSE_DEPLOYED_ADDRESS"
        ],
        function_name=function_name,
        args=args,
        transaction_hash_variant=(
            TransactionHashVariant.LATEST_FINAL
        ),
    )


def validator_addresses(
    validators,
):
    return {
        str(
            validator[
                "address"
            ]
        ).lower()
        for validator in validators
    }


def validator_value(
    validator,
    name,
    default=None,
):
    if name in validator:
        return validator[
            name
        ]

    provider = (
        validator.get(
            "llmprovider"
        )
        or {}
    )

    return provider.get(
        name,
        default,
    )


def update_validator(
    validator,
    plugin_config,
):
    result = rpc(
        "sim_updateValidator",
        [
            validator[
                "address"
            ],
            int(
                validator_value(
                    validator,
                    "stake",
                    8,
                )
            ),
            validator_value(
                validator,
                "provider",
                "openrouter",
            ),
            validator_value(
                validator,
                "model",
                "@preset/rally-testnet-gpt-5-1",
            ),
            validator_value(
                validator,
                "config",
                {
                    "temperature":
                        0.75,
                    "max_tokens":
                        500,
                },
            ),
            validator_value(
                validator,
                "plugin",
                "openai-compatible",
            ),
            plugin_config,
        ],
        timeout=60,
    )

    assert (
        str(
            result.get(
                "address",
                validator[
                    "address"
                ],
            )
        ).lower()
        ==
        str(
            validator[
                "address"
            ]
        ).lower()
    )


def wait_worker_refresh(
    since: str,
):
    assert WORKER_ID

    phrase = (
        "created snapshot with 5 "
        "validator nodes"
    )

    for attempt in range(
        1,
        121,
    ):
        output = subprocess.run(
            [
                "docker",
                "logs",
                "--since",
                since,
                WORKER_ID,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        ).stdout

        if phrase in output:
            print(
                "WORKER_FIVE_VALIDATOR_REFRESH_ATTEMPTS="
                + str(
                    attempt
                )
            )

            return

        time.sleep(
            1
        )

    raise AssertionError(
        "worker did not reload five-validator snapshot"
    )


def force_worker_refresh(
    validators,
):
    current = rpc(
        "sim_getAllValidators"
    )

    assert len(
        current
    ) == 5

    first = current[0]

    plugin_config = dict(
        validator_value(
            first,
            "plugin_config",
            {},
        )
        or {}
    )

    since = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    update_validator(
        first,
        plugin_config,
    )

    wait_worker_refresh(
        since
    )


def create_five_validators():
    assert (
        rpc(
            "sim_countValidators"
        )
        == 0
    )

    assert (
        rpc(
            "sim_getAllValidators"
        )
        == []
    )

    for index in range(
        1,
        6,
    ):
        result = rpc(
            "sim_createValidator",
            [
                8,
                "openrouter",
                "@preset/rally-testnet-gpt-5-1",
                {
                    "temperature":
                        0.75,
                    "max_tokens":
                        500,
                },
                "openai-compatible",
                {
                    "api_key_env_var":
                        "OPENROUTERAPIKEY",
                    "api_url":
                        "https://openrouter.ai/api",
                    "mock_response": {
                        "response": {},
                        "eq_principle_prompt_comparative":
                            {},
                        "eq_principle_prompt_non_comparative":
                            {},
                    },
                },
            ],
        )

        assert result.get(
            "address"
        )

        print(
            "CREATED_VALIDATOR_"
            + str(
                index
            )
            + "="
            + result[
                "address"
            ]
        )

    validators = rpc(
        "sim_getAllValidators"
    )

    assert len(
        validators
    ) == 5

    assert (
        rpc(
            "sim_countValidators"
        )
        == 5
    )

    addresses = validator_addresses(
        validators
    )

    assert len(
        addresses
    ) == 5

    force_worker_refresh(
        validators
    )

    return (
        validators,
        addresses,
    )


def update_case_vector(
    label: str,
    states,
    validators,
    expected_addresses,
):
    vector = {
        "kind":
            "RULE_VECTOR_V1",
        "rules": [
            {
                "id":
                    "R1",
                "state":
                    states[0],
            },
            {
                "id":
                    "R2",
                "state":
                    states[1],
            },
        ],
    }

    mock_response = {
        "response": {
            PROMPT_KEY:
                json.dumps(
                    vector,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
        },
        "eq_principle_prompt_comparative":
            {},
        "eq_principle_prompt_non_comparative":
            {},
    }

    for validator in validators:
        plugin_config = dict(
            validator_value(
                validator,
                "plugin_config",
                {},
            )
            or {}
        )

        plugin_config[
            "mock_response"
        ] = mock_response

        update_validator(
            validator,
            plugin_config,
        )

    raw_registry = rpc_raw(
        "sim_getAllValidators"
    )

    registry_path = (
        EVIDENCE_DIR
        / (
            label.lower()
            + "-validator-registry-raw.json"
        )
    )

    registry_path.write_bytes(
        raw_registry
    )

    current = decode_rpc(
        raw_registry
    )

    assert len(
        current
    ) == 5

    assert (
        validator_addresses(
            current
        )
        == expected_addresses
    )

    for validator in current:
        plugin_config = (
            validator_value(
                validator,
                "plugin_config",
                {},
            )
            or {}
        )

        persisted = (
            plugin_config
            .get(
                "mock_response",
                {},
            )
            .get(
                "response",
                {},
            )
            .get(
                PROMPT_KEY
            )
        )

        assert persisted is not None

        if isinstance(
            persisted,
            str,
        ):
            persisted = json.loads(
                persisted
            )

        assert persisted == vector

    force_worker_refresh(
        current
    )

    print(
        f"{label}_MOCK_VECTOR="
        + json.dumps(
            vector,
            sort_keys=True,
        )
    )

    return vector


def deploy_policyfuse(
    client,
    account,
    history_file: Path,
):
    assert db_tx_count() == 0

    tx_hash = normalize_hash(
        client.deploy_contract(
            code=CONTRACT_PATH.read_bytes(),
            account=account,
            args=[],
            consensus_max_rotations=3,
            leader_only=False,
        )
    )

    assert db_tx_count() == 1

    journey = wait_finalized(
        "DEPLOY",
        tx_hash,
        history_file,
    )

    _, transaction = (
        fetch_final_transaction(
            tx_hash
        )
    )

    validate_consensus(
        "DEPLOY",
        transaction,
    )

    address = db_scalar(
        "SELECT to_address "
        "FROM transactions "
        f"WHERE hash='{tx_hash}';"
    )

    assert address.startswith(
        "0x"
    )

    assert len(
        address
    ) == 42

    os.environ[
        "POLICYFUSE_DEPLOYED_ADDRESS"
    ] = address

    print(
        "DEPLOY_TX_HASH="
        + tx_hash
    )

    print(
        "DEPLOYED_CONTRACT_ADDRESS="
        + address
    )

    return (
        tx_hash,
        journey,
        address,
    )


def verify_deployed_schema(
    address: str,
):
    schema = rpc(
        "gen_getContractSchema",
        [
            address
        ],
        timeout=180,
    )

    serialized = json.dumps(
        schema,
        sort_keys=True,
    )

    required = [
        "create_policy",
        "supersede_policy",
        "revoke_policy",
        "create_intent",
        "evaluate_intent",
        "repair_intent",
        "expire_intent",
        "get_policy",
        "get_intent",
        "get_decision",
        "get_authorization",
        "get_verdict",
        "is_authorization_current",
        "is_authorization_current_for",
        "get_latest_policy",
    ]

    missing = [
        method
        for method in required
        if method not in serialized
    ]

    assert missing == []


def assert_case_state(
    client,
    *,
    label: str,
    expected_decision: str,
    expected_failure: str,
    intent_id: str,
    consumer,
):
    intent = read_final(
        client,
        "get_intent",
        [
            intent_id
        ],
    )

    decision = read_final(
        client,
        "get_decision",
        [
            intent_id
        ],
    )

    verdict = read_final(
        client,
        "get_verdict",
        [
            intent_id
        ],
    )

    assert (
        str(
            obj_field(
                intent,
                "status",
            )
        )
        == expected_decision
    )

    assert (
        str(
            obj_field(
                decision,
                "decision",
            )
        )
        == expected_decision
    )

    assert (
        str(
            obj_field(
                decision,
                "failure_code",
            )
        )
        == expected_failure
    )

    authorization_id = str(
        obj_field(
            decision,
            "authorization_id",
        )
    )

    print(
        f"{label}_VERDICT={verdict}"
    )

    if label == "ALLOW":
        assert len(
            authorization_id
        ) == 64

        authorization = read_final(
            client,
            "get_authorization",
            [
                authorization_id
            ],
        )

        assert (
            str(
                obj_field(
                    authorization,
                    "intent_id",
                )
            )
            == intent_id
        )

        assert (
            str(
                obj_field(
                    authorization,
                    "policy_id",
                )
            )
            ==
            str(
                obj_field(
                    intent,
                    "policy_id",
                )
            )
        )

        action_digest = str(
            obj_field(
                intent,
                "action_core_digest",
            )
        )

        assert (
            str(
                obj_field(
                    authorization,
                    "action_core_digest",
                )
            )
            == action_digest
        )

        assert (
            str(
                obj_field(
                    authorization,
                    "full_intent_digest",
                )
            )
            ==
            str(
                obj_field(
                    intent,
                    "full_intent_digest",
                )
            )
        )

        created_at = int(
            obj_field(
                authorization,
                "created_at",
            )
        )

        valid_until = int(
            obj_field(
                authorization,
                "valid_until",
            )
        )

        deadline = int(
            obj_field(
                intent,
                "deadline",
            )
        )

        assert (
            created_at
            < valid_until
            <= deadline
        )

        current = read_final(
            client,
            "is_authorization_current",
            [
                authorization_id
            ],
        )

        current_for = read_final(
            client,
            "is_authorization_current_for",
            [
                authorization_id,
                consumer,
                action_digest,
            ],
        )

        assert current is True
        assert current_for is True

        assert verdict == [
            "ALLOW",
            "ALLOW",
            "",
            authorization_id,
            str(
                valid_until
            ),
        ]

        return {
            "authorization_id":
                authorization_id,
            "action_core_digest":
                action_digest,
            "valid_until":
                valid_until,
        }

    assert authorization_id == ""

    assert verdict == [
        expected_decision,
        expected_decision,
        expected_failure,
        "",
        "0",
    ]

    return {
        "authorization_id":
            "",
    }


def test_policyfuse_supported_runtime_three_way_finality():
    assert POSTGRES_ID
    assert WORKER_ID

    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_file = (
        EVIDENCE_DIR
        / "status-history.jsonl"
    )

    history_file.write_text(
        ""
    )

    assert (
        sha256_bytes(
            CONTRACT_PATH.read_bytes()
        )
        == EXPECTED_CONTRACT_SHA256
    )

    assert (
        rpc(
            "eth_chainId"
        )
        == "0xf22f"
    )

    assert (
        rpc(
            "sim_getFinalityWindowTime"
        )
        == 1
    )

    assert db_tx_count() == 0

    account = create_account(
        hashlib.sha256(
            b"policyfuse-supported-runtime-owner-v1"
        ).digest()
    )

    assert (
        account.address
        == EXPECTED_OWNER
    )

    assert int(
        rpc(
            "eth_getTransactionCount",
            [
                account.address,
                "latest",
            ],
        ),
        16,
    ) == 0

    client = create_client(
        chain=localnet,
        endpoint=RPC_URL,
        account=account,
    )

    validators, addresses = (
        create_five_validators()
    )

    (
        deploy_tx,
        deploy_journey,
        contract_address,
    ) = deploy_policyfuse(
        client,
        account,
        history_file,
    )

    verify_deployed_schema(
        contract_address
    )

    owner_calldata = CalldataAddress(
        bytes.fromhex(
            account.address[2:]
        )
    )

    consumer = CalldataAddress(
        hashlib.sha256(
            b"policyfuse-consumer"
        ).digest()[:20]
    )

    (
        policy_tx,
        policy_journey,
        _,
        _,
    ) = submit_write(
        client,
        account,
        label="CREATE_POLICY",
        function_name="create_policy",
        args=[
            "spend-policy",
            1,
            "Autonomous Spend Policy",
            CRITERIA,
            RULE_IDS,
            RULE_TEXTS,
            "PURCHASE",
            DAY,
            HOUR,
        ],
        expected_tx_count=2,
        history_file=history_file,
    )

    policy_id = str(
        read_final(
            client,
            "get_latest_policy",
            [
                owner_calldata,
                "spend-policy",
            ],
        )
    )

    assert len(
        policy_id
    ) == 64

    results = {
        "deploy": {
            "transaction_hash":
                deploy_tx,
            "status_journey":
                deploy_journey,
            "contract_address":
                contract_address,
        },
        "policy": {
            "transaction_hash":
                policy_tx,
            "status_journey":
                policy_journey,
            "policy_id":
                policy_id,
        },
        "cases":
            {},
    }

    allow_state = None

    for index, (
        label,
        states,
        expected_decision,
        expected_failure,
    ) in enumerate(
        CASES,
        start=1,
    ):
        vector = update_case_vector(
            label,
            states,
            validators,
            addresses,
        )

        deadline = (
            int(
                time.time()
            )
            + (
                8
                * HOUR
            )
        )

        create_tx_count = (
            3
            + (
                (
                    index
                    - 1
                )
                * 2
            )
        )

        (
            intent_tx,
            intent_journey,
            _,
            intent_transaction,
        ) = submit_write(
            client,
            account,
            label=(
                label
                + "_CREATE_INTENT"
            ),
            function_name="create_intent",
            args=[
                policy_id,
                consumer,
                "PURCHASE",
                ACTION,
                CLARIFICATION,
                deadline,
            ],
            expected_tx_count=create_tx_count,
            history_file=history_file,
        )

        intent_id = str(
            transaction_return(
                intent_transaction
            )
        )

        assert len(
            intent_id
        ) == 64

        assert (
            str(
                obj_field(
                    read_final(
                        client,
                        "get_intent",
                        [
                            intent_id
                        ],
                    ),
                    "status",
                )
            )
            == "OPEN"
        )

        raw_file = (
            EVIDENCE_DIR
            / (
                label.lower()
                + "-evaluation-raw.json"
            )
        )

        (
            evaluation_tx,
            evaluation_journey,
            evaluation_raw,
            evaluation_transaction,
        ) = submit_write(
            client,
            account,
            label=(
                label
                + "_EVALUATE"
            ),
            function_name="evaluate_intent",
            args=[
                intent_id
            ],
            expected_tx_count=(
                create_tx_count
                + 1
            ),
            history_file=history_file,
            preserve_before_decode=(
                raw_file
            ),
        )

        assert (
            raw_file.read_bytes()
            == evaluation_raw
        )

        assert (
            str(
                transaction_return(
                    evaluation_transaction
                )
            )
            == expected_decision
        )

        state = assert_case_state(
            client,
            label=label,
            expected_decision=(
                expected_decision
            ),
            expected_failure=(
                expected_failure
            ),
            intent_id=intent_id,
            consumer=consumer,
        )

        results[
            "cases"
        ][
            label
        ] = {
            "vector":
                vector,
            "intent_transaction":
                intent_tx,
            "intent_status_journey":
                intent_journey,
            "intent_id":
                intent_id,
            "evaluation_transaction":
                evaluation_tx,
            "evaluation_status_journey":
                evaluation_journey,
            "evaluation_raw_file":
                str(
                    raw_file
                ),
            "evaluation_raw_sha256":
                sha256_bytes(
                    evaluation_raw
                ),
            "state":
                state,
        }

        if label == "ALLOW":
            allow_state = state

    assert allow_state is not None

    assert read_final(
        client,
        "is_authorization_current",
        [
            allow_state[
                "authorization_id"
            ]
        ],
    ) is True

    assert read_final(
        client,
        "is_authorization_current_for",
        [
            allow_state[
                "authorization_id"
            ],
            consumer,
            allow_state[
                "action_core_digest"
            ],
        ],
    ) is True

    assert db_tx_count() == 8

    assert int(
        rpc(
            "eth_getTransactionCount",
            [
                account.address,
                "latest",
            ],
        ),
        16,
    ) == 8

    final_validators = rpc(
        "sim_getAllValidators"
    )

    assert len(
        final_validators
    ) == 5

    assert (
        validator_addresses(
            final_validators
        )
        == addresses
    )

    results[
        "summary"
    ] = {
        "chain_id":
            61999,
        "runtime":
            "v0.121.24",
        "genvm":
            "v0.2.16",
        "platform":
            "linux/arm64",
        "validator_count":
            5,
        "transaction_count":
            8,
        "allow_finalized":
            True,
        "deny_finalized":
            True,
        "repair_required_finalized":
            True,
        "allow_authorization_current":
            True,
        "allow_authorization_current_for":
            True,
        "raw_evaluation_responses_persisted_before_decode":
            True,
    }

    (
        EVIDENCE_DIR
        / "result.json"
    ).write_text(
        json.dumps(
            results,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "POLICYFUSE_SUPPORTED_RUNTIME_TEST=PASS"
    )

    print(
        "ALLOW_FINALIZED=YES"
    )

    print(
        "DENY_FINALIZED=YES"
    )

    print(
        "REPAIR_REQUIRED_FINALIZED=YES"
    )

    print(
        "ALLOW_AUTHORIZATION_CURRENTNESS_RUNTIME_VERIFIED=YES"
    )

    print(
        "RAW_EVALUATION_RESPONSES_PRESERVED_BEFORE_DECODE=YES"
    )
