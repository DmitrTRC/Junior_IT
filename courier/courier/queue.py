"""Файловые очереди: элемент — <id>.json плюс каталог <id>/ с вложениями.

Порядок записи: сначала каталог с файлами, потом JSON — читатель берёт
элемент только по JSON, поэтому недописанных элементов не видит.
Переходы между каталогами — rename, атомарно.
"""
from __future__ import annotations
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BOXES = ("outbox", "sending", "sent", "inbox", "failed")
PULL_MARKER = ".last_pull"


def new_id() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S%f") + "-" + secrets.token_hex(4)


@dataclass
class Item:
    id: str
    data: dict
    files_dir: Path


class Queue:
    def __init__(self, root: Path):
        self.root = Path(root)
        for box in BOXES:
            (self.root / box).mkdir(parents=True, exist_ok=True)

    def _box(self, box: str) -> Path:
        if box not in BOXES:
            raise ValueError(f"неизвестный каталог очереди {box!r}")
        return self.root / box

    def put(self, box: str, data: dict, files: dict[str, bytes] | None = None) -> str:
        directory = self._box(box)
        item_id = data.get("id") or new_id()
        data = {**data, "id": item_id, "files": sorted((files or {}).keys())}
        if files:
            files_dir = directory / item_id
            files_dir.mkdir(exist_ok=True)
            for name, payload in files.items():
                (files_dir / name).write_bytes(payload)
        self._write_json(directory / f"{item_id}.json", data)
        return item_id

    def items(self, box: str) -> list[Item]:
        directory = self._box(box)
        return [self.load(box, path.stem) for path in sorted(directory.glob("*.json"))]

    def load(self, box: str, item_id: str) -> Item:
        directory = self._box(box)
        data = json.loads((directory / f"{item_id}.json").read_text(encoding="utf-8"))
        return Item(id=item_id, data=data, files_dir=directory / item_id)

    def save(self, item: Item, box: str) -> None:
        self._write_json(self._box(box) / f"{item.id}.json", item.data)

    def move(self, item_id: str, src: str, dst: str) -> None:
        src_dir, dst_dir = self._box(src), self._box(dst)
        files = src_dir / item_id
        if files.is_dir():
            os.rename(files, dst_dir / item_id)
        os.rename(src_dir / f"{item_id}.json", dst_dir / f"{item_id}.json")

    def find_sent_by_message(self, message_id: int) -> Item | None:
        for item in self.items("sent"):
            if item.data.get("message_id") == message_id:
                return item
        return None

    def touch_pull(self) -> None:
        (self.root / PULL_MARKER).touch()

    def last_pull_age(self, now: datetime) -> float | None:
        marker = self.root / PULL_MARKER
        if not marker.exists():
            return None
        return now.timestamp() - marker.stat().st_mtime

    def sizes(self) -> dict[str, int]:
        return {box: len(list((self.root / box).glob("*.json"))) for box in BOXES}

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
