"""Mac <-> HP: rsync по ssh. Ключ только в сторону Mac -> HP."""
from __future__ import annotations
import shutil

from comms.config import Config
from comms.queue import read_items

SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
RSYNC_TIMEOUT = 120


class TransportError(Exception):
    pass


def _ok(result, what: str) -> None:
    if result.returncode != 0:
        raise TransportError(f"{what}: код {result.returncode}: {(result.stderr or '').strip()[:200]}")


def pull(cfg: Config, runner) -> int:
    local_inbox = cfg.local_dir / "inbox"
    local_inbox.mkdir(parents=True, exist_ok=True)
    before = {i.id for i in read_items(local_inbox)}
    remote = f"{cfg.hp_host}:{cfg.hp_queue_dir}"
    _ok(runner(["rsync", "-a", "--remove-source-files", "--exclude", "*.tmp", "-e", " ".join(SSH),
                f"{remote}/inbox/", f"{local_inbox}/"], timeout=RSYNC_TIMEOUT), "rsync inbox")
    _ok(runner([*SSH, cfg.hp_host,                        # -mmin +1: каталог моложе минуты ещё наполняется
                f"find {cfg.hp_queue_dir}/inbox -mindepth 1 -type d -empty -mmin +1 -delete; "
                f"touch {cfg.hp_queue_dir}/.last_pull"],
               timeout=RSYNC_TIMEOUT), "ssh cleanup")
    runner(["rsync", "-a", "-e", " ".join(SSH), f"{remote}/status.json", str(cfg.local_dir / "status.json")],
           timeout=RSYNC_TIMEOUT)                      # статус — best effort
    return len({i.id for i in read_items(local_inbox)} - before)


def push(cfg: Config, runner) -> int:
    staging = cfg.local_dir / "outbox-staging"
    items = read_items(staging)
    if not items:
        return 0
    remote = f"{cfg.hp_host}:{cfg.hp_queue_dir}/outbox/"
    _ok(runner(["rsync", "-a", "--exclude", "*.json", "-e", " ".join(SSH), f"{staging}/", remote],
               timeout=RSYNC_TIMEOUT), "rsync вложений")
    _ok(runner(["rsync", "-a", "--remove-source-files", "--include", "*.json", "--exclude", "*", "-e", " ".join(SSH),
                f"{staging}/", remote], timeout=RSYNC_TIMEOUT), "rsync json")
    for child in staging.iterdir():                      # каталоги вложений: их содержимое уже уехало
        if child.is_dir():
            shutil.rmtree(child)
    return len(items)
