"""Входящие из очереди -> журнал, черновики, исходящие. Детям — только после кнопки Димаса."""
from __future__ import annotations
import html
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from comms import course
from comms.claude_draft import draft
from comms.config import Config
from comms.github_poll import Submission
from comms.identity import Identity
from comms.outbox import Outbox, esc
from comms.queue import Item
from comms.state import State
from journal import ops, store
from journal.model import JournalError

log = logging.getLogger("comms.apply")
SUBMISSION_BUTTONS = [("принято", "accept:{id}"), ("доработать", "rework:{id}"), ("Claude, разбери", "claude:{id}")]
QUESTION_BUTTONS = [("Claude, черновик", "claude:{id}")]
POST_BUTTONS = [("отправить", "send:{id}"), ("отбросить", "discard:{id}")]
UNSUPPORTED_RU = {"voice": "голосовое", "sticker": "стикер", "video": "видео", "other": "что-то нечитаемое"}
TEXT_EXT = {".py", ".txt", ".md", ".html", ".css", ".js"}


@dataclass
class Context:
    cfg: Config
    state: State
    identity: Identity
    outbox: Outbox
    runner: object
    now: datetime
    names: dict[str, str] = field(default_factory=dict)

    @property
    def today(self) -> date:
        return self.now.date()

    def name(self, student_id: str) -> str:
        return self.names.get(student_id, student_id)

    def pending_dir(self, item_id: str) -> Path:
        return self.cfg.local_dir / "pending" / item_id


