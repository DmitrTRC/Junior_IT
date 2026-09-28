"""Исходящие элементы brain -> outbox-staging/ (на HP их переносит transport.push)."""
from __future__ import annotations
import html
from pathlib import Path

from comms.queue import write_item


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


class Outbox:
    def __init__(self, staging: Path):
        self.staging = Path(staging)

    def _put(self, to: str, text: str, buttons=None, files=None, **extra) -> str:
        data = {"to": to, "text": text, "parse_mode": "HTML", "reply_to": None, "attempts": 0,
                "buttons": [{"label": label, "data": data} for label, data in (buttons or [])], **extra}
        return write_item(self.staging, data, files)

    def teacher(self, text: str, buttons=None, files=None) -> str:
        return self._put("teacher", text, buttons, files)

    def group(self, text: str, files=None) -> str:
        return self._put("group", text, None, files)

    def person(self, comms_id: str, text: str, buttons=None, files=None) -> str:
        return self._put(comms_id, text, buttons, files)

    def control_add_code(self, code: str, comms_id: str) -> str:
        return self._put("courier", "", action="add_code", code=code, comms_id=comms_id)
