#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:${NGINX_PORT:-8080}}"
LOAD_TEST_SCRIPT="loadtests/task_workflow.js"
LOAD_TEST_USER_ID="${LOAD_TEST_USER_ID:-00000000-0000-0000-0000-000000000101}"
LOAD_TEST_ASSIGNEE_ID="${LOAD_TEST_ASSIGNEE_ID:-00000000-0000-0000-0000-000000000102}"
LOAD_TEST_PROJECT_ID="${LOAD_TEST_PROJECT_ID:-00000000-0000-0000-0000-000000000301}"
LOAD_TEST_PAGE_SIZE="${LOAD_TEST_PAGE_SIZE:-20}"
LOAD_TEST_VUS="${LOAD_TEST_VUS:-10}"
LOAD_TEST_DURATION="${LOAD_TEST_DURATION:-30s}"
LOAD_TEST_SUMMARY_EXPORT="${LOAD_TEST_SUMMARY_EXPORT:-}"

if ! curl --fail --silent --show-error "${BASE_URL}/ready" >/dev/null; then
  echo "The API is not reachable at ${BASE_URL}. Start the stack with 'docker compose up -d --build' first."
  exit 1
fi

echo "Seeding deterministic load-test data against ${BASE_URL}"
docker compose run --rm --no-deps api python scripts/seed_load_test_data.py >/dev/null

run_local_k6() {
  local -a summary_args=()

  if [[ -n "${LOAD_TEST_SUMMARY_EXPORT}" ]]; then
    mkdir -p "$(dirname "${LOAD_TEST_SUMMARY_EXPORT}")"
    summary_args=(--summary-export "${LOAD_TEST_SUMMARY_EXPORT}")
  fi

  k6 run \
    "${summary_args[@]}" \
    --env BASE_URL="${BASE_URL}" \
    --env LOAD_TEST_USER_ID="${LOAD_TEST_USER_ID}" \
    --env LOAD_TEST_ASSIGNEE_ID="${LOAD_TEST_ASSIGNEE_ID}" \
    --env LOAD_TEST_PROJECT_ID="${LOAD_TEST_PROJECT_ID}" \
    --env LOAD_TEST_PAGE_SIZE="${LOAD_TEST_PAGE_SIZE}" \
    --env LOAD_TEST_VUS="${LOAD_TEST_VUS}" \
    --env LOAD_TEST_DURATION="${LOAD_TEST_DURATION}" \
    "${LOAD_TEST_SCRIPT}"
}

run_docker_k6() {
  local -a summary_args=()

  if [[ -n "${LOAD_TEST_SUMMARY_EXPORT}" ]]; then
    mkdir -p "$(dirname "${LOAD_TEST_SUMMARY_EXPORT}")"
    summary_args=(--summary-export "/workspace/${LOAD_TEST_SUMMARY_EXPORT}")
  fi

  docker run --rm --network host -i \
    --user "$(id -u):$(id -g)" \
    -v "${PWD}:/workspace" \
    grafana/k6:0.49.0 run \
    "${summary_args[@]}" \
    --env BASE_URL="${BASE_URL}" \
    --env LOAD_TEST_USER_ID="${LOAD_TEST_USER_ID}" \
    --env LOAD_TEST_ASSIGNEE_ID="${LOAD_TEST_ASSIGNEE_ID}" \
    --env LOAD_TEST_PROJECT_ID="${LOAD_TEST_PROJECT_ID}" \
    --env LOAD_TEST_PAGE_SIZE="${LOAD_TEST_PAGE_SIZE}" \
    --env LOAD_TEST_VUS="${LOAD_TEST_VUS}" \
    --env LOAD_TEST_DURATION="${LOAD_TEST_DURATION}" \
    "/workspace/${LOAD_TEST_SCRIPT}"
}

if command -v k6 >/dev/null 2>&1; then
  run_local_k6
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  run_docker_k6
  exit 0
fi

echo "k6 is not installed and Docker is unavailable. Install k6 or use Docker to run the scenario."
exit 1
