#!/usr/bin/env bash

set -euo pipefail

REPO="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

cd "$REPO"

PYTHON="$REPO/.venv/bin/python"
PYTEST="$REPO/.venv/bin/pytest"

COMPOSE="$REPO/tests/supported_runtime/docker-compose.v0.121.24.yml"

PROJECT="${POLICYFUSE_SUPPORTED_RUNTIME_PROJECT:-policyfuse-supported-v012124-$$}"
RPC_PORT="${POLICYFUSE_SUPPORTED_RUNTIME_RPC_PORT:-4200}"
RPC_URL="http://127.0.0.1:${RPC_PORT}/api"

RUN_ID="$(
  date -u +%Y%m%dT%H%M%SZ
)"

EVIDENCE_DIR="$REPO/.artifacts/supported-runtime/$RUN_ID"

mkdir -p "$EVIDENCE_DIR"

export POLICYFUSE_SUPPORTED_RUNTIME_RPC_PORT="$RPC_PORT"

STACK_STARTED=0
CLEANED=0

compose() {
  docker compose \
    -p "$PROJECT" \
    -f "$COMPOSE" \
    "$@"
}

capture_logs() {
  if [ "$STACK_STARTED" = "1" ]; then
    compose logs \
      --no-color \
      >"$EVIDENCE_DIR/runtime.log" \
      2>&1 || true
  fi
}

cleanup() {
  if [ "$CLEANED" = "1" ]; then
    return
  fi

  CLEANED=1

  if [ ! -f "$EVIDENCE_DIR/runtime.log" ]; then
    capture_logs
  fi

  if [ "$STACK_STARTED" = "1" ]; then
    compose down \
      -v \
      --remove-orphans \
      >/dev/null \
      2>&1 || true
  fi
}

on_exit() {
  RC=$?

  trap - EXIT INT TERM

  cleanup

  exit "$RC"
}

trap on_exit EXIT INT TERM

echo "============================================================"
echo "POLICYFUSE SUPPORTED-RUNTIME VERIFICATION"
echo "LOCALNET=v0.121.24"
echo "GENVM=v0.2.16"
echo "PLATFORM=linux/arm64"
echo "PROJECT=$PROJECT"
echo "RPC=$RPC_URL"
echo "EVIDENCE=$EVIDENCE_DIR"
echo "============================================================"
echo

test -x "$PYTHON" || {
  echo "STOP: .venv Python missing"
  exit 1
}

test -x "$PYTEST" || {
  echo "STOP: .venv pytest missing"
  exit 1
}

test -f "$COMPOSE" || {
  echo "STOP: supported-runtime compose missing"
  exit 1
}

test "$(
  shasum -a 256 \
    contracts/policy_fuse.py |
  awk '{print $1}'
)" = \
"00f94d240e2090d1e25c6594322057b6246175eae75cafee030de702b427f7e9" || {
  echo "STOP: PolicyFuse contract SHA changed"
  exit 1
}

echo "===== TOOLCHAIN GATE ====="

"$PYTHON" - <<'PY'
import importlib.metadata

expected = {
    "genlayer-test":
        "0.29.2",
    "genlayer-py":
        "0.16.3",
    "genvm-linter":
        "0.11.0",
    "pytest":
        "9.1.1",
    "web3":
        "8.0.0",
    "eth-account":
        "0.14.0",
}

for package, expected_version in expected.items():
    actual = importlib.metadata.version(
        package
    )

    print(
        package
        + "="
        + actual
    )

    if actual != expected_version:
        raise SystemExit(
            "STOP: "
            + package
            + " expected "
            + expected_version
            + ", got "
            + actual
        )

print(
    "PINNED_PYTHON_TOOLCHAIN=PASS"
)
PY

echo

echo "===== PORT GATE ====="

if lsof \
  -nP \
  -iTCP:"$RPC_PORT" \
  -sTCP:LISTEN \
  >/dev/null \
  2>&1
then
  echo "STOP: RPC port $RPC_PORT already in use"
  exit 1
fi

echo "RPC_PORT_AVAILABLE=YES"
echo

echo "===== FRESH PROJECT GATE ====="

test -z "$(
  docker ps -aq \
    --filter "label=com.docker.compose.project=$PROJECT"
)" || {
  echo "STOP: compose project already exists"
  exit 1
}

echo "FRESH_PROJECT=PASS"
echo

echo "===== PULL EXACT PINNED IMAGES ====="

compose pull

