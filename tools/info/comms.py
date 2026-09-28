"""info comms — бокс «связь»: статус почтальона и последнего тика мозга."""
from __future__ import annotations
from datetime import datetime

from info.common import Line

STALE_MIN = 5


def _age_min(ts: str | None, now: datetime) -> int | None:
    if not ts:
        return None
    return max(0, int((now - datetime.fromisoformat(ts)).total_seconds() // 60))


def lines(status: dict | None, last_tick: dict | None, now: datetime) -> list[Line]:
    if status is None:
        courier = Line("почтальон: статус не забирали", style="warn")
    else:
        sizes = status.get("sizes") or {}
        age = _age_min(status.get("ts"), now)
        online = bool(status.get("online"))
        text = (f"почтальон: {'онлайн' if online else 'офлайн'} · исходящих {sizes.get('outbox', 0)} · "
                f"входящих {sizes.get('inbox', 0)} · не доставлено {sizes.get('failed', 0)}")
        if age is not None and age > STALE_MIN:
            text += f" · статус {age} мин назад"
        style = "err" if (not online or sizes.get("failed", 0)) else ("warn" if age is not None and age > STALE_MIN else "ok")
        courier = Line(text, style=style)
    if last_tick is None:
        brain = Line("мозг: тик не запускался", style="warn")
    else:
        age = _age_min(last_tick.get("ts"), now) or 0
        errors = (last_tick.get("counts") or {}).get("errors", 0)
        brain = Line(f"мозг: тик {age} мин назад · ждут кнопок {last_tick.get('pending', 0)} · ошибок {errors}",
                     style="warn" if (age > 3 or errors) else "ok")
    return [courier, brain]
