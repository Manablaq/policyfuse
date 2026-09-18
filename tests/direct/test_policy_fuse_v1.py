import json

from eth_utils import keccak
from gltest.direct import create_address


NOW_ISO = "2026-09-18T10:00:00Z"
NOW = 1_789_725_600
HOUR = 3600
DAY = 24 * HOUR

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
ACTION = '{"amount_usd":50,"vendor":"Acme"}'


def _enc(value):
    return f"{len(value.encode())}:{value}"


def _hash(domain, *fields):
    payload = _enc(domain) + "".join(_enc(field) for field in fields)
    return keccak(text=payload).hex()


def _deploy(vm, deploy):
    vm.check_pickling = True
    vm.strict_mocks = True
    contract = deploy("contracts/policy_fuse.py")
    owner = create_address("default_sender")
    vm.sender = owner
    vm.warp(NOW_ISO)
    return contract, owner


def _create_policy(
    vm,
    contract,
    owner,
    *,
    slug="spend-policy",
    version=1,
    name="Autonomous Spend Policy",
    criteria=CRITERIA,
    rule_ids=RULE_IDS,
    rule_texts=RULE_TEXTS,
    action_types="PURCHASE",
    max_intent=DAY,
    max_auth=HOUR,
):
    vm.sender = owner
    return contract.create_policy(
        slug,
        version,
        name,
        criteria,
        rule_ids,
        rule_texts,
        action_types,
        max_intent,
        max_auth,
    )


def _create_intent(
    vm,
    contract,
    owner,
    policy_id,
    consumer,
    *,
    action_type="PURCHASE",
    action_core=ACTION,
    clarification="Acme appears on the approved vendor list.",
    deadline=NOW + (4 * HOUR),
):
    vm.sender = owner
    return contract.create_intent(
        policy_id,
        consumer,
        action_type,
        action_core,
        clarification,
        deadline,
    )


def _mock_vector(vm, states, rule_ids=("R1", "R2"), **extra):
    payload = {
        "kind": "RULE_VECTOR_V1",
        "rules": [
            {"id": rule_id, "state": state}
            for rule_id, state in zip(rule_ids, states)
        ],
    }
    payload.update(extra)
    vm.mock_llm(
        r"(?s).*PolicyFuse semantic authorization evaluator.*",
        json.dumps(payload),
    )


def _setup(vm, deploy):
    contract, owner = _deploy(vm, deploy)
    consumer = create_address("policyfuse-consumer")
    policy_id = _create_policy(vm, contract, owner)
    intent_id = _create_intent(
        vm,
        contract,
        owner,
        policy_id,
        consumer,
    )
    return contract, owner, consumer, policy_id, intent_id


def _no_decision(vm, contract, intent_id):
    with vm.expect_revert("DECISION_NOT_FOUND"):
        contract.get_decision(intent_id)


def _allow_case(vm, deploy):
    contract, owner, consumer, policy_id, intent_id = _setup(vm, deploy)
    _mock_vector(vm, ("PASS", "PASS"))
    assert contract.evaluate_intent(intent_id) == "ALLOW"
    assert vm.run_validator() is True
    decision = contract.get_decision(intent_id)
    authorization = contract.get_authorization(decision.authorization_id)
    intent = contract.get_intent(intent_id)
    assert decision.decision == "ALLOW"
    assert decision.failure_code == ""
    assert authorization.intent_id == intent_id
    assert authorization.policy_id == policy_id
    assert authorization.consumer == consumer
    assert authorization.action_core_digest == intent.action_core_digest
    assert authorization.full_intent_digest == intent.full_intent_digest
    assert contract.is_authorization_current(decision.authorization_id) is True
    return (
        contract,
        owner,
        consumer,
        policy_id,
        intent_id,
        decision,
        authorization,
    )