echo "PINNED_IMAGE_PULL=PASS"
echo

echo "===== START FRESH DISTRIBUTED RUNTIME ====="

STACK_STARTED=1

compose up -d

POSTGRES_ID="$(
  compose ps -q postgres
)"

REDIS_ID="$(
  compose ps -q redis
)"

WEBDRIVER_ID="$(
  compose ps -q webdriver
)"

MIGRATION_ID="$(
  compose ps -a -q database-migration
)"

JSONRPC_ID="$(
  compose ps -q jsonrpc
)"

WORKER_ID="$(
  compose ps -q consensus-worker
)"

for VALUE in \
  "$POSTGRES_ID" \
  "$REDIS_ID" \
  "$WEBDRIVER_ID" \
  "$MIGRATION_ID" \
  "$JSONRPC_ID" \
  "$WORKER_ID"
do
  test -n "$VALUE" || {
    echo "STOP: required service container missing"
    exit 1
  }
done

echo "FRESH_RUNTIME_CONTAINERS_CREATED=PASS"
echo

echo "===== MIGRATION GATE ====="

MIGRATION_STATUS="$(
  docker inspect "$MIGRATION_ID" \
    --format '{{.State.Status}}'
)"

MIGRATION_EXIT="$(
  docker inspect "$MIGRATION_ID" \
    --format '{{.State.ExitCode}}'
)"

echo "MIGRATION_STATUS=$MIGRATION_STATUS"
echo "MIGRATION_EXIT_CODE=$MIGRATION_EXIT"

test "$MIGRATION_STATUS" = "exited" || {
  echo "STOP: migration did not exit"
  exit 1
}

test "$MIGRATION_EXIT" = "0" || {
  echo "STOP: migration failed"
  exit 1
}

echo "MIGRATION_COMPLETED=PASS"
echo

echo "===== HEALTH GATE ====="

for ENTRY in \
  "postgres:$POSTGRES_ID" \
  "redis:$REDIS_ID" \
  "webdriver:$WEBDRIVER_ID" \
  "jsonrpc:$JSONRPC_ID" \
  "consensus-worker:$WORKER_ID"
do
  SERVICE="${ENTRY%%:*}"
  CID="${ENTRY#*:}"

  READY=0

  for ATTEMPT in $(seq 1 480)
  do
    HEALTH="$(
      docker inspect "$CID" \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'
    )"

    if [ "$HEALTH" = "healthy" ]; then
      READY=1
      break
    fi

    sleep 1
  done

  echo "$SERVICE=$HEALTH"

  test "$READY" = "1" || {
    echo "STOP: $SERVICE did not become healthy"
    exit 1
  }
done

echo "FULL_RUNTIME_HEALTH=PASS"
echo

echo "===== EXACT IMAGE IDENTITY ====="

check_image() {
  CID="$1"
  EXPECTED="$2"
  LABEL="$3"

  ACTUAL="$(
    docker inspect "$CID" \
      --format '{{.Image}}'
  )"

  echo "${LABEL}_IMAGE_ID=$ACTUAL"

  test "$ACTUAL" = "$EXPECTED" || {
    echo "STOP: $LABEL image identity mismatch"
    exit 1
  }
}

check_image \
  "$POSTGRES_ID" \
  "sha256:3c5c8892d184f738f4fe282d14ddaa613a38f00f4189d2d94725ebe6f2909ddb" \
  "POSTGRES"

check_image \
  "$REDIS_ID" \
  "sha256:bd999b5cfee25fb24b8320a31fddbd69f462df44c8138c66e369582937beebc0" \
  "REDIS"

check_image \
  "$WEBDRIVER_ID" \
  "sha256:57ad706cdf79c18070cdcbf5838c29fa83f85d487294ab659579616d33f0ee23" \
  "WEBDRIVER"

check_image \
  "$MIGRATION_ID" \
  "sha256:e6fb4d7cfff92150a7e02bbf63f5cda2bc5a36f4294d730420662c796b1f6949" \
  "MIGRATION"

check_image \
  "$JSONRPC_ID" \
  "sha256:a8019b1ec9b6273677a85478d74b5e70f2de96b6af0526d71da98a3926d14273" \
  "JSONRPC"

check_image \
  "$WORKER_ID" \
  "sha256:c4cacac3d0853249a62e2c067dfc9a973f1476f3f3c8b5c31225b4ea5d90b209" \
  "WORKER"

echo "EXACT_IMAGE_IDENTITY=PASS"
echo

