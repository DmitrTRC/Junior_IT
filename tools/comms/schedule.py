"""Что brain делает по часам: напоминание накануне, пост после занятия, сводка хвостов."""
from __future__ import annotations
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from comms import course
from comms.config import Config
from comms.drafts import lesson_date, max_section, new_drafts
from comms.homework_text import homework_block
from comms.outbox import Outbox, esc
from comms.state import State
from info.common import next_session, weekday_ru
from journal import stats as journal_stats

TAIL_RE = re.compile(r"^(?P<hw>[^:]+): просрочена с (?P<since>\d{4}-\d{2}-\d{2})$")
SEND_BUTTONS = [("отправить в группу", "send:{id}"), ("отбросить", "discard:{id}")]


def _stage_post(state: State, outbox: Outbox, cfg: Config, text: str, files: dict[str, bytes], max_copy: bool) -> str:
    preview = text if len(text) < 3900 else text[:3900] + "…"
    item_id = outbox.teacher_with_self_buttons(preview, SEND_BUTTONS, files=files or None)
    pending_dir = cfg.local_dir / "pending" / item_id
    if files:
        pending_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (pending_dir / name).write_bytes(content)
    state.pending[item_id] = {"kind": "post", "target": "group", "text": text,
                              "files": sorted(files.keys()), "max_copy": max_copy}
    return item_id


def reminder_text(session: dict, pages_url: str) -> str:
    day = session["date"]
    when = f"{weekday_ru(day)} {day.strftime('%d.%m')} в {session.get('time', '20:00')}"
    theme = esc(session.get("theme") or "занятие")
    return f"Напоминаю: завтра, {when} — занятие Junior_IT.\nТема: {theme}.\nМатериалы: {pages_url}"


def post_text(max_text: str, hw_blocks: list[str]) -> str:
    return "\n\n".join([esc(max_text), *hw_blocks]).strip()


def digest_text(tails: list[dict]) -> str:
    lines = [f"Хвосты по домашкам на сегодня ({len(tails)}):"]
    for t in tails:
        lines.append(f"• {esc(t['name'])} — {esc(t['hw_id'])}, срок был {t['since']}")
    lines.append("Кнопка — напомнить ученику в личку.")
    return "\n".join(lines)


def collect_tails(students_root, repo_root, today: date) -> list[dict]:
    group = journal_stats.collect(students_root, repo_root, today)
    out = []
    for s in group.students:
        for tail in s.tails:
            m = TAIL_RE.match(tail)
            if m:
                out.append({"student": s.id, "name": s.name, "hw_id": m.group("hw"), "since": m.group("since")})
    return out


def _reminder(cfg: Config, state: State, outbox: Outbox, now: datetime) -> bool:
    session, stale = next_session(course.sessions(cfg.repo_root), now.date())
    if not session or stale or session["date"] != now.date() + timedelta(days=1):
        return False
    if now.hour < cfg.reminder_hour or state.data.get("reminder_sent_for") == session["date"].isoformat():
        return False
    text = reminder_text(session, cfg.pages_url)
    _stage_post(state, outbox, cfg, text, {}, max_copy=False)
    state.data["reminder_sent_for"] = session["date"].isoformat()
    return True


def _posts(cfg: Config, state: State, outbox: Outbox) -> list[str]:
    done = []
    for path in new_drafts(course.drafts_dir(cfg.repo_root), state.data["drafts_seen"]):
        state.data["drafts_seen"].append(path.name)
        section = max_section(path.read_text(encoding="utf-8"))
        if not section:
            continue
        day = lesson_date(path)
        plan = course.plan_for(cfg.repo_root, day) if day else None
        blocks, files = [], {}
        for hw_id in (course.homework_ids(plan) if plan else []):
            url = course.page_url(cfg.pages_url, hw_id)
            blocks.append(homework_block(course.task_text(cfg.repo_root, hw_id), hw_id, course.due(plan), url))
            files.update(course.attachments(cfg.repo_root, hw_id))
        _stage_post(state, outbox, cfg, post_text(section, blocks), files, max_copy=True)
        done.append(f"post:{path.name}")
    return done


def _digest(cfg: Config, state: State, outbox: Outbox, now: datetime, tails_fn) -> bool:
    today = now.date().isoformat()
    if now.hour < cfg.digest_hour or state.data.get("digest_sent_on") == today:
        return False
    state.data["digest_sent_on"] = today
    tails = tails_fn()
    if not tails:
        return False
    spec = [(f"напомнить: {t['name']}", f"remind:{n}:{{id}}") for n, t in enumerate(tails)]
    item_id = outbox.teacher_with_self_buttons(digest_text(tails), spec)
    state.pending[item_id] = {"kind": "digest", "tails": tails}
    return True


def run(cfg: Config, state: State, outbox: Outbox, now: datetime, tails_fn) -> list[str]:
    done: list[str] = []
    if _reminder(cfg, state, outbox, now):
        done.append("reminder")
    done.extend(_posts(cfg, state, outbox))
    if _digest(cfg, state, outbox, now, tails_fn):
        done.append("digest")
    return done
