#!/usr/bin/env bash
set -euo pipefail

# Creates a clean tarball you can copy/paste/transfer into another repo/machine.
# The bundle intentionally excludes secrets, local caches, and SQLite DB files.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/export_bundle"
STAMP="$(date +"%Y%m%d_%H%M%S")"
ARCHIVE="${OUT_DIR}/viirs_nightlights_bundle_${STAMP}.tar.gz"

mkdir -p "${OUT_DIR}"

echo "Preparing export bundle..."
echo "  repo: ${ROOT_DIR}"
echo "  out : ${ARCHIVE}"

tar -czf "${ARCHIVE}" \
  --exclude=".git" \
  --exclude=".cursor" \
  --exclude="**/__pycache__" \
  --exclude="**/.pytest_cache" \
  --exclude="**/*.log" \
  --exclude="**/.DS_Store" \
  --exclude="**/*.db" \
  --exclude="**/*.sqlite" \
  --exclude="**/*.sqlite3" \
  -C "${ROOT_DIR}" \
  backend \
  frontend \
  docs \
  scripts \
  nginx.conf \
  README.md \
  QUICKSTART.md \
  METHODOLOGY.md \
  LICENSE \
  DEPLOY_SERVER.md \
  .env.example \
  systemd \
  nginx

echo "Done."
echo "${ARCHIVE}"