echo "===== GENVM + POLICYFUSE RUNNER ====="

JSONRPC_GENVM="$(
  docker exec "$JSONRPC_ID" \
    /genvm/executor/v0.2.16/bin/genvm \
    --version
)"

WORKER_GENVM="$(
  docker exec "$WORKER_ID" \
    /genvm/executor/v0.2.16/bin/genvm \
    --version
)"

echo "JSONRPC_GENVM=$JSONRPC_GENVM"
echo "WORKER_GENVM=$WORKER_GENVM"

case "$JSONRPC_GENVM" in
  "genvm v0.2.16-"*)
    ;;
  *)
    echo "STOP: JSONRPC GenVM version wrong"
    exit 1
    ;;
esac

case "$WORKER_GENVM" in
  "genvm v0.2.16-"*)
    ;;
  *)
    echo "STOP: worker GenVM version wrong"
    exit 1
    ;;
esac

RUNNER_ARCHIVE="/genvm/runners/py-genlayer/1j/b45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6.tar"

JSONRPC_RUNNER_SHA="$(
  docker exec "$JSONRPC_ID" \
    sha256sum "$RUNNER_ARCHIVE" |
  awk '{print $1}'
)"

WORKER_RUNNER_SHA="$(
  docker exec "$WORKER_ID" \
    sha256sum "$RUNNER_ARCHIVE" |
  awk '{print $1}'
)"

echo "JSONRPC_RUNNER_SHA256=$JSONRPC_RUNNER_SHA"
echo "WORKER_RUNNER_SHA256=$WORKER_RUNNER_SHA"

test "$JSONRPC_RUNNER_SHA" = \
"0626f0af44103acd2b96e73a0e47c2a56a04313e6bd89e5852025a8f942a64c9" || {
  echo "STOP: JSONRPC runner SHA mismatch"
  exit 1
}

test "$WORKER_RUNNER_SHA" = "$JSONRPC_RUNNER_SHA" || {
  echo "STOP: worker runner SHA mismatch"
  exit 1
}

echo "GENVM_AND_RUNNER_GATE=PASS"
echo

echo "===== FRESH CHAIN BASELINE ====="

TX_COUNT="$(
  docker exec \
    -e PGPASSWORD=postgres \
    "$POSTGRES_ID" \
    psql \
      -U postgres \
      -d genlayer_state \
      -Atc \
      'SELECT count(*) FROM transactions;' |
  tr -d '[:space:]'
)"

echo "INITIAL_TRANSACTION_COUNT=$TX_COUNT"

test "$TX_COUNT" = "0" || {
  echo "STOP: initial transaction count not zero"
  exit 1
}

POLICYFUSE_SUPPORTED_RUNTIME_RPC="$RPC_URL" \
"$PYTHON" - <<'PY'
import json
import os
import urllib.request

url = os.environ[
    "POLICYFUSE_SUPPORTED_RUNTIME_RPC"
]

def rpc(method):
    request = urllib.request.Request(
        url,
        data=json.dumps({
            "jsonrpc": "2.0",
            "id": method,
            "method": method,
            "params": [],
        }).encode(),
        headers={
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        body = json.loads(
            response.read()
        )

    if "error" in body:
        raise SystemExit(
            repr(body["error"])
        )

    return body["result"]

assert rpc(
    "eth_chainId"
) == "0xf22f"

assert rpc(
    "sim_getFinalityWindowTime"
) == 1

assert rpc(
    "sim_countValidators"
) == 0

assert rpc(
    "sim_getAllValidators"
) == []

print(
    "FRESH_CHAIN_BASELINE=PASS"
)
PY

echo

echo "===== RUN PYTEST SUPPORTED-RUNTIME REGRESSION ====="

export POLICYFUSE_SUPPORTED_RUNTIME=1
export POLICYFUSE_SUPPORTED_RUNTIME_RPC="$RPC_URL"
export POLICYFUSE_SUPPORTED_RUNTIME_POSTGRES_ID="$POSTGRES_ID"
export POLICYFUSE_SUPPORTED_RUNTIME_WORKER_ID="$WORKER_ID"
export POLICYFUSE_SUPPORTED_RUNTIME_EVIDENCE_DIR="$EVIDENCE_DIR"

PYTHONDONTWRITEBYTECODE=1 \
"$PYTEST" \
  -q \
  -s \
  -p no:cacheprovider \
  tests/supported_runtime/test_policyfuse_finality.py

echo "SUPPORTED_RUNTIME_PYTEST=PASS"
echo

echo "===== EVIDENCE GATE ====="

for NAME in \
  allow-evaluation-raw.json \
  allow-validator-registry-raw.json \
  deny-evaluation-raw.json \
  deny-validator-registry-raw.json \
  repair_required-evaluation-raw.json \
  repair_required-validator-registry-raw.json \
  status-history.jsonl \
  result.json
do
  FILE="$EVIDENCE_DIR/$NAME"

  test -s "$FILE" || {
    echo "STOP: evidence missing: $NAME"
    exit 1
  }

  echo "$NAME|BYTES=$(
    wc -c <"$FILE" |
    tr -d '[:space:]'
  )|SHA256=$(
    shasum -a 256 "$FILE" |
    awk '{print $1}'
  )"
done

echo "SUPPORTED_RUNTIME_EVIDENCE=PASS"
echo

echo "===== FINAL FRESH-RUN STATE ====="

FINAL_TX_COUNT="$(
  docker exec \
    -e PGPASSWORD=postgres \
    "$POSTGRES_ID" \
    psql \
      -U postgres \
      -d genlayer_state \
      -Atc \
      'SELECT count(*) FROM transactions;' |
  tr -d '[:space:]'
)"

