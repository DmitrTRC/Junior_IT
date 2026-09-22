from __future__ import annotations

from info.common import TUI_CMD, Line
from journal.model import num

ROSTER_EXAMPLE = "tools/journal/roster.example.yml"


def lines(group, tui_cmd: str = TUI_CMD) -> list[Line]:
    """group — journal.stats.GroupStats или None, если нет students/roster.yml."""
    if group is None:
        return [Line("нет students/roster.yml — шаблон: tools/journal/roster.example.yml",
                     open=ROSTER_EXAMPLE, style="warn")]
    out = [Line(f"журнал · занятий {group.lessons_total}", open=f"run:{tui_cmd}")]
    for s in group.students:
        attended = s.present + s.late
        text = f"{s.name} · был {attended}/{s.lessons_total} · дз {s.hw_accepted}/{s.hw_issued} · {num(s.points_total)} б"
        out.append(Line(text, open=f"run:{tui_cmd}", style="warn" if s.tails else None))
    for day in group.missing_journals:
        out.append(Line(f"без журнала: {day.isoformat()}",
                        open=f"run:{tui_cmd} --date {day.isoformat()}", style="warn"))
    return out
