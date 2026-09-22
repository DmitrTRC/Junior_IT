from __future__ import annotations
from datetime import date

from info.common import (
    REPO_ROOT, Line, as_date, countdown, fmt_day, homework_task, hw_id_from_ref,
    scenario_target, weekday_ru,
)


def lines(session: dict | None, stale: bool, today: date, repo_root=REPO_ROOT) -> list[Line]:
    if session is None:
        return [Line("планов нет — заведи playground/<дата>/session.yml", style="warn")]
    day = as_date(session["date"])
    plan_path = f"playground/{day.isoformat()}/session.yml"
    head = f"{weekday_ru(day)} {fmt_day(day)}"
    if session.get("time"):
        head += f" {session['time']}"
    head += f" · {countdown(day, today)}"
    if stale:
        out = [Line(head + " · план на следующее не создан", open=plan_path, style="warn")]
    else:
        out = [Line(head, open=plan_path, style="ok" if day == today else None)]
    if session.get("theme"):
        out.append(Line(str(session["theme"]), open=plan_path))
    for item in session.get("playlist") or []:
        if not isinstance(item, dict) or not item.get("module"):
            continue
        module_id = str(item["module"])
        text = f"{module_id} · {item['minutes']} мин" if item.get("minutes") else module_id
        out.append(Line(text, open=scenario_target(module_id, repo_root)))
    homework = session.get("homework") or {}
    due = homework.get("due")
    for ref in homework.get("items") or []:
        hw_id = hw_id_from_ref(ref)
        prefix = f"домашка до {fmt_day(as_date(due))}: " if due else "домашка: "
        out.append(Line(prefix + hw_id, open=homework_task(hw_id)))
    if session.get("buffer"):
        out.append(Line(f"буфер {session['buffer']} мин", style="dim"))
    return out
