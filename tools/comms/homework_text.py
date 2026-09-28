"""Markdown задания -> Telegram-HTML (подмножество: b, code, pre, a)."""
from __future__ import annotations
import html
import re
from datetime import date

WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _inline(line: str) -> str:
    """Применяет разметку, защищая код-спаны от обработки."""
    code_spans = []

    def save_code(match):
        idx = len(code_spans)
        content = match.group(1)
        code_spans.append(f"<code>{content}</code>")
        return f"\x00{idx}\x00"

    line = re.sub(r"`([^`]+)`", save_code, line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', line)

    for idx, span in enumerate(code_spans):
        line = line.replace(f"\x00{idx}\x00", span)

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


def _balance(head: str) -> str:
    """Гарантирует, что все теги закрыты; обрезает до последнего открытого тега."""
    for tag in ("pre", "b", "code", "a"):
        while head.count(f"<{tag}>") > head.count(f"</{tag}>"):
            pos = head.rfind(f"<{tag}>")
            if pos >= 0:
                head = head[:pos].rstrip()
            else:
                break

    last_close = head.rfind(">")
    last_open = head.rfind("<", 0, last_close) if last_close >= 0 else -1
    if last_open >= 0 and last_close > last_open:
        pass
    elif last_open >= 0:
        head = head[:last_open].rstrip()

    return head


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
    head = _balance(head)
    return head.rstrip() + tail


def homework_block(task_md: str, hw_id: str, due: date | None, url: str) -> str:
    title = f"<b>Домашка до {WEEKDAYS[due.weekday()]} {due.strftime('%d.%m')}</b>" if due else "<b>Домашка</b>"
    return f"{title}\n{telegram_html(task_md, more_url=url)}\n\nСтраница: {url}"
