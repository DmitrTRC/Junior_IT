"""Один тик brain: pull -> apply -> schedule -> github -> push. Запускается launchd раз в минуту."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/

from comms import apply, course, github_poll, schedule, transport  # noqa: E402
from comms.config import Config, load_config  # noqa: E402
from comms.identity import Identity  # noqa: E402
from comms.outbox import Outbox  # noqa: E402
from comms.queue import read_items, remove_item  # noqa: E402
from comms.state import State  # noqa: E402
from journal.model import JournalError  # noqa: E402

DEFAULT_CONFIG = Path.home() / ".junior_it" / "comms.toml"


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
    tmp.write_text(json.dumps({"ts": now.isoformat(timespec="seconds"), "counts": counts,
                               "pending": pending, "inbox_left": inbox_left}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def run_tick(cfg: Config, now: datetime, runner, log=print) -> dict:
    for sub in ("inbox", "outbox-staging", "pending"):
        (cfg.local_dir / sub).mkdir(parents=True, exist_ok=True)
    counts = {"pulled": 0, "applied": 0, "errors": 0, "scheduled": [], "github": 0, "pushed": 0}
    try:
        counts["pulled"] = transport.pull(cfg, runner)
    except transport.TransportError as exc:
        log(f"pull: {exc}")
    state = State(cfg.state_path)
    ctx = apply.Context(cfg=cfg, state=state, identity=Identity(cfg.students_root / "comms.yml"),
                        outbox=Outbox(cfg.local_dir / "outbox-staging"), runner=runner, now=now, names=_names(cfg))
    inbox = cfg.local_dir / "inbox"
    for item in read_items(inbox):
        if state.processed(item.id):
            remove_item(inbox, item.id)
            continue
        try:
            apply.apply_item(item, ctx)
        except Exception as exc:
            counts["errors"] += 1
            log(f"элемент {item.id}: {exc}")
            continue
        state.mark_processed(item.id, now)
        remove_item(inbox, item.id)
        counts["applied"] += 1
    roster_exists = (cfg.students_root / "roster.yml").is_file()
    tails_fn = (lambda: schedule.collect_tails(cfg.students_root, cfg.repo_root, now.date())) if roster_exists else (lambda: [])
    try:
        counts["scheduled"] = schedule.run(cfg, state, ctx.outbox, now, tails_fn)
    except (JournalError, OSError) as exc:
        log(f"расписание: {exc}")
    state.tick += 1
    if state.tick % cfg.github_poll_every == 0:
        submissions = github_poll.poll(cfg, ctx.identity, state, runner, now)
        apply.handle_github(ctx, submissions)
        counts["github"] = len(submissions)
    try:
        counts["pushed"] = transport.push(cfg, runner)
    except transport.TransportError as exc:
        log(f"push: {exc}")
    state.prune(now)
    state.save()
    _write_last_tick(cfg, now, counts, len(state.pending), len(read_items(inbox)))
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="comms.tick", description="Тик brain: очереди, журнал, черновики")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--once", action="store_true", help="один тик (по умолчанию)")
    ap.add_argument("--dry-run", action="store_true", help="показать состояние, ничего не делая")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