def test_policy_identity_canonicalization_and_latest_pointer(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    policy_id = _create_policy(
        direct_vm,
        contract,
        owner,
        rule_texts='[ "The purchase amount must not exceed the approved budget.", "The vendor must be approved by the policy owner." ]',
    )
    policy = contract.get_policy(policy_id)
    expected_id = _hash(
        "policyfuse-policy-v1",
        owner.as_hex,
        "spend-policy",
        "1",
    )
    assert policy_id == expected_id
    assert policy.owner == owner
    assert policy.status == "ACTIVE"
    assert policy.replacement_policy_id == ""
    assert policy.rule_texts_json == json.dumps(
        [
            "The purchase amount must not exceed the approved budget.",
            "The vendor must be approved by the policy owner.",
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert policy.allowed_action_types_csv == "PURCHASE"
    assert len(policy.fingerprint) == 64
    assert contract.get_latest_policy(owner, "spend-policy") == policy_id


def test_policy_versions_are_monotonic_but_new_version_does_not_supersede(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    first = _create_policy(direct_vm, contract, owner, version=1)
    second = _create_policy(direct_vm, contract, owner, version=2)
    assert contract.get_latest_policy(owner, "spend-policy") == second
    assert contract.get_policy(first).status == "ACTIVE"
    assert contract.get_policy(second).status == "ACTIVE"
    with direct_vm.expect_revert("POLICY_VERSION_NOT_INCREASING"):
        _create_policy(direct_vm, contract, owner, version=2)


def test_policy_rejects_duplicate_rules_unsorted_actions_and_duplicate_actions(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    with direct_vm.expect_revert("DUPLICATE_RULE_ID"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="duplicate-rules",
            rule_ids="R1,R1",
        )
    with direct_vm.expect_revert("ACTION_TYPES_NOT_SORTED"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="unsorted-actions",
            action_types="TRANSFER,PURCHASE",
        )
    with direct_vm.expect_revert("DUPLICATE_ACTION_TYPE"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="duplicate-actions",
            action_types="PURCHASE,PURCHASE",
        )


def test_policy_rejects_rule_shape_and_text_bounds(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    with direct_vm.expect_revert("RULE_TEXT_COUNT_MISMATCH"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="count-mismatch",
            rule_texts=json.dumps(["one"]),
        )
    with direct_vm.expect_revert("RULE_TEXT_TOO_LONG"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="long-rule",
            rule_texts=json.dumps(["X" * 1025, "valid"]),
        )
    ids = ",".join(f"R{i}" for i in range(13))
    texts = json.dumps(["x"] * 13)
    with direct_vm.expect_revert("RULE_ID_TOO_MANY"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="too-many-rules",
            rule_ids=ids,
            rule_texts=texts,
        )


def test_policy_rejects_text_identifier_and_lifetime_bounds(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    with direct_vm.expect_revert("POLICY_SLUG_INVALID_CHARACTER"):
        _create_policy(direct_vm, contract, owner, slug="bad slug")
    with direct_vm.expect_revert("POLICY_NAME_TOO_LONG"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="long-name",
            name="N" * 97,
        )
    with direct_vm.expect_revert("POLICY_CRITERIA_CONTAINS_NUL"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="nul-criteria",
            criteria="bad\x00criteria",
        )
    with direct_vm.expect_revert("INVALID_MAX_INTENT_LIFETIME"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="short-intent-life",
            max_intent=59,
        )
    with direct_vm.expect_revert("INVALID_MAX_AUTHORIZATION_LIFETIME"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="long-auth-life",
            max_auth=604801,
        )


def test_supersede_is_owner_only_and_requires_same_lineage_active_greater_version(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    first = _create_policy(direct_vm, contract, owner, version=1)
    second = _create_policy(direct_vm, contract, owner, version=2)

    attacker = create_address("attacker")
    direct_vm.sender = attacker
    with direct_vm.expect_revert("ONLY_POLICY_OWNER"):
        contract.supersede_policy(first, second)

    direct_vm.sender = owner
    other_slug = _create_policy(
        direct_vm,
        contract,
        owner,
        slug="other-policy",
        version=2,
    )
    with direct_vm.expect_revert("REPLACEMENT_SLUG_MISMATCH"):
        contract.supersede_policy(first, other_slug)

    direct_vm.sender = attacker
    foreign = _create_policy(
        direct_vm,
        contract,
        attacker,
        slug="spend-policy",
        version=2,
    )
    direct_vm.sender = owner
    with direct_vm.expect_revert("REPLACEMENT_OWNER_MISMATCH"):
        contract.supersede_policy(first, foreign)

    contract.supersede_policy(first, second)
    old = contract.get_policy(first)
    assert old.status == "SUPERSEDED"
    assert old.replacement_policy_id == second
    with direct_vm.expect_revert("POLICY_NOT_ACTIVE"):
        contract.supersede_policy(first, second)


def test_revoke_is_owner_only_and_terminal(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    policy_id = _create_policy(direct_vm, contract, owner)
    direct_vm.sender = create_address("attacker")
    with direct_vm.expect_revert("ONLY_POLICY_OWNER"):
        contract.revoke_policy(policy_id)
    direct_vm.sender = owner
    contract.revoke_policy(policy_id)
    assert contract.get_policy(policy_id).status == "REVOKED"
    with direct_vm.expect_revert("POLICY_NOT_ACTIVE"):
        contract.revoke_policy(policy_id)


def test_intent_exact_binding_and_counter_uniqueness(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    consumer = create_address("consumer")
    policy_id = _create_policy(direct_vm, contract, owner)
    first = _create_intent(
        direct_vm,
        contract,
        owner,
        policy_id,
        consumer,
    )
    second = _create_intent(
        direct_vm,
        contract,
        owner,
        policy_id,
        consumer,
    )
    a = contract.get_intent(first)
    b = contract.get_intent(second)
    expected_action_digest = _hash(
        "policyfuse-action-core-v1",
        consumer.as_hex,
        "PURCHASE",
        ACTION,
    )
    assert a.action_core_digest == expected_action_digest
    assert a.action_core_digest == b.action_core_digest
    assert a.clarification_digest == b.clarification_digest
    assert a.intent_id != b.intent_id
    assert int(a.counter) == 1
    assert int(b.counter) == 2
    assert a.full_intent_digest != b.full_intent_digest
    assert a.status == "OPEN"


def test_intent_rejects_zero_consumer_action_and_deadline_violations(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    policy_id = _create_policy(direct_vm, contract, owner)
    from genlayer.py.types import Address

    zero = Address("0x" + "0" * 40)
    with direct_vm.expect_revert("CONSUMER_ZERO_ADDRESS"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            zero,
        )

    consumer = create_address("consumer")
    with direct_vm.expect_revert("ACTION_TYPE_NOT_ALLOWED"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
            action_type="TRANSFER",
        )
    with direct_vm.expect_revert("ACTION_CORE_TOO_LONG"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
            action_core="X" * 4097,
        )
    with direct_vm.expect_revert("CLARIFICATION_TOO_LONG"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
            clarification="Y" * 4097,
        )
    with direct_vm.expect_revert("DEADLINE_NOT_FUTURE"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
            deadline=NOW,
        )
    with direct_vm.expect_revert("INTENT_LIFETIME_TOO_LONG"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
            deadline=NOW + DAY + 1,
        )


def test_intent_requires_active_policy(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    consumer = create_address("consumer")
    policy_id = _create_policy(direct_vm, contract, owner)
    contract.revoke_policy(policy_id)
    with direct_vm.expect_revert("POLICY_NOT_ACTIVE"):
        _create_intent(
            direct_vm,
            contract,
            owner,
            policy_id,
            consumer,
        )


def test_allow_creates_exact_authorization_and_currentness(direct_vm, direct_deploy):
    (
        contract,
        _owner,
        consumer,
        _policy_id,
        intent_id,
        decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    intent = contract.get_intent(intent_id)
    assert intent.status == "ALLOW"
    assert int(authorization.created_at) == NOW
    assert int(authorization.valid_until) == NOW + HOUR
    assert len(authorization.authorization_id) == 64
    verdict = contract.get_verdict(intent_id)
    assert verdict == [
        "ALLOW",
        "ALLOW",
        "",
        authorization.authorization_id,
        str(NOW + HOUR),
    ]
    assert contract.is_authorization_current_for(
        authorization.authorization_id,
        consumer,
        intent.action_core_digest,
    ) is True


def test_deny_is_terminal_and_creates_no_authorization(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "FAIL"))
    assert contract.evaluate_intent(intent_id) == "DENY"
    assert direct_vm.run_validator() is True
    intent = contract.get_intent(intent_id)
    decision = contract.get_decision(intent_id)
    assert intent.status == "DENY"
    assert decision.failure_code == "RULE_FAILED"
    assert decision.authorization_id == ""
    assert contract.get_verdict(intent_id) == [
        "DENY",
        "DENY",
        "RULE_FAILED",
        "",
        "0",
    ]
    with direct_vm.expect_revert("INTENT_NOT_OPEN"):
        contract.evaluate_intent(intent_id)


def test_unknown_requires_repair_and_creates_no_authorization(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "UNKNOWN"))
    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"
    assert direct_vm.run_validator() is True
    decision = contract.get_decision(intent_id)
    assert contract.get_intent(intent_id).status == "REPAIR_REQUIRED"
    assert decision.failure_code == "RULE_UNKNOWN"
    assert decision.authorization_id == ""
    assert contract.get_verdict(intent_id) == [
        "REPAIR_REQUIRED",
        "REPAIR_REQUIRED",
        "RULE_UNKNOWN",
        "",
        "0",
    ]


def test_fail_has_precedence_over_unknown(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("UNKNOWN", "FAIL"))
    assert contract.evaluate_intent(intent_id) == "DENY"
    assert contract.get_decision(intent_id).failure_code == "RULE_FAILED"


def test_validator_substantive_agreement_and_disagreement(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "PASS"))
    assert contract.evaluate_intent(intent_id) == "ALLOW"
    assert direct_vm.run_validator() is True

    direct_vm.clear_mocks()
    _mock_vector(direct_vm, ("PASS", "FAIL"))
    assert direct_vm.run_validator() is False


def test_validator_rejects_nonreturn_leader_result(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "PASS"))
    assert contract.evaluate_intent(intent_id) == "ALLOW"
    assert direct_vm.run_validator(
        leader_error=RuntimeError("synthetic leader failure")
    ) is False


def test_malformed_top_level_schema_cannot_mutate_intent(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "PASS"), forbidden="extra")
    with direct_vm.expect_revert("LLM_RESULT_SCHEMA_MISMATCH"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"
    _no_decision(direct_vm, contract, intent_id)


def test_wrong_kind_cannot_mutate_intent(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    payload = {
        "kind": "OTHER_KIND",
        "rules": [
            {"id": "R1", "state": "PASS"},
            {"id": "R2", "state": "PASS"},
        ],
    }
    direct_vm.mock_llm(
        r"(?s).*PolicyFuse semantic authorization evaluator.*",
        json.dumps(payload),
    )
    with direct_vm.expect_revert("LLM_RESULT_KIND_INVALID"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"
    _no_decision(direct_vm, contract, intent_id)


def test_missing_reordered_and_invalid_rule_vectors_are_rejected(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS",), rule_ids=("R1",))
    with direct_vm.expect_revert("LLM_RULE_COUNT_MISMATCH"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"

    direct_vm.clear_mocks()
    _mock_vector(direct_vm, ("PASS", "PASS"), rule_ids=("R2", "R1"))
    with direct_vm.expect_revert("LLM_RULE_ID_ORDER_MISMATCH"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"

    direct_vm.clear_mocks()
    _mock_vector(direct_vm, ("PASS", "MAYBE"))
    with direct_vm.expect_revert("LLM_RULE_STATE_INVALID"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"
    _no_decision(direct_vm, contract, intent_id)


def test_evaluation_after_deadline_writes_nothing(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    consumer = create_address("consumer")
    policy_id = _create_policy(direct_vm, contract, owner)
    intent_id = _create_intent(
        direct_vm,
        contract,
        owner,
        policy_id,
        consumer,
        deadline=NOW + HOUR,
    )
    direct_vm.warp("2026-09-18T11:00:00Z")
    with direct_vm.expect_revert("INTENT_DEADLINE_REACHED"):
        contract.evaluate_intent(intent_id)
    assert contract.get_intent(intent_id).status == "OPEN"
    _no_decision(direct_vm, contract, intent_id)


def test_repair_preserves_action_core_and_creates_new_lineage_revision(direct_vm, direct_deploy):
    contract, owner, consumer, policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "UNKNOWN"))
    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"

    old = contract.get_intent(intent_id)
    direct_vm.clear_mocks()
    direct_vm.sender = owner
    new_id = contract.repair_intent(
        intent_id,
        "Acme is explicitly listed in the signed approved-vendor schedule.",
        NOW + (3 * HOUR),
    )
    new = contract.get_intent(new_id)
    old_after = contract.get_intent(intent_id)

    assert old_after.status == "SUPERSEDED"
    assert new.status == "OPEN"
    assert new.predecessor_intent_id == intent_id
    assert new.requester == old.requester == owner
    assert new.consumer == old.consumer == consumer
    assert new.policy_id == old.policy_id == policy_id
    assert new.policy_fingerprint == old.policy_fingerprint
    assert new.action_type == old.action_type
    assert new.action_core == old.action_core
    assert new.action_core_digest == old.action_core_digest
    assert new.clarification != old.clarification
    assert new.clarification_digest != old.clarification_digest
    assert new.intent_id != old.intent_id
    assert int(new.counter) == int(old.counter) + 1


def test_repair_is_requester_only_and_requires_repair_state_before_deadline(direct_vm, direct_deploy):
    contract, owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    with direct_vm.expect_revert("INTENT_NOT_REPAIRABLE"):
        contract.repair_intent(
            intent_id,
            "new context",
            NOW + (3 * HOUR),
        )

    _mock_vector(direct_vm, ("UNKNOWN", "PASS"))
    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"
    direct_vm.clear_mocks()

    direct_vm.sender = create_address("attacker")
    with direct_vm.expect_revert("ONLY_REQUESTER"):
        contract.repair_intent(
            intent_id,
            "new context",
            NOW + (3 * HOUR),
        )

    direct_vm.sender = owner
    direct_vm.warp("2026-09-18T14:00:00Z")
    with direct_vm.expect_revert("INTENT_DEADLINE_REACHED"):
        contract.repair_intent(
            intent_id,
            "late context",
            NOW + (5 * HOUR),
        )


def test_repair_is_blocked_if_policy_is_no_longer_active(direct_vm, direct_deploy):
    contract, owner, _consumer, policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("PASS", "UNKNOWN"))
    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"
    direct_vm.clear_mocks()
    direct_vm.sender = owner
    contract.revoke_policy(policy_id)
    with direct_vm.expect_revert("POLICY_NOT_ACTIVE"):
        contract.repair_intent(
            intent_id,
            "new context",
            NOW + (3 * HOUR),
        )


def test_expire_open_intent_only_after_deadline(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    consumer = create_address("consumer")
    policy_id = _create_policy(direct_vm, contract, owner)
    intent_id = _create_intent(
        direct_vm,
        contract,
        owner,
        policy_id,
        consumer,
        deadline=NOW + HOUR,
    )

    with direct_vm.expect_revert("INTENT_DEADLINE_NOT_REACHED"):
        contract.expire_intent(intent_id)

    direct_vm.warp("2026-09-18T11:00:00Z")
    contract.expire_intent(intent_id)
    assert contract.get_intent(intent_id).status == "EXPIRED"
    assert contract.get_verdict(intent_id) == [
        "EXPIRED",
        "",
        "INTENT_DEADLINE_REACHED",
        "",
        "0",
    ]
    with direct_vm.expect_revert("INTENT_NOT_EXPIRABLE"):
        contract.expire_intent(intent_id)


def test_expire_repair_required_intent_after_deadline(direct_vm, direct_deploy):
    contract, _owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm, direct_deploy
    )
    _mock_vector(direct_vm, ("UNKNOWN", "PASS"))
    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"
    direct_vm.warp("2026-09-18T14:00:00Z")
    contract.expire_intent(intent_id)
    assert contract.get_intent(intent_id).status == "EXPIRED"
    assert contract.get_verdict(intent_id)[0] == "EXPIRED"


def test_authorization_expires_by_time(direct_vm, direct_deploy):
    (
        contract,
        _owner,
        _consumer,
        _policy_id,
        _intent_id,
        _decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    direct_vm.warp("2026-09-18T11:00:00Z")
    assert contract.is_authorization_current(authorization.authorization_id) is False


def test_current_for_rejects_wrong_consumer_and_wrong_action_digest(direct_vm, direct_deploy):
    (
        contract,
        _owner,
        consumer,
        _policy_id,
        intent_id,
        _decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    intent = contract.get_intent(intent_id)
    wrong_consumer = create_address("wrong-consumer")
    assert contract.is_authorization_current_for(
        authorization.authorization_id,
        wrong_consumer,
        intent.action_core_digest,
    ) is False
    assert contract.is_authorization_current_for(
        authorization.authorization_id,
        consumer,
        "0" * 64,
    ) is False


def test_new_policy_version_alone_does_not_invalidate_authorization(direct_vm, direct_deploy):
    (
        contract,
        owner,
        _consumer,
        policy_id,
        _intent_id,
        _decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    second = _create_policy(
        direct_vm,
        contract,
        owner,
        version=2,
        criteria="Version two criteria.",
    )
    assert second != policy_id
    assert contract.get_policy(policy_id).status == "ACTIVE"
    assert contract.is_authorization_current(authorization.authorization_id) is True


def test_supersession_immediately_invalidates_historical_authorization(direct_vm, direct_deploy):
    (
        contract,
        owner,
        _consumer,
        policy_id,
        _intent_id,
        _decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    replacement = _create_policy(
        direct_vm,
        contract,
        owner,
        version=2,
        criteria="Version two criteria.",
    )
    contract.supersede_policy(policy_id, replacement)
    assert contract.is_authorization_current(authorization.authorization_id) is False
    assert contract.get_authorization(authorization.authorization_id).intent_id != ""


def test_revocation_immediately_invalidates_historical_authorization(direct_vm, direct_deploy):
    (
        contract,
        owner,
        _consumer,
        policy_id,
        _intent_id,
        _decision,
        authorization,
    ) = _allow_case(direct_vm, direct_deploy)
    direct_vm.sender = owner
    contract.revoke_policy(policy_id)
    assert contract.is_authorization_current(authorization.authorization_id) is False


def test_missing_authorization_currentness_is_false_and_lookup_reverts(direct_vm, direct_deploy):
    contract, _owner = _deploy(direct_vm, direct_deploy)
    missing = "0" * 64
    assert contract.is_authorization_current(missing) is False
    with direct_vm.expect_revert("AUTHORIZATION_NOT_FOUND"):
        contract.get_authorization(missing)


def test_allow_authorization_is_bounded_by_intent_deadline(direct_vm, direct_deploy):
    contract, owner = _deploy(direct_vm, direct_deploy)
    consumer = create_address("consumer")
    policy_id = _create_policy(
        direct_vm,
        contract,
        owner,
        max_auth=4 * HOUR,
    )
    intent_id = _create_intent(
        direct_vm,
        contract,
        owner,
        policy_id,
        consumer,
        deadline=NOW + HOUR,
    )
    _mock_vector(direct_vm, ("PASS", "PASS"))
    assert contract.evaluate_intent(intent_id) == "ALLOW"
    decision = contract.get_decision(intent_id)
    authorization = contract.get_authorization(decision.authorization_id)
    assert int(authorization.valid_until) == NOW + HOUR


def test_no_consumption_or_execution_surface_exists(direct_vm, direct_deploy):
    contract, _owner = _deploy(direct_vm, direct_deploy)
    for name in (
        "consume_authorization",
        "execute_authorization",
        "transfer",
        "withdraw",
        "deposit",
        "pay",
        "escrow",
    ):
        assert not hasattr(contract, name)

def test_repair_rejects_unchanged_clarification_without_mutation(
    direct_vm,
    direct_deploy,
):
    contract, owner, _consumer, _policy_id, intent_id = _setup(
        direct_vm,
        direct_deploy,
    )

    _mock_vector(direct_vm, ("UNKNOWN", "PASS"))

    assert contract.evaluate_intent(intent_id) == "REPAIR_REQUIRED"
    assert direct_vm.run_validator() is True

    direct_vm.clear_mocks()

    old = contract.get_intent(intent_id)

    direct_vm.sender = owner

    with direct_vm.expect_revert("CLARIFICATION_UNCHANGED"):
        contract.repair_intent(
            intent_id,
            old.clarification,
            NOW + (3 * HOUR),
        )

    after_failed_repair = contract.get_intent(intent_id)

    assert after_failed_repair.status == "REPAIR_REQUIRED"
    assert after_failed_repair.clarification == old.clarification
    assert (
        after_failed_repair.clarification_digest
        == old.clarification_digest
    )

    new_id = contract.repair_intent(
        intent_id,
        "Fresh vendor-approval evidence is now available.",
        NOW + (3 * HOUR),
    )

    new = contract.get_intent(new_id)
    old_after_success = contract.get_intent(intent_id)

    assert old_after_success.status == "SUPERSEDED"
    assert new.status == "OPEN"
    assert new.predecessor_intent_id == intent_id
    assert new.clarification != old.clarification
    assert new.clarification_digest != old.clarification_digest
    assert int(new.counter) == int(old.counter) + 1


def test_multibyte_utf8_policy_name_boundary_is_byte_counted(
    direct_vm,
    direct_deploy,
):
    contract, owner = _deploy(
        direct_vm,
        direct_deploy,
    )

    at_limit = "é" * 48
    over_limit = "é" * 49

    assert len(at_limit.encode()) == 96
    assert len(over_limit.encode()) == 98

    policy_id = _create_policy(
        direct_vm,
        contract,
        owner,
        slug="utf8-name-max",
        name=at_limit,
    )

    assert contract.get_policy(policy_id).name == at_limit

    with direct_vm.expect_revert("POLICY_NAME_TOO_LONG"):
        _create_policy(
            direct_vm,
            contract,
            owner,
            slug="utf8-name-over",
            name=over_limit,
        )


def test_missing_policy_intent_verdict_and_lineage_getters_revert(
    direct_vm,
    direct_deploy,
):
    contract, owner = _deploy(
        direct_vm,
        direct_deploy,
    )

    missing = "f" * 64

    with direct_vm.expect_revert("POLICY_NOT_FOUND"):
        contract.get_policy(missing)

    with direct_vm.expect_revert("INTENT_NOT_FOUND"):
        contract.get_intent(missing)

    with direct_vm.expect_revert("INTENT_NOT_FOUND"):
        contract.get_verdict(missing)

    with direct_vm.expect_revert("POLICY_LINEAGE_NOT_FOUND"):
        contract.get_latest_policy(
            owner,
            "missing-lineage",
        )
