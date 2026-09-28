"""Реестр: код регистрации -> comms_id, telegram_id -> comms_id. Имён здесь нет."""
from __future__ import annotations
import json
import os
from pathlib import Path


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.codes: dict[str, str] = {}
        self.ids: dict[str, str] = {}
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.codes = dict(data.get("codes") or {})
            self.ids = {str(k): v for k, v in (data.get("ids") or {}).items()}

    def add_code(self, code: str, comms_id: str) -> None:
        self.codes[code] = comms_id
        self.save()

    def bind(self, code: str, telegram_id: int) -> str | None:
        comms_id = self.codes.pop(code, None)
        if comms_id is None:
            return None
        self.ids = {k: v for k, v in self.ids.items() if v != comms_id}
        self.ids[str(telegram_id)] = comms_id
        self.save()
        return comms_id

    def who(self, telegram_id: int) -> str | None:
        return self.ids.get(str(telegram_id))

    def telegram_id_of(self, comms_id: str) -> int | None:
        for key, value in self.ids.items():
            if value == comms_id:
                return int(key)
        return None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"codes": self.codes, "ids": self.ids}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)
