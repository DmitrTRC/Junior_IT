"""Один тик brain: pull -> apply -> schedule -> github -> push. Запускается launchd раз в минуту."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/

from comms import apply, course, github_poll, schedule, transport  # noqa: E402
from comms.config import Config, ConfigError, load_config  # noqa: E402
from comms.identity import Identity  # noqa: E402
from comms.outbox import Outbox, esc  # noqa: E402
from comms.queue import read_items, remove_item  # noqa: E402
from comms.state import State  # noqa: E402
from journal.model import JournalError  # noqa: E402

DEFAULT_CONFIG = Path.home() / ".junior_it" / "comms.toml"
DEAD_AFTER = 3


def default_runner(cmd, *, timeout, stdin_text=None):
    return subprocess.run(cmd, input=stdin_text, capture_output=True, text=True, timeout=timeout)


def _names(cfg: Config) -> dict[str, str]:
    try:
        return course.student_names(cfg.students_root)
    except (JournalError, FileNotFoundError):
        return {}


def _write_last_tick(cfg: Config, now: datetime, counts: dict, pending: int, inbox_left: int) -> None:
    path = cfg.local_dir / "last_tick.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"ts": now.astimezone().isoformat(timespec="seconds"), "counts": counts,
                               "pending": pending, "inbox_left": inbox_left}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


_LOCKED_COUNTS = {"pulled": 0, "applied": 0, "errors": 0, "scheduled": [], "github": 0, "pushed": 0, "locked": True}


def _missing_files(item) -> list[str]:
    return [name for name in item.data.get("files") or [] if not (item.files_dir / name).is_file()]


def _count_failure(cfg: Config, state: State, ctx, inbox: Path, item_id: str, exc: Exception, log) -> None:
    """Ядовитый элемент не должен ходить по кругу: после трёх падений — в dead/ и сообщение Димасу."""
    failures = state.data.setdefault("failures", {})
    failures[item_id] = int(failures.get(item_id, 0)) + 1
    if failures[item_id] < DEAD_AFTER:
        return
    failures.pop(item_id)
    dead = cfg.local_dir / "dead"
    dead.mkdir(parents=True, exist_ok=True)
    if (inbox / f"{item_id}.json").is_file():
        os.replace(inbox / f"{item_id}.json", dead / f"{item_id}.json")
    if (inbox / item_id).is_dir():
        shutil.rmtree(dead / item_id, ignore_errors=True)
        os.replace(inbox / item_id, dead / item_id)
    ctx.outbox.teacher(f"элемент {esc(item_id)} отложен после {DEAD_AFTER} ошибок: {esc(str(exc))}")
    log(f"элемент {item_id} отложен в dead/")


def run_tick(cfg: Config, now: datetime, runner, log=print) -> dict:
    cfg.local_dir.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(cfg.local_dir / "tick.lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock_fd)
        log("тик пропущен: предыдущий ещё идёт")
        return dict(_LOCKED_COUNTS)
    try:
        for sub in ("inbox", "outbox-staging", "pending"):
            (cfg.local_dir / sub).mkdir(parents=True, exist_ok=True)
        counts = {"pulled": 0, "applied": 0, "errors": 0, "scheduled": [], "github": 0, "pushed": 0}
        try:
            counts["pulled"] = transport.pull(cfg, runner)
        except transport.TransportError as exc:
            log(f"pull: {exc}")
        inbox = cfg.local_dir / "inbox"
        state = State(cfg.state_path)
        try:
            ctx = apply.Context(cfg=cfg, state=state, identity=Identity(cfg.students_root / "comms.yml"),
                                outbox=Outbox(cfg.local_dir / "outbox-staging"), runner=runner, now=now,
                                names=_names(cfg))
            for item in read_items(inbox):
                if state.processed(item.id):
                    remove_item(inbox, item.id)
                    continue
                if _missing_files(item):
                    log(f"элемент {item.id}: вложения ещё не доехали")
                    continue
                try:
                    apply.apply_item(item, ctx)
                except Exception as exc:
                    counts["errors"] += 1
                    log(f"элемент {item.id}: {exc}")
                    _count_failure(cfg, state, ctx, inbox, item.id, exc, log)
                    continue
                state.mark_processed(item.id, now)
                state.data["failures"].pop(item.id, None)
                remove_item(inbox, item.id)
                counts["applied"] += 1
            roster_exists = (cfg.students_root / "roster.yml").is_file()
            tails_fn = ((lambda: schedule.collect_tails(cfg.students_root, cfg.repo_root, now.date()))
                       if roster_exists else (lambda: []))
            try:
                counts["scheduled"] = schedule.run(cfg, state, ctx.outbox, now, tails_fn)
            except (JournalError, OSError) as exc:
                log(f"расписание: {exc}")
            state.tick += 1
            if state.tick % cfg.github_poll_every == 0:
                try:
                    submissions = github_poll.poll(cfg, ctx.identity, state, runner, now)
                    apply.handle_github(ctx, submissions)
                    counts["github"] = len(submissions)
                except Exception as exc:
                    log(f"github: {exc}")
                    counts["errors"] += 1
            try:
                counts["pushed"] = transport.push(cfg, runner)
            except Exception as exc:
                log(f"push: {exc}")
        finally:
            state.prune(now)
            state.save()
            _write_last_tick(cfg, now, counts, len(state.pending), len(read_items(inbox)))
        return counts
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="comms.tick", description="Тик brain: очереди, журнал, черновики")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--once", action="store_true", help="один тик (по умолчанию)")
    ap.add_argument("--dry-run", action="store_true", help="показать состояние, ничего не делая")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"comms: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        state = State(cfg.state_path)
        last = cfg.local_dir / "last_tick.json"
        print(f"входящих локально: {len(read_items(cfg.local_dir / 'inbox'))}, "
              f"исходящих в staging: {len(read_items(cfg.local_dir / 'outbox-staging'))}, "
              f"ожидают кнопок: {len(state.pending)}, тик № {state.tick}")
        print(f"последний тик: {json.loads(last.read_text(encoding='utf-8'))['ts'] if last.is_file() else 'не было'}")
        return 0
    counts = run_tick(cfg, datetime.now(), default_runner, log=lambda m: print(m, file=sys.stderr))
    if counts["applied"] or counts["errors"] or counts["scheduled"] or counts["github"] or counts["pushed"]:
        print(f"тик: {counts}", file=sys.stderr)
    return 1 if counts["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
