#!/usr/bin/env bash
# Собирает публикуемую часть репозитория.
# teacher/ и внутренняя кухня на сайт не попадают.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/_site}"

rm -rf "$OUT"
mkdir -p "$OUT"

rsync -a \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude '.claude/' \
  --exclude '_site/' \
  --exclude 'teacher/' \
  --exclude 'live-code.md' \
  --exclude 'tools/' \
  --exclude 'meta/' \
  --exclude 'refs/' \
  --exclude 'homework/' \
  --exclude 'playground/' \
  --exclude 'provisioning/' \
  --exclude 'print/' \
  --exclude 'students/' \
  --exclude 'recordings/' \
  --exclude 'TO_PARENTS/' \
  --exclude 'graphify-out/' \
  --exclude 'docs/superpowers/' \
  --exclude '.superpowers/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  "$ROOT/" "$OUT/"

echo "сайт собран: $OUT"
