"""Markdown задания -> Telegram-HTML (подмножество: b, code, pre, a)."""
from __future__ import annotations
import html
import re
from datetime import date

WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _inline(line: str) -> str:
    line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', line)
    return line


def _blocks(md: str) -> list[str]:
    """Список блоков: обычные строки по одной, fenced-код — одним блоком <pre>."""
    out: list[str] = []
    lines = html.escape(md, quote=False).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            code: list[str] = []
            while j < len(lines) and not lines[j].startswith("```"):
                code.append(lines[j])
                j += 1
            out.append("<pre>" + "\n".join(code) + "</pre>")
            i = j + 1
            continue
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            out.append(f"<b>{_inline(heading.group(1).strip())}</b>")
        elif line.startswith("&gt; "):
            out.append(_inline(line[5:]))
        else:
            out.append(_inline(line))
        i += 1
    return out


def telegram_html(md: str, limit: int = 3500, more_url: str | None = None) -> str:
    text = "\n".join(_blocks(md)).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) <= limit:
        return text
    tail = f"…\nПолностью: {more_url}" if more_url else "…"
    budget = limit - len(tail)
    cut = text.rfind("\n", 0, budget)
    head = text[:cut if cut > 0 else budget]
    if head.count("<pre>") != head.count("</pre>"):
        head = head[:head.rfind("<pre>")].rstrip()
    return head.rstrip() + tail


def homework_block(task_md: str, hw_id: str, due: date | None, url: str) -> str:
    title = f"<b>Домашка до {WEEKDAYS[due.weekday()]} {due.strftime('%d.%m')}</b>" if due else "<b>Домашка</b>"
    return f"{title}\n{telegram_html(task_md, more_url=url)}\n\nСтраница: {url}"
