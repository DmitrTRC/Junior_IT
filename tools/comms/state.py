from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class State:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.fresh = not self.path.is_file()              # первый запуск: файла состояния ещё не было
        self.data: dict = {"processed": {}, "pending": {}, "github": {}, "failures": {}, "tick": 0,
                           "reminder_sent_for": None, "digest_sent_on": None, "drafts_seen": []}
        if self.path.is_file():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))

    @property
    def pending(self) -> dict:
        return self.data["pending"]

    @property
    def github(self) -> dict:
        return self.data["github"]

    @property
    def tick(self) -> int:
        return int(self.data["tick"])

    @tick.setter
    def tick(self, value: int) -> None:
        self.data["tick"] = int(value)

    def processed(self, item_id: str) -> bool:
        return item_id in self.data["processed"]

    def mark_processed(self, item_id: str, now: datetime) -> None:
        self.data["processed"][item_id] = now.isoformat(timespec="seconds")

    def prune(self, now: datetime, days: int = 30) -> None:
        edge = (now - timedelta(days=days)).isoformat(timespec="seconds")
        self.data["processed"] = {k: v for k, v in self.data["processed"].items() if v >= edge}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)