def plain(html_text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", html_text))


def open_homework(students_root, student_id: str) -> tuple[date, str] | None:
    for rec in sorted(store.load_lessons(students_root), key=lambda r: r.date, reverse=True):
        for hw_id, marks in rec.homework.items():
            m = marks.get(student_id)
            if m and m.status in ("issued", "rework"):
                return rec.date, hw_id
    return None


def ensure_issued(ctx: Context, student_id: str, hw_id: str) -> date:
    for rec in sorted(store.load_lessons(ctx.cfg.students_root), key=lambda r: r.date, reverse=True):
        if student_id in (rec.homework.get(hw_id) or {}):
            return rec.date
    found = course.latest_plan_with_homework(ctx.cfg.repo_root, ctx.today)
    if not found:
        raise JournalError(f"нет плана с домашкой для {hw_id}")
    day, _ = found
    ops.issue_homework(day, hw_id, [student_id], ctx.cfg.students_root, ctx.cfg.repo_root)
    return day


def record_submission(ctx: Context, student_id: str, hw_id: str, note: str, by: str) -> date:
    day = ensure_issued(ctx, student_id, hw_id)
    ops.set_homework(day, hw_id, student_id, "submitted", note, ctx.cfg.students_root, ctx.today, by)
    return day


def _stash_files(ctx: Context, item_id: str, files: dict[str, bytes]) -> None:
    if not files:
        return
    target = ctx.pending_dir(item_id)
    target.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (target / name).write_bytes(content)


def _pending_files(ctx: Context, item_id: str) -> dict[str, bytes]:
    d = ctx.pending_dir(item_id)
    return {p.name: p.read_bytes() for p in sorted(d.iterdir())} if d.is_dir() else {}


def _drop_pending(ctx: Context, item_id: str) -> dict | None:
    meta = ctx.state.pending.pop(item_id, None)
    shutil.rmtree(ctx.pending_dir(item_id), ignore_errors=True)
    return meta


def _notify_submission(ctx: Context, student_id: str, hw_id: str, day: date, summary: str,
                       files: dict[str, bytes]) -> str:
    person = ctx.identity.by_student(student_id)
    text = f"<b>{esc(ctx.name(student_id))}</b> сдал(а) {esc(hw_id)}: {esc(summary)}"
    item_id = ctx.outbox.teacher_with_self_buttons(text, SUBMISSION_BUTTONS, files=files or None)
    _stash_files(ctx, item_id, files)
    ctx.state.pending[item_id] = {"kind": "submission", "student": student_id, "comms_id": person.comms_id,
                                  "hw_id": hw_id, "day": day.isoformat(), "summary": summary, "await_reply": False}
    return item_id


def _stage_draft(ctx: Context, text: str, target: str, max_copy: bool, files: dict[str, bytes] | None = None) -> str:
    item_id = ctx.outbox.teacher_with_self_buttons(esc(text), POST_BUTTONS, files=files)
    _stash_files(ctx, item_id, files or {})
    ctx.state.pending[item_id] = {"kind": "post", "target": target, "text": esc(text),
                                  "files": sorted((files or {}).keys()), "max_copy": max_copy}
    return item_id


def handle_github(ctx: Context, submissions: list[Submission]) -> None:
    for sub in submissions:
        total = sub.passed + sub.failed
        summary = f"github {sub.sha[:7]}: тесты {sub.passed}/{total}" if total else f"github {sub.sha[:7]}: тестов нет"
        try:
            day = record_submission(ctx, sub.student, sub.hw_id, summary, "github")
        except JournalError as exc:
            ctx.outbox.teacher(f"Сдача {esc(sub.student)} {esc(sub.hw_id)} не записана: {esc(str(exc))}")
            continue
        _notify_submission(ctx, sub.student, sub.hw_id, day, summary + ("\n" + esc(sub.log[-600:]) if sub.failed else ""), {})


def _handle_registered(ctx: Context, item: Item) -> None:
    person = ctx.identity.bind(item.data["from"], int(item.data.get("telegram_id") or 0))
    if person is None:
        ctx.outbox.teacher(f"Зарегистрирован неизвестный comms_id {esc(item.data['from'])}")
        return
    role = "ученик" if person.role == "student" else "родитель"
    ctx.outbox.teacher(f"{esc(ctx.name(person.student))} ({role}) зарегистрирован(а) в Telegram.")


def _handle_person(ctx: Context, item: Item) -> None:
    person = ctx.identity.by_comms_id(item.data["from"])
    if person is None:
        log.warning("сообщение от незнакомого %s", item.data["from"])
        return
    name = ctx.name(person.student)
    if item.data.get("unsupported"):
        ctx.outbox.teacher(f"{esc(name)} прислал(а) {UNSUPPORTED_RU.get(item.data['unsupported'], 'что-то нечитаемое')} — "
                           f"бот такое не читает, ответь в Telegram сам.")
        return
    files = {n: (item.files_dir / n).read_bytes() for n in item.data.get("files") or [] if (item.files_dir / n).is_file()}
    is_submission = (person.role == "student" and ctx.cfg.telegram_fallback
                     and item.data["kind"] in ("photo", "document"))
    if is_submission:
        found = open_homework(ctx.cfg.students_root, person.student)
        if found:
            _, hw_id = found
        else:
            plan = course.latest_plan_with_homework(ctx.cfg.repo_root, ctx.today)
            if not plan:
                ctx.outbox.teacher(f"{esc(name)} прислал(а) файл, но домашки в планах нет — разбери сам.")
                return
            hw_id = course.homework_ids(plan[1])[0]
        keep = ctx.cfg.students_root / "submissions" / person.student / hw_id / item.id
        keep.mkdir(parents=True, exist_ok=True)
        for n, content in files.items():
            (keep / n).write_bytes(content)
        summary = f"telegram: {', '.join(files) or 'без файлов'}"
        try:
            day = record_submission(ctx, person.student, hw_id, summary, "telegram")
        except JournalError as exc:
            ctx.outbox.teacher(f"Сдача {esc(name)} не записана: {esc(str(exc))}")
            return
        _notify_submission(ctx, person.student, hw_id, day, summary + (f" — «{item.data['text']}»" if item.data.get("text") else ""), files)
        return
    who = "родитель" if person.role == "parent" else "ученик"
    text = (f"<b>{esc(name)}</b> ({who}, {'группа' if item.data['chat'] == 'group' else 'личка'}): "
            f"{esc(item.data.get('text') or '')}\nОтветь reply — уйдёт человеку от бота.")
    item_id = ctx.outbox.teacher_with_self_buttons(text, QUESTION_BUTTONS, files=files or None)
    ctx.state.pending[item_id] = {"kind": "question", "student": person.student, "comms_id": person.comms_id,
                                  "text": item.data.get("text") or ""}


def _send_post(ctx: Context, item_id: str, meta: dict) -> None:
    files = _pending_files(ctx, item_id)
    if meta["target"] == "group":
        ctx.outbox.group(meta["text"], files=files or None)
    else:
        ctx.outbox.person(meta["target"], meta["text"], files=files or None)
    if meta.get("max_copy"):
        ctx.outbox.teacher("Дубль для MAX (скопируй):\n\n" + esc(plain(meta["text"])))
    else:
        ctx.outbox.teacher("Отправлено.")


def _handle_callback(ctx: Context, item: Item) -> None:
    action, _, rest = (item.data.get("callback") or "").partition(":")
    if action == "remind":
        index, _, item_id = rest.partition(":")
        meta = ctx.state.pending.get(item_id)
        if not meta or meta.get("kind") != "digest":
            ctx.outbox.teacher("Уже сделано.")
            return
        tail = meta["tails"][int(index)]
        person = ctx.identity.by_student(tail["student"])
        url = course.page_url(ctx.cfg.pages_url, tail["hw_id"])
        ctx.outbox.person(person.comms_id, f"Напоминаю: домашка {esc(tail['hw_id'])} ждёт, срок был {tail['since']}. "
                                           f"Страница: {url}")
        ctx.outbox.teacher(f"Напомнил(а) {esc(tail['name'])}.")
        return
    item_id = rest
    meta = ctx.state.pending.get(item_id)
    if meta is None:
        ctx.outbox.teacher("Уже сделано.")
        return
    if action == "send" and meta["kind"] == "post":
        _send_post(ctx, item_id, meta)
        _drop_pending(ctx, item_id)
    elif action == "discard":
        _drop_pending(ctx, item_id)
        ctx.outbox.teacher("Отброшено.")
    elif action == "accept" and meta["kind"] == "submission":
        _drop_pending(ctx, item_id)
        try:
            ops.set_homework(date.fromisoformat(meta["day"]), meta["hw_id"], meta["student"], "accepted",
                             None, ctx.cfg.students_root, ctx.today, "teacher")
        except JournalError as exc:
            ctx.outbox.teacher(f"Не принято: {esc(str(exc))}")
            return
        ctx.outbox.person(meta["comms_id"], f"Домашка {esc(meta['hw_id'])} принята. Молодец!")
        ctx.outbox.teacher(f"Принято: {esc(ctx.name(meta['student']))}, {esc(meta['hw_id'])}.")
    elif action == "rework" and meta["kind"] == "submission":
        meta["await_reply"] = True
        ctx.outbox.teacher(f"Ответь reply на сообщение о сдаче {esc(ctx.name(meta['student']))} текстом для ученика — "
                           f"уйдёт ему, статус станет «доработать».")
    elif action == "claude":
        _claude_for(ctx, item_id, meta)
    else:
        ctx.outbox.teacher("Уже сделано.")


def _claude_for(ctx: Context, item_id: str, meta: dict) -> None:
    task_text = course.task_text(ctx.cfg.repo_root, meta.get("hw_id", "")) if meta.get("hw_id") else ""
    if meta["kind"] == "submission":
        files = _pending_files(ctx, item_id)
        files_text = "\n\n".join(f"--- {n} ---\n{c.decode('utf-8', 'replace')[:4000]}"
                                 for n, c in files.items() if Path(n).suffix in TEXT_EXT) or "(файлов с кодом нет)"
        text = draft("review", {"student_name": ctx.name(meta["student"]), "hw_id": meta["hw_id"],
                                "task_text": task_text, "files_text": files_text, "tests_summary": meta["summary"]},
                     ctx.cfg, ctx.runner)
    elif meta["kind"] == "question":
        found = open_homework(ctx.cfg.students_root, meta["student"])
        task_text = course.task_text(ctx.cfg.repo_root, found[1]) if found else ""
        text = draft("answer", {"student_name": ctx.name(meta["student"]), "question": meta["text"],
                                "task_text": task_text}, ctx.cfg, ctx.runner)
    else:
        ctx.outbox.teacher("К этому черновик не нужен.")
        return
    if not text:
        ctx.outbox.teacher("Черновик не получился — claude -p не ответил.")
        return
    _stage_draft(ctx, text, meta["comms_id"], max_copy=False)


def _handle_reply(ctx: Context, item: Item) -> None:
    meta = ctx.state.pending.get(item.data.get("reply_to_item") or "")
    text = item.data.get("text") or ""
    if meta is None:
        ctx.outbox.teacher("Не нашёл, к чему этот ответ — сообщение уже обработано.")
        return
    if meta["kind"] == "submission" and meta.get("await_reply"):
        _drop_pending(ctx, item.data["reply_to_item"])
        try:
            ops.set_homework(date.fromisoformat(meta["day"]), meta["hw_id"], meta["student"], "rework",
                             text, ctx.cfg.students_root, ctx.today, "teacher")
        except JournalError as exc:
            ctx.outbox.teacher(f"Статус не изменён: {esc(str(exc))}")
            return
        ctx.outbox.person(meta["comms_id"], f"Домашка {esc(meta['hw_id'])} — доработать:\n{esc(text)}\n— Димас")
        ctx.outbox.teacher(f"Отправлено {esc(ctx.name(meta['student']))}, статус «доработать».")
    elif meta["kind"] == "question":
        _drop_pending(ctx, item.data["reply_to_item"])
        ctx.outbox.person(meta["comms_id"], f"{esc(text)}\n— Димас")
        ctx.outbox.teacher(f"Отправлено {esc(ctx.name(meta['student']))}.")
    else:
        ctx.outbox.teacher("К этому сообщению reply не нужен — есть кнопки.")


def _handle_teacher_text(ctx: Context, item: Item) -> None:
    text = (item.data.get("text") or "").strip()
    if text.startswith("/claude"):
        task = text[len("/claude"):].strip() or "сводка по группе"
        context = _context_text(ctx)
        result = draft("task", {"task": task, "context": context}, ctx.cfg, ctx.runner)
        if not result:
            ctx.outbox.teacher("Черновик не получился — claude -p не ответил.")
            return
        _stage_draft(ctx, result, "group", max_copy=True)
    elif text.startswith("/status"):
        ctx.outbox.teacher(_status_text(ctx))


def _context_text(ctx: Context) -> str:
    from journal import stats as journal_stats
    from journal.cli import format_report
    try:
        return format_report(journal_stats.collect(ctx.cfg.students_root, ctx.cfg.repo_root, ctx.today))
    except JournalError as exc:
        return f"(журнал не прочитан: {exc})"


def _status_text(ctx: Context) -> str:
    return (f"Ожидают кнопок: {len(ctx.state.pending)}. Тик № {ctx.state.tick}. "
            f"Людей без Telegram: {sum(1 for p in ctx.identity.people if p.telegram_id is None)}.")


def apply_item(item: Item, ctx: Context) -> None:
    kind, sender = item.data.get("kind"), item.data.get("from", "")
    if kind == "registered":
        _handle_registered(ctx, item)
    elif kind == "callback":
        _handle_callback(ctx, item)
    elif kind == "reply" and sender == "teacher":
        _handle_reply(ctx, item)
    elif sender == "teacher":
        _handle_teacher_text(ctx, item)
    elif kind in ("text", "photo", "document"):
        _handle_person(ctx, item)
    else:
        log.info("пропущен элемент %s kind=%s from=%s", item.id, kind, sender)
