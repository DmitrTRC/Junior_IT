from __future__ import annotations
from datetime import date

from build_course_map import module_statuses
from info.common import PAGES_URL, Line


def lines(modules: list[dict], sessions: list[dict], today: date) -> list[Line]:
    held = sum(1 for s in sessions if s["date"] < today)
    statuses = module_statuses(modules, sessions, today)
    counted = [m for m in modules if statuses[m["id"]] != "library"]
    done_total = sum(1 for m in counted if statuses[m["id"]] == "done")
    by_track: dict[str, list[int]] = {}
    for module in counted:
        done, total = by_track.setdefault(module["track"], [0, 0])
        by_track[module["track"]] = [done + (statuses[module["id"]] == "done"), total + 1]
    tracks = " · ".join(f"{track} {done}/{total}" for track, (done, total) in sorted(by_track.items()))
    return [
        Line(f"занятий проведено: {held}", open=PAGES_URL, style="dim"),
        Line(f"модулей: {done_total}/{len(counted)}", open=PAGES_URL, style="dim"),
        Line(tracks or "модулей нет", open=PAGES_URL, style="dim"),
    ]
