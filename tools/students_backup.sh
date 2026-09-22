#!/usr/bin/env bash
# students_backup.sh — зеркало приватного students/ на NAS. Раз в час из launchd
# (com.juniorit.students-backup). Шара не смонтирована — тихий пропуск, не ошибка.
set -uo pipefail

SRC="${JUNIOR_IT_STUDENTS:-$(cd "$(dirname "$0")/.." && pwd)/students}"
SHARE="${STUDENTS_BACKUP_SHARE:-/Volumes/BACKUP-VIDEO}"
DEST="${STUDENTS_BACKUP_DEST:-$SHARE/JuniorIT/students}"
stamp=$(date '+%Y-%m-%d %H:%M:%S')

if [[ ! -d "$SHARE" ]]; then
  echo "$stamp: шара $SHARE не смонтирована, пропуск"
  exit 0
fi
if [[ ! -d "$SRC" ]]; then
  echo "$stamp: нет источника $SRC, пропуск"
  exit 0
fi

mkdir -p "$DEST" || { echo "$stamp: не создать $DEST"; exit 1; }
if rsync -a --delete "$SRC/" "$DEST/"; then
  count=$(find "$SRC" -type f | wc -l | tr -d ' ')
  echo "$stamp: ok $count файлов → $DEST"
else
  echo "$stamp: rsync завершился с ошибкой"
  exit 1
fi
