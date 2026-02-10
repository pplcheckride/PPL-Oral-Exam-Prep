#!/usr/bin/env bash
set -euo pipefail

PROJECT_REF="${PROJECT_REF:-dserfffyhcferhlpggkw}"
PUBLISHABLE_KEY="${PUBLISHABLE_KEY:-${ANON_KEY:-}}"
LICENSE_KEY="${LICENSE_KEY:-PPL-TEST-001}"

if ! command -v supabase >/dev/null 2>&1; then
  echo "ERROR: supabase CLI not found in PATH"
  exit 1
fi

if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "NOTE: SUPABASE_ACCESS_TOKEN is not set; relying on existing 'supabase login' credentials."
fi

if [[ -z "${PUBLISHABLE_KEY}" ]]; then
  echo "ERROR: Set PUBLISHABLE_KEY (or ANON_KEY) to your project's publishable key (sb_publishable_...)"
  exit 1
fi

echo "Deploying edge functions to project-ref: ${PROJECT_REF}"
supabase functions deploy license_exchange --project-ref "${PROJECT_REF}" --no-verify-jwt
supabase functions deploy progress_sync --project-ref "${PROJECT_REF}" --no-verify-jwt
supabase functions deploy mock_results --project-ref "${PROJECT_REF}" --no-verify-jwt

BASE="https://${PROJECT_REF}.supabase.co/functions/v1"

echo
echo "Smoke test: license_exchange"
LICENSE_JSON="$(
  curl -sS "${BASE}/license_exchange" \
    -H "apikey: ${PUBLISHABLE_KEY}" \
    -H "content-type: application/json" \
    --data "{\"licenseKey\":\"${LICENSE_KEY}\"}"
)"
echo "${LICENSE_JSON}"

TOKEN="$(
  printf '%s' "${LICENSE_JSON}" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))'
)"

if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: license_exchange did not return token"
  exit 1
fi

echo
echo "Smoke test: progress_sync GET"
curl -sS -i "${BASE}/progress_sync" \
  -H "apikey: ${PUBLISHABLE_KEY}" \
  -H "Authorization: Bearer ${TOKEN}"