echo "FINAL_TRANSACTION_COUNT=$FINAL_TX_COUNT"

test "$FINAL_TX_COUNT" = "8" || {
  echo "STOP: final transaction count not eight"
  exit 1
}

FINAL_VALIDATOR_COUNT="$(
  POLICYFUSE_SUPPORTED_RUNTIME_RPC="$RPC_URL" \
  "$PYTHON" - <<'PY'
import json
import os
import urllib.request

request = urllib.request.Request(
    os.environ[
        "POLICYFUSE_SUPPORTED_RUNTIME_RPC"
    ],
    data=json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sim_countValidators",
        "params": [],
    }).encode(),
    headers={
        "Content-Type": "application/json",
    },
)

with urllib.request.urlopen(
    request,
    timeout=30,
) as response:
    body = json.loads(
        response.read()
    )

if "error" in body:
    raise SystemExit(
        repr(body["error"])
    )

print(
    body["result"]
)
PY
)"

echo "FINAL_VALIDATOR_COUNT=$FINAL_VALIDATOR_COUNT"

test "$FINAL_VALIDATOR_COUNT" = "5" || {
  echo "STOP: final validator count not five"
  exit 1
}

capture_logs

cp "$COMPOSE" \
  "$EVIDENCE_DIR/docker-compose.v0.121.24.yml"

(
  cd "$EVIDENCE_DIR"

  find . \
    -maxdepth 1 \
    -type f \
    ! -name SHA256SUMS \
    -print0 |
  sort -z |
  while IFS= read -r -d '' FILE
  do
    printf '%s  %s\n' \
      "$(
        shasum -a 256 "$FILE" |
        awk '{print $1}'
      )" \
      "${FILE#./}"
  done
) >"$EVIDENCE_DIR/SHA256SUMS"

echo "EVIDENCE_MANIFEST=$EVIDENCE_DIR/SHA256SUMS"
echo

cleanup
trap - EXIT INT TERM

echo "ISOLATED_STACK_REMOVED=YES"
echo
echo "============================================================"
echo "POLICYFUSE_SUPPORTED_RUNTIME_VERIFY=PASS"
echo "TARGET_LOCALNET_VERSION=V0_121_24"
echo "TARGET_GENVM_VERSION=V0_2_16"
echo "TARGET_PLATFORM=LINUX_ARM64"
echo "FRESH_ISOLATED_RUNTIME=YES"
echo "EXACTLY_FIVE_MOCK_VALIDATORS=PASS"
echo "ALLOW_FINALIZED=YES"
echo "DENY_FINALIZED=YES"
echo "REPAIR_REQUIRED_FINALIZED=YES"
echo "ALLOW_AUTHORIZATION_CURRENTNESS_RUNTIME_VERIFIED=YES"
echo "RAW_EVALUATION_RESPONSES_PRESERVED_BEFORE_DECODE=YES"
echo "FINAL_TRANSACTION_COUNT=8"
echo "FINAL_VALIDATOR_COUNT=5"
echo "ISOLATED_STACK_REMOVED=YES"
echo "EVIDENCE_DIR=$EVIDENCE_DIR"
echo "============================================================"
