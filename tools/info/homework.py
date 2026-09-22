from __future__ import annotations
from datetime import date

from info.common import Line, fmt_day, homework_task, hw_id_from_ref
from journal.store import hw_due_from_plan

SUBMITTED = ("submitted", "accepted", "rework")


def lines(lessons, plans: dict, today: date, next_plan: dict | None = None, active_ids: set[str] | None = None) -> list[Line]:
    """lessons — journal.model.LessonRecord; plans — {date: план}; next_plan — план ближайшего занятия."""
    out: list[Line] = []
    for rec in sorted(lessons, key=lambda r: r.date, reverse=True):
        plan = plans.get(rec.date)
        due = hw_due_from_plan(plan) if plan else None
        for hw_id, marks in rec.homework.items():
            marks = {sid: m for sid, m in marks.items() if active_ids is None or sid in active_ids}
            if not marks:
                continue
            total = len(marks)
            submitted = sum(1 for m in marks.values() if m.status in SUBMITTED)
            if not submitted:
                continue
            accepted = sum(1 for m in marks.values() if m.status == "accepted")
            text = f"{hw_id} · сдано {submitted}/{total} · принято {accepted}/{total}"
            if due:
                text += f" · до {fmt_day(due)}"
            if total and accepted == total:
                style = "ok"
            elif due and due < today:
                style = "warn"
            else:
                style = None
            out.append(Line(text, open=homework_task(hw_id), style=style))
    issued = {hw_id for rec in lessons for hw_id in rec.homework}
    for ref in ((next_plan or {}).get("homework") or {}).get("items") or []:
        hw_id = hw_id_from_ref(ref)
        if hw_id not in issued:
            out.append(Line(f"{hw_id} · не выдана", open=homework_task(hw_id), style="dim"))
    if not out:
        out.append(Line("нет журнала", style="dim"))
    return out
