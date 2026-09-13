#!/usr/bin/env bash
# Собирает публикуемую часть репозитория.
# Белый список: публикуется только перечисленное в PUBLISH.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/_site}"

rm -rf "$OUT"
mkdir -p "$OUT"

# Белый список публикации: на сайт попадает только перечисленное.
PUBLISH=(
  index.html
  README.md
  LICENSE
  CHANGELOG.md
  CODE_OF_CONDUCT.md
  CONTRIBUTING.md
  SECURITY.md
  docs
  lessons
  textbook
  tracks
  trainer
)

SRC=()
for item in "${PUBLISH[@]}"; do
  SRC+=("$ROOT/$item")
done

rsync -a \
  --exclude 'teacher/' \
  --exclude 'live-code.md' \
  --exclude 'docs/superpowers/' \
  --exclude 'REVIEW-07-1.md' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  "${SRC[@]}" "$OUT/"

PYBIN="${PYBIN:-$ROOT/tools/.venv/bin/python}"
"$PYBIN" "$ROOT/tools/build_course_map.py" "$ROOT" "$OUT/course-map.json"

echo "сайт собран: $OUT"
