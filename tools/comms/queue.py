"""Элементы очередей в формате courier: <id>.json + каталог <id>/ с вложениями. Без импорта из courier."""
from __future__ import annotations
import json
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def new_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "-" + secrets.token_hex(4)


@dataclass
class Item:
    id: str
    data: dict
    files_dir: Path


def write_item(box_dir: Path, data: dict, files: dict[str, bytes] | None = None) -> str:
    box_dir = Path(box_dir)
    box_dir.mkdir(parents=True, exist_ok=True)
    item_id = data.get("id") or new_id()
    payload = {**data, "id": item_id, "files": sorted((files or {}).keys())}
    if files:
        (box_dir / item_id).mkdir(exist_ok=True)
        for name, content in files.items():
            (box_dir / item_id / name).write_bytes(content)
    tmp = box_dir / f"{item_id}.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, box_dir / f"{item_id}.json")
    return item_id


def read_items(box_dir: Path) -> list[Item]:
    box_dir = Path(box_dir)
    if not box_dir.is_dir():
        return []
    items = []
    for path in sorted(box_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items.append(Item(id=path.stem, data=data, files_dir=box_dir / path.stem))
    return items


def remove_item(box_dir: Path, item_id: str) -> None:
    box_dir = Path(box_dir)
    (box_dir / f"{item_id}.json").unlink(missing_ok=True)
    shutil.rmtree(box_dir / item_id, ignore_errors=True)
