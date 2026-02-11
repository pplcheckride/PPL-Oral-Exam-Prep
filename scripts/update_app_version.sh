#!/usr/bin/env bash
set -euo pipefail

INDEX_FILE="${1:-index.html}"

if [[ ! -f "${INDEX_FILE}" ]]; then
  echo "ERROR: File not found: ${INDEX_FILE}" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Must run inside a git repository." >&2
  exit 1
fi

if ! grep -q "const APP_VERSION = '" "${INDEX_FILE}"; then
  echo "ERROR: APP_VERSION constant not found in ${INDEX_FILE}" >&2
  exit 1
fi

git_hash="$(git rev-parse --short HEAD)"
utc_date="$(date -u +%Y.%m.%d)"
new_version="v${utc_date}+${git_hash}"

tmp_file="$(mktemp)"
sed -E "s|const APP_VERSION = '[^']*';|const APP_VERSION = '${new_version}';|" "${INDEX_FILE}" > "${tmp_file}"
mv "${tmp_file}" "${INDEX_FILE}"

echo "Updated ${INDEX_FILE}: APP_VERSION=${new_version}"
