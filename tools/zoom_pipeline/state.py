import json
from pathlib import Path

PHASES = ("downloaded", "backed_up", "transcribed", "analyzed", "cloud_deleted")


class State:
    def __init__(self, path, entries):
        self._path = Path(path)
        self._entries = entries

    @classmethod
    def load(cls, path):
        path = Path(path)
        entries = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    entries = raw
            except json.JSONDecodeError:
                entries = {}  # битый state не повод падать: начнём заново
        return cls(path, entries)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def phase(self, uuid):
        return self._entries.get(uuid, {}).get("phase", "new")

    def meta(self, uuid):
        entry = self._entries.get(uuid, {})
        return {"date": entry.get("date", ""), "topic": entry.get("topic", "")}

    def advance(self, uuid, phase, *, date="", topic=""):
        entry = self._entries.setdefault(uuid, {})
        entry["phase"] = phase
        if date and not entry.get("date"):
            entry["date"] = date
        if topic and not entry.get("topic"):
            entry["topic"] = topic
        self._save()

    def uuids_in_phase(self, phase):
        return [u for u, e in self._entries.items() if e.get("phase") == phase]
